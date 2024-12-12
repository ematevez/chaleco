"""

"""
import tempfile
import os
import base64
import json
import random
import socket
import sqlite3
import qrcode
from datetime import datetime, timedelta

import cv2
import threading
import time
import serial
import hashlib
import uuid


from dbr import BarcodeReader, EnumBarcodeFormat, BarcodeReaderError

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.checkbox import CheckBox
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.core.window import Window
from kivy.uix.image import Image as KivyImage
from kivy.core.image import Image as CoreImage
from kivy.uix.spinner import Spinner

from kivy.clock import Clock
from reportlab.pdfgen import canvas
from io import BytesIO
from dateutil import parser
from reportlab.lib.pagesizes import letter

from reportlab.lib.pagesizes import A4 ,legal  # Para tamaño legal (215.9 x 355.6 mm)
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import Image

BarcodeReader.init_license("t0068lQAAAJE2JXBA6tK6wQpYF0Wxe4oRj6oTYrPcH7RTiKUsx4L/E+yzVChE0B2dQiBMv6ghACzDeWR1lZi8E5T1AnBd8XI=;t0068lQAAAA5cVZ/dEh6TnHTS7RnGyZIn5IMCJtoKBr4i7Rab1V+/eE/njJonaNpZnJUyKFJosRPRvW+nWkEceVNukxDu8ck=")

class DatePicker(BoxLayout):
    def __init__(self, on_select, **kwargs):
        super().__init__(orientation='vertical', **kwargs)
        self.on_select = on_select

        self.spinner_year = Spinner(
            text='Año',
            values=[str(year) for year in range(1999, 2030)],
            size_hint=(1, None),
            height=40
        )
        self.spinner_month = Spinner(
            text='Mes',
            values=[str(month).zfill(2) for month in range(1, 13)],
            size_hint=(1, None),
            height=40
        )
        self.spinner_day = Spinner(
            text='Día',
            values=[str(day).zfill(2) for day in range(1, 32)],
            size_hint=(1, None),
            height=40
        )

        self.add_widget(self.spinner_year)
        self.add_widget(self.spinner_month)
        self.add_widget(self.spinner_day)

        btn_confirm = Button(text='Confirmar', size_hint=(1, None), height=44)
        btn_confirm.bind(on_press=self.confirm)
        self.add_widget(btn_confirm)

    def confirm(self, instance):
        year = self.spinner_year.text
        month = self.spinner_month.text
        day = self.spinner_day.text
        if year != 'Año' and month != 'Mes' and day != 'Día':
            fecha = f"{year}-{month}-{day}"
            self.on_select(fecha)
            self.parent.dismiss()
        else:
            popup = Popup(
                title='Error',
                content=Label(text='Debe seleccionar Año, Mes y Día.'),
                size_hint=(None, None),
                size=(400, 200)
            )
            popup.open()

class ChalecoApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Window.fullscreen = "auto" 
        self.arduino = None  
        
        base_desktop = r"C:\Users\Usuario}\Desktop"
        self.reportes_folder = os.path.join(base_desktop, 'Informes') 
        self.imagenes_folder = os.path.join(base_desktop, 'Imagenes') 
        self.db_path = os.path.join(os.getcwd(), '.chalecos.db')  

        os.makedirs(self.reportes_folder, exist_ok=True)
        os.makedirs(self.imagenes_folder, exist_ok=True)

        if not os.path.isfile(self.db_path):
            self.conn = sqlite3.connect(self.db_path)
            self.create_db()
            os.system(f'attrib +h {self.db_path}')  
    
    def iniciar_conexion_arduino(self):
        """Inicia la conexión serie con el Arduino."""
        try:
            self.arduino = serial.Serial('COM3', 9600, timeout=1)
            print("Conexión con Arduino establecida en COM3 a 9600 baudios.")
        except serial.SerialException as e:
            print(f"Error al conectar con Arduino: {e}")
            self.arduino = None
    def cerrar_conexion_arduino(self):
        """Cierra la conexión con el Arduino al salir de la aplicación."""
        if self.arduino and self.arduino.is_open:
            self.arduino.close()
            print("Conexión con Arduino cerrada.")
    def obtener_ip_local(self):
        """Obtiene la IP local de la máquina en la red."""
        try:
            hostname = socket.gethostname()
            ip_local = socket.gethostbyname(hostname)

            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0)
            try:
                s.connect(('10.254.254.254', 1))
                ip_local = s.getsockname()[0]
            except Exception:
                ip_local = '127.0.0.1'  
            finally:
                s.close()

            return ip_local

        except Exception as e:
            print(f"Error al obtener la IP local: {str(e)}")
            return '127.0.0.1'  
        
    def obtener_mac(self):
        """Obtiene la dirección MAC de la máquina."""
        mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) for elements in range(0, 8 * 6, 8)][::-1])
        return mac

    def encriptar(self, valor):
        """Encripta un valor usando SHA-256."""
        return hashlib.sha256(valor.encode()).hexdigest()
    
    def validar_mac(self):
        """Verifica si la MAC actual coincide con la autorizada."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT mac_autorizada FROM configuracion WHERE id = 1")
        resultado = cursor.fetchone()

        if resultado:
            mac_autorizada_encriptada = resultado[0]
            mac_actual = self.obtener_mac()
            mac_actual_encriptada = self.encriptar(mac_actual)

            if mac_actual_encriptada != mac_autorizada_encriptada:
                self.mostrar_popup('Error', 'La MAC de esta máquina no está autorizada. Contacte al administrador.')
                return False
        else:
            self.mostrar_popup('Error', 'No se encontró una MAC autorizada en la configuración.')
            return False
        return True
        
    def validar_codigo_y_fecha(self):
        """Verifica si el código sigue siendo válido en base a la fecha límite."""
        print("Iniciando validación de código y fecha...")
        
        cursor = self.conn.cursor()
        cursor.execute("SELECT fecha_creacion, codigo FROM configuracion WHERE id = 1")
        resultado = cursor.fetchone()

        if resultado:
            fecha_creacion_str, codigo_guardado = resultado
            print(f"Fecha en base de datos: {fecha_creacion_str}, Código guardado: {codigo_guardado}")

            mac_actual = self.obtener_mac()
            print(f"MAC actual: {mac_actual}")
            
            fecha_actual = datetime.now()
            print(f"Fecha actual: {fecha_actual.strftime('%Y-%m-%d')}")

            codigo_generado = self.encriptar(mac_actual + fecha_actual.strftime('%Y-%m-%d'))
            print(f"Código generado: {codigo_generado}")
            
            if codigo_guardado != codigo_generado:
                # self.mostrar_popup('Error', 'Código de validación inválido. Contacte al administrador.')
                return False

            fecha_creacion = datetime.strptime(fecha_creacion_str, '%Y-%m-%d')
            fecha_limite = fecha_creacion + timedelta(days=15)
            print(f"Fecha límite: {fecha_limite}")

        #     if fecha_actual > fecha_limite:
        #         self.mostrar_popup('Error', 'El programa ha expirado. Contacte al administrador.')
        #         return True
        # else:
        #     self.mostrar_popup('Error', 'No se encontró una fecha o código en la configuración.')
        #     return True
            
            print("Validación exitosa")
            return True


            
    def build(self):
        
        self.iniciar_conexion_arduino()
        
        self.conn = sqlite3.connect('chalecos.db', check_same_thread=False)
        self.create_db()
        
        if not self.validar_mac():
            print("Falla en la validación de MAC")
            exit(1)

        if not self.validar_codigo_y_fecha():
            print("Falla en la validación de código y fecha")
            # exit(1)
        
        self.root = BoxLayout(orientation='vertical', padding=10, spacing=10)
        self.create_widgets()
    
        self.ip_destino = self.obtener_ip_local()
        print(f"IP local detectada: {self.ip_destino}")
        
        Window.bind(on_key_down=self.on_key_down)
        
        return self.root
    def on_stop(self):
        """Se ejecuta al cerrar la aplicación."""
        self.cerrar_conexion_arduino()
        if self.conn:
            self.conn.close()
            print("Base de datos cerrada correctamente.")
        print("Aplicación cerrada correctamente.")

    def create_db(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chalecos_receptora (
                id INTEGER PRIMARY KEY AUTOINCREMENT,  -- Campo id como PRIMARY KEY
                lote TEXT,
                numero_serie TEXT,
                fabricante TEXT,
                fecha_fabricacion TEXT,
                fecha_vencimiento TEXT,
                tipo_modelo TEXT,
                peso TEXT,
                talla TEXT,
                procedencia TEXT,
                qr_image BLOB,  
                transmitido INTEGER DEFAULT 0,
                destruido INTEGER DEFAULT 0,
                informe INTEGER DEFAULT 0,
                fecha_destruido TEXT DEFAULT 0
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS configuracion (
                id INTEGER PRIMARY KEY,
                mac_autorizada TEXT,
                fecha_creacion TEXT,
                codigo TEXT
            )
        ''')
        self.conn.commit()
    def create_widgets(self):
        self.lote_input = TextInput(hint_text='Lote (autogenerado)', disabled=True)
        self.numero_serie_input = TextInput(hint_text='Número de Serie')
        self.fabricante_input = TextInput(hint_text='Fabricante')

        self.fecha_fabricacion_input = TextInput(hint_text='Fecha de Fabricación (YYYY-MM-DD)', readonly=True)
        self.btn_fecha_fabricacion = Button(text='Seleccionar Fecha', size_hint=(None, None), size=(150, 44))
        self.btn_fecha_fabricacion.bind(on_press=self.abrir_datepicker_fabricacion)

        self.fecha_vencimiento_input = TextInput(hint_text='Fecha de Vencimiento (YYYY-MM-DD)', readonly=True)
        self.btn_fecha_vencimiento = Button(text='Seleccionar Fecha', size_hint=(None, None), size=(150, 44))
        self.btn_fecha_vencimiento.bind(on_press=self.abrir_datepicker_vencimiento)

        self.tipo_modelo_input = TextInput(hint_text='Tipo/Modelo')
        self.peso_input = TextInput(hint_text='Peso')
        self.talla_spinner = Spinner(text='Seleccionar Talla', values=('XS', 'S', 'M', 'L', 'XL', 'XXL'), size_hint=(1, None), height=40)
        self.procedencia_input = TextInput(hint_text='Procedencia')

        self.scan_qr_button = Button(text='Escanear QR')  
        self.scan_qr_button.bind(on_press=self.scan_qr)  
        self.root.add_widget(self.scan_qr_button)

        self.destruction_button = Button(text='Destruir Chaleco', disabled=True)  
        self.destruction_button.bind(on_press=self.on_destruction_button)
        self.root.add_widget(self.destruction_button)

        self.comenzar_lote_button = Button(text='Comenzar Lote')
        self.comenzar_lote_button.bind(on_press=self.comenzar_lote) 
        self.add_chaleco_button = Button(text='Agregar Chaleco', disabled=True)
        self.add_chaleco_button.bind(on_press=self.agregar_chaleco)
        self.finalizar_lote_button = Button(text='Finalizar Lote', disabled=True)
        self.finalizar_lote_button.bind(on_press=self.finalizar_lote)
        self.ver_registro_button = Button(text='Ver Registro')
        self.ver_registro_button.bind(on_press=self.ver_registro)
        self.transmitir_wifi_button = Button(text='Transmitir WiFi', disabled=True)
        #self.transmitir_wifi_button.bind(on_press=self.transmitir_wifi)
        
        self.generar_informe_button = Button(text='Generar Informe', size_hint=(1, None), height=50)
        self.generar_informe_button.bind(on_press=self.generar_informe)
        self.root.add_widget(self.generar_informe_button)

        self.boton_secreto = Button(text='', size_hint=(None, None), size=(0, 0), opacity=0)  # Oculto inicialmente
        self.boton_secreto.bind(on_press=self.accion_secreta)
        self.root.add_widget(self.boton_secreto)
        
        self.root.add_widget(self.lote_input)
        self.root.add_widget(self.numero_serie_input)
        self.root.add_widget(self.fabricante_input)

        fecha_fabricacion_layout = BoxLayout(orientation='horizontal', size_hint=(1, None), height=40, spacing=10)
        fecha_fabricacion_layout.add_widget(self.fecha_fabricacion_input)
        fecha_fabricacion_layout.add_widget(self.btn_fecha_fabricacion)
        self.root.add_widget(fecha_fabricacion_layout)

        fecha_vencimiento_layout = BoxLayout(orientation='horizontal', size_hint=(1, None), height=40, spacing=10)
        fecha_vencimiento_layout.add_widget(self.fecha_vencimiento_input)
        fecha_vencimiento_layout.add_widget(self.btn_fecha_vencimiento)
        self.root.add_widget(fecha_vencimiento_layout)

        self.root.add_widget(self.tipo_modelo_input)
        self.root.add_widget(self.peso_input)
        self.root.add_widget(self.talla_spinner)
        self.root.add_widget(self.procedencia_input)
        self.root.add_widget(self.comenzar_lote_button)
        self.root.add_widget(self.add_chaleco_button)
        self.root.add_widget(self.finalizar_lote_button)
        self.root.add_widget(self.transmitir_wifi_button)
        self.root.add_widget(self.ver_registro_button)
        
    def solicitar_clave(self, instance):
        popup_content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        clave_input = TextInput(hint_text='Ingrese clave', password=True, multiline=False)

        btn_confirmar = Button(text='Confirmar')
        btn_confirmar.bind(on_press=lambda x: self.verificar_clave(clave_input.text))

        popup_content.add_widget(clave_input)
        popup_content.add_widget(btn_confirmar)

        self.popup_clave = Popup(title='Ingresar clave', content=popup_content, size_hint=(0.6, 0.4))
        self.popup_clave.open()
    def mostrar_boton_secreto(self):
        self.boton_secreto.size_hint = (None, None)
        self.boton_secreto.size = (150, 50) 
        self.boton_secreto.text = "Botón Secreto"
        self.boton_secreto.opacity = 1 
        self.boton_secreto.disabled = False  
    def verificar_clave(self, clave_ingresada):
        if clave_ingresada == '987123456':
            self.popup_clave.dismiss()  
            self.mostrar_popup_config_ip()  
        else:
            self.mostrar_popup('Error', 'Clave incorrecta')
            
    def mostrar_popup_config_ip(self):
        popup_content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        ip_input = TextInput(hint_text='Ingrese nueva IP', text=self.ip_destino, multiline=False)

        btn_guardar = Button(text='Guardar IP')
        btn_guardar.bind(on_press=lambda x: self.guardar_ip(ip_input.text))

        popup_content.add_widget(ip_input)
        popup_content.add_widget(btn_guardar)

        self.popup_ip = Popup(title='Configurar IP', content=popup_content, size_hint=(0.6, 0.4))
        self.popup_ip.open()
    
    def guardar_ip(self, nueva_ip):
        self.ip_destino = nueva_ip  
        self.popup_ip.dismiss()  
        self.mostrar_popup('Éxito', f'IP actualizada a {nueva_ip}')
        
    def generar_informe(self, instance):
        
        pdf_path = self.crear_pdf_informe_destruccion()

        if pdf_path:
            self.mostrar_popup('Informe Generado', f'El informe ha sido generado en: {pdf_path}')
        else:
            self.mostrar_popup('Error', 'No se pudo generar el informe.')
            
    def crear_pdf_informe_destruccion(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, lote, numero_serie, fabricante, tipo_modelo, fecha_fabricacion, fecha_vencimiento, fecha_destruido FROM chalecos_receptora WHERE destruido = 1 AND informe = 0")
        chalecos = cursor.fetchall()

        if not chalecos:
            self.mostrar_popup('Error', 'No hay chalecos destruidos para generar el informe.')
            return

        fecha_actual = datetime.now().strftime("%Y%m%d")
        pdf_path = os.path.join(self.reportes_folder, f"informe_{fecha_actual}.pdf")
        
        c = canvas.Canvas(pdf_path, pagesize=(legal[1], legal[0]))
        width, height = legal[1], legal[0]  

        def encabezado_pagina():
            y_position = height - 30  
            logo_path = "Logo.png"
            if os.path.exists(logo_path):
                c.drawImage(logo_path, 30, y_position - 40, width=70, height=40) 

            c.setFont("Helvetica-Bold", 16)
            c.drawCentredString(width / 2, y_position - 10, "INFORME DE DESTRUCCIÓN DE CHALECOS")

            c.setFont("Helvetica", 10)
            c.drawRightString(width - 30, y_position - 30, f"Fecha: {datetime.now().strftime('%Y-%m-%d')}")

            c.line(30, y_position - 40, width - 30, y_position - 40)

            c.setFont("Helvetica-Bold", 12)
            c.drawString(30, y_position - 60, "Lote")
            c.drawString(110, y_position - 60, "Número de Serie")  
            c.drawString(220, y_position - 60, "Fabricante")
            c.drawString(350, y_position - 60, "Modelo")
            c.drawString(460, y_position - 60, "Fecha Fab.")
            c.drawString(570, y_position - 60, "Fecha Venc.")
            c.drawString(680, y_position - 60, "Fecha Destruido.")
            c.drawString(800, y_position - 60, "Observaciones")

            return y_position - 70

        def agregar_registro(chaleco, y_position):
            c.setFont("Helvetica", 10)
            lote = chaleco[1] if chaleco[1] is not None else ""
            numero_serie = chaleco[2] if chaleco[2] is not None else ""
            fabricante = chaleco[3] if chaleco[3] is not None else ""
            modelo = chaleco[4] if chaleco[4] is not None else ""
            fecha_fabricacion = chaleco[5] if chaleco[5] is not None else ""
            fecha_vencimiento = chaleco[6] if chaleco[6] is not None else ""
            fecha_destruido = chaleco[7] if chaleco[7] is not None else ""

            c.drawString(30, y_position - 20, lote)
            c.drawString(110, y_position - 20, numero_serie)
            c.drawString(220, y_position - 20, fabricante)
            c.drawString(350, y_position - 20, modelo)
            c.drawString(460, y_position - 20, fecha_fabricacion)
            c.drawString(570, y_position - 20, fecha_vencimiento)
            c.drawString(680, y_position - 20, fecha_destruido)

            c.drawString(820, y_position - 10, "Obs.:")  

            return y_position - 15  

        registros_por_pagina = 40
        registros_contados = 0
        y_position = encabezado_pagina()

        for chaleco in chalecos:
            if registros_contados and registros_contados % registros_por_pagina == 0:
                c.showPage()
                y_position = encabezado_pagina()

            y_position = agregar_registro(chaleco, y_position)
            registros_contados += 1

        c.save()
        cursor.execute("UPDATE chalecos_receptora SET informe = 1 WHERE destruido = 1 AND informe = 0")
        self.conn.commit()

        return pdf_path
    def validar_orden_fechas(self):
        """Valida que la fecha de vencimiento sea mayor que la de fabricación"""
        try:
            fecha_fabricacion = datetime.strptime(self.fecha_fabricacion_input.text, '%Y-%m-%d')
            fecha_vencimiento = datetime.strptime(self.fecha_vencimiento_input.text, '%Y-%m-%d')

            if fecha_vencimiento > fecha_fabricacion:
                return True
            else:
                return False
        except ValueError:
            self.mostrar_popup('Error', 'Formato de fecha incorrecto. Use YYYY-MM-DD')
            return False
    
    def accion_secreta(self, instance):
        self.mostrar_popup('Acción Secreta', '¡Has activado el botón secreto!')

    def verificar_lote_existente(self, lote):
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM chalecos_receptora WHERE lote=?", (lote,))
        count = cursor.fetchone()[0]
        return count > 0
    
    def comenzar_lote(self, instance):
        lote_id = random.randint(1000, 9999)
        fecha_actual = datetime.now().strftime("%Y%m%d")
        lote_numero = f"L{lote_id}-{fecha_actual}"
        
        if self.verificar_lote_existente(lote_numero):
            self.mostrar_popup('Error', 'Número de lote ya existe, intenta nuevamente.')
            return
        
        self.lote_input.text = lote_numero

        self.add_chaleco_button.disabled = False
        self.finalizar_lote_button.disabled = False
        # self.transmitir_wifi_button.disabled = False
        self.comenzar_lote_button.disabled = True

        self.mostrar_popup('Lote Comenzado', f'Se ha comenzado el lote: {lote_numero}')
        
    def agregar_chaleco(self, instance):
        try:
            if not self.campos_llenos():
                self.mostrar_popup('Error', 'Complete todos los campos antes de agregar un chaleco')
                return

            if not self.validar_fechas():
                self.mostrar_popup('Error', 'Formato de fecha incorrecto. Use YYYY-MM-DD')
                return

            if not self.validar_orden_fechas():
                self.mostrar_popup('Error', 'La fecha de vencimiento no puede ser menor o igual que la fecha de fabricación')
                return
            
            chaleco_id = self.guardar_chaleco()
            
            # DEBUG: Verifica que chaleco_id es diferente para cada chaleco
            #print(f"Generando QR para chaleco ID: {chaleco_id}")

            self.generar_qr(chaleco_id) 

            self.limpiar_campos()
    
        except Exception as e:
            self.mostrar_popup('Error', f'Error inesperado: {str(e)}')

    def limpiar_campos(self):
        self.numero_serie_input.text = ''
        self.fabricante_input.text = ''
        self.fecha_fabricacion_input.text = ''
        self.fecha_vencimiento_input.text = ''
        self.tipo_modelo_input.text = ''
        self.peso_input.text = ''
        self.talla_spinner.text = 'Seleccionar Talla'
        self.procedencia_input.text = ''

    def guardar_chaleco(self):
        lote = self.lote_input.text.strip().upper()
        numero_serie = self.numero_serie_input.text.strip().upper()
        fabricante = self.fabricante_input.text.strip().upper()
        fecha_fabricacion = self.fecha_fabricacion_input.text.strip()
        fecha_vencimiento = self.fecha_vencimiento_input.text.strip()
        tipo_modelo = self.tipo_modelo_input.text.strip().upper()
        peso = self.peso_input.text.strip().upper()
        talla = self.talla_spinner.text.strip().upper()
        procedencia = self.procedencia_input.text.strip().upper()

        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO chalecos_receptora (lote, numero_serie, fabricante, fecha_fabricacion, fecha_vencimiento, tipo_modelo, peso, talla, procedencia)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (lote, numero_serie, fabricante, fecha_fabricacion, fecha_vencimiento, tipo_modelo, peso, talla, procedencia))
        self.conn.commit()
        
        chaleco_id = cursor.lastrowid
        return chaleco_id

    def generar_qr(self, chaleco_id):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT id, lote, numero_serie  FROM chalecos_receptora  WHERE id = ?
        ''', (chaleco_id,))  
        chaleco = cursor.fetchone()

        if chaleco:
            id_chaleco, lote, numero_serie = chaleco
            datos_qr = f"ID: {id_chaleco}, Lote: {lote}, Serie: {numero_serie}"
            
            qr = qrcode.make(datos_qr)
            buffer = BytesIO()
            qr.save(buffer, format="PNG")
            buffer.seek(0)

            self.guardar_imagen_qr(buffer.getvalue(), id_chaleco)
            
            #DEBUG QUE GENERO
            #print(f"QR generado para chaleco {id_chaleco} - Lote: {lote}, Número de Serie: {numero_serie}")

            image_texture = CoreImage(buffer, ext="png").texture
            image = KivyImage(texture=image_texture, size_hint=(1, 1))

            layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
            layout.add_widget(Label(text='Chaleco registrado correctamente', size_hint=(1, 0.2)))
            layout.add_widget(image)

            botones_layout = BoxLayout(size_hint=(1, 0.2), spacing=10)
            btn_cerrar = Button(text='Cerrar')
            btn_imprimir = Button(text='Imprimir')
            botones_layout.add_widget(btn_imprimir)
            botones_layout.add_widget(btn_cerrar)
            layout.add_widget(botones_layout)

            popup = Popup(title='Registro Exitoso', content=layout, size_hint=(0.6, 0.6))
            btn_cerrar.bind(on_press=popup.dismiss)
            btn_imprimir.bind(on_press=lambda _: self.imprimir_qr(buffer, popup))
            popup.open()
        else:
            self.mostrar_popup('Error', 'No se encontró el chaleco en la base de datos.')

    def activar_boton_secreto(self, *args):
        posicion = Window.mouse_pos
        if posicion[0] < 50 and posicion[1] > (Window.height - 50):
            self.solicitar_clave(None)  
    def crear_pdf_qr(self, qr_image_data, lote):
        temp_pdf_path = os.path.join(tempfile.gettempdir(), f"qr_chaleco_{lote}.pdf")
        
        c = canvas.Canvas(temp_pdf_path, pagesize=letter)
        width, height = letter
        
        c.setFont("Helvetica", 10)
        c.drawString(100, height - 100, f"Chaleco - Lote: {lote}")
        
        qr_temp_path = os.path.join(tempfile.gettempdir(), f"qr_{lote}.png")
        with open(qr_temp_path, 'wb') as f:
            f.write(qr_image_data.getvalue())

        c.drawImage(qr_temp_path, 200, height - 300, 150, 150)        
        c.showPage()
        c.save()
        
        os.remove(qr_temp_path)
        
        return temp_pdf_path

    def guardar_imagen_qr(self, qr_bytes, chaleco_id):
        """Guardar la imagen del código QR en la base de datos usando el id del chaleco"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                UPDATE chalecos_receptora SET qr_image = ? WHERE id = ?
            ''', (sqlite3.Binary(qr_bytes), chaleco_id))  
            self.conn.commit()
            print(f"QR guardado en la base de datos para chaleco ID: {chaleco_id}")
        except Exception as e:
            print(f"Error al guardar el QR para el chaleco ID {chaleco_id}: {e}")

    def imprimir_qr(self, qr_image_data, popup):
        lote = self.lote_input.text
        
        pdf_path = self.crear_pdf_qr(qr_image_data, lote)
        try:
            if os.name == 'nt':  
                os.startfile(pdf_path)  
            elif os.name == 'posix':  
                os.system(f"open {pdf_path}")
            else:
                self.mostrar_popup('Error', 'No se pudo abrir el archivo para imprimir.')
        except Exception as e:
            self.mostrar_popup('Error', f'Error al intentar abrir el archivo: {str(e)}')

        popup.dismiss()

    def finalizar_lote(self, instance):

        lote_actual = self.lote_input.text
        if not lote_actual:
            self.mostrar_popup('Error', 'No se ha comenzado ningún lote.')
            return

        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM chalecos_receptora WHERE lote = ?", (lote_actual,))
        chalecos = cursor.fetchall()

        if chalecos:
            for chaleco in chalecos:
                chaleco_id = chaleco[0]
                self.generar_qr(chaleco_id)

                layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
                layout.add_widget(Label(text='El lote ha sido finalizado y los chalecos han sido registrados.'))

                btn_cerrar = Button(text='Cerrar', size_hint=(1, 0.2))
                layout.add_widget(btn_cerrar)

                popup = Popup(title='Lote Finalizado', content=layout, size_hint=(0.8, 0.4))

                btn_cerrar.bind(on_press=popup.dismiss)
                popup.open()
        else:
            self.mostrar_popup('Error', 'No se encontraron chalecos en este lote.')

        chaleco_id = self.guardar_chaleco()
            
        # DEBUG: Verifica que chaleco_id es diferente para cada chaleco
        #print(f"Generando QR para chaleco ID: {chaleco_id}")

        self.generar_qr(chaleco_id)
        self.limpiar_campos()
        
        self.add_chaleco_button.disabled = True
        self.finalizar_lote_button.disabled = True
        self.comenzar_lote_button.disabled = False          

    def abrir_pantalla_transmision(self, instance):
        pass

    def enviar_seleccion(self, instance):
        registros_seleccionados = [registro for checkbox, registro in self.checkboxes if checkbox.active]

        if registros_seleccionados:
            datos_transmitir = []
            for reg in registros_seleccionados:
                if isinstance(reg[10], bytes):
                    qr_image_base64 = base64.b64encode(reg[10]).decode('utf-8')
                elif isinstance(reg[10], str):
                    qr_image_base64 = reg[10] 
                else:
                    qr_image_base64 = 'No QR available'
                datos_transmitir.append({
                    "Id": reg[0],
                    "Lote": reg[1],
                    "Número de Serie": reg[2],
                    "Fabricante": reg[3],
                    "Fecha de Fabricación": reg[4],
                    "Fecha de Vencimiento": reg[5],
                    "Tipo de Modelo": reg[6],
                    "Peso": reg[7],
                    "Talla": reg[8],
                    "Procedencia": reg[9],
                    "QR Image": qr_image_base64
                })

            self.transmitir_wifi(datos_transmitir)
            self.marcar_registros_como_transmitidos(registros_seleccionados)
            self.mostrar_popup('Éxito', 'Registros empaquetado transmitiendo ...', auto_close_time=2)
        else:
            self.mostrar_popup('Error', 'No se seleccionaron registros para transmitir')

    def marcar_registros_como_transmitidos(self, registros_seleccionados):
        cursor = self.conn.cursor()
        for registro in registros_seleccionados:
            print(f"Marcando transmitido=1 para ID: {registro[0]}, Lote: {registro[1]}")  # Depuración
            cursor.execute("UPDATE chalecos_receptora SET transmitido=1 WHERE id=? AND lote=?", (registro[0], registro[1]))
        self.conn.commit()

    def transmitir_wifi(self, datos):
        try:
            puerto_destino = 8000
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            sock.settimeout(5) 
            sock.connect((self.ip_destino, puerto_destino))
            datos_json = json.dumps({"data": datos})

            sock.sendall(datos_json.encode('utf-8'))
            try:
                respuesta = sock.recv(1024)  
                if respuesta.decode() == "OK":
                    self.mostrar_popup('Éxito', 'Datos transmitidos y confirmados por el servidor')
                else:
                    self.mostrar_popup('Error', f'Error en la confirmación del servidor: {respuesta.decode()}')
            except socket.timeout:
                self.mostrar_popup('Finalizados', 'Ok', auto_close_time=2) # Poner linea de cerrar programa
                
            print("______sock.close_____________")
            sock.close()

        except socket.timeout:
            self.mostrar_popup('Error', 'Error de tiempo de espera en la transmisión (timeout)', auto_close_time=2)
        except Exception as e:
            self.mostrar_popup('Error', f'Error al transmitir: {str(e)}', auto_close_time=5)
        finally:
            sock.close()
        return
        
    def ver_registro(self, instance):
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        scroll_view = ScrollView(size_hint=(1, 0.9))
        grid_layout = GridLayout(cols=4, size_hint_y=None, spacing=10)
        grid_layout.bind(minimum_height=grid_layout.setter('height'))
        font_size = '8sp'  
        column_width = 0.25  

        titulos_por_destruir = ["Lote (Por Destruir)", "Número de Serie", "Fabricante", "Tipo/Modelo"]
        titulos_destruidos = ["Lote (Destruidos)", "Número de Serie", "Fabricante", "Tipo/Modelo"]

        for titulo in titulos_por_destruir:
            label = Label(text=titulo, bold=True, size_hint_y=None, height=40, size_hint_x=column_width, font_size=font_size, halign='center', valign='middle')
            label.bind(size=label.setter('text_size'))  # Center the text
            grid_layout.add_widget(label)

        cursor = self.conn.cursor()
        cursor.execute("SELECT lote, numero_serie, fabricante, tipo_modelo FROM chalecos_receptora WHERE destruido = 0")
        por_destruir = cursor.fetchall()

        for registro in por_destruir:
            for campo in registro:
                label = Label(text=str(campo), size_hint_y=None, height=40, size_hint_x=column_width, font_size=font_size, halign='center', valign='middle')
                label.bind(size=label.setter('text_size'))  # Center the text
                grid_layout.add_widget(label)

        # Add a spacer to separate the two sections
        for _ in range(4):  # Add 4 empty labels to keep the columns aligned
            spacer = Label(text="", size_hint_y=None, height=40, size_hint_x=column_width)
            grid_layout.add_widget(spacer)

        # Titles for "Destruidos"
        for titulo in titulos_destruidos:
            label = Label(text=titulo, bold=True, size_hint_y=None, height=40, size_hint_x=column_width, font_size=font_size, halign='center', valign='middle')
            label.bind(size=label.setter('text_size'))  # Center the text
            grid_layout.add_widget(label)

        # Query for "Destruidos" records (destruido = 1)
        cursor.execute("SELECT lote, numero_serie, fabricante, tipo_modelo FROM chalecos_receptora WHERE destruido = 1")
        destruidos = cursor.fetchall()

        # Add each "Destruidos" record to the grid layout
        for registro in destruidos:
            for campo in registro:
                label = Label(text=str(campo), size_hint_y=None, height=40, size_hint_x=column_width, font_size=font_size, halign='center', valign='middle')
                label.bind(size=label.setter('text_size'))  # Center the text
                grid_layout.add_widget(label)

        scroll_view.add_widget(grid_layout)
        layout.add_widget(scroll_view)

        # Close button
        cerrar_button = Button(text='Cerrar', size_hint=(1, 0.1), height=50)
        cerrar_button.bind(on_press=lambda x: self.popup_ver_registro.dismiss())
        layout.add_widget(cerrar_button)

        self.popup_ver_registro = Popup(
            title='Registro de Chalecos',
            content=layout,
            size_hint=(0.8, 0.8)
        )
        self.popup_ver_registro.open()

    def on_key_down(self, window, key, *args):
        if key == 273:  # Código de tecla para Flecha arriba
            self.cambiar_foco(-1)
        elif key == 274:  # Código de tecla para Flecha abajo
            self.cambiar_foco(1)

    def cambiar_foco(self, direction):
        focus_order = [
            self.numero_serie_input,
            self.fabricante_input,
            self.fecha_fabricacion_input,
            self.fecha_vencimiento_input,
            self.tipo_modelo_input,
            self.peso_input,
            self.talla_spinner,
            self.procedencia_input
        ]

        current_focus = next(
            (widget for widget in focus_order if hasattr(widget, 'focus') and widget.focus), None
        )

        if current_focus:
            current_index = focus_order.index(current_focus)
            next_index = (current_index + direction) % len(focus_order)
            
            next_widget = focus_order[next_index]
            if hasattr(next_widget, 'focus'):
                next_widget.focus = True
            else:
                for i in range(1, len(focus_order)):
                    next_index = (current_index + direction + i) % len(focus_order)
                    next_widget = focus_order[next_index]
                    if hasattr(next_widget, 'focus'):
                        next_widget.focus = True
                        break  

    def campos_llenos(self):
        return all([
            self.numero_serie_input.text,
            self.fabricante_input.text,
            self.fecha_fabricacion_input.text,
            self.fecha_vencimiento_input.text,
            self.tipo_modelo_input.text,
            self.peso_input.text,
            self.talla_spinner.text,
            self.procedencia_input.text
        ])

    def validar_fechas(self):
        """Valida que las fechas tengan el formato correcto"""
        try:
            parser.parse(self.fecha_fabricacion_input.text)
            parser.parse(self.fecha_vencimiento_input.text)
            return True
        except ValueError:
            self.mostrar_popup('Error', 'El formato de fecha es incorrecto. Por favor use el formato YYYY-MM-DD')
            return False

    def mostrar_popup(self, titulo, mensaje, boton_texto='Cerrar', auto_close_time=None):
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        label = Label(text=mensaje, size_hint=(1, 0.8), halign='center', valign='middle')
        label.bind(size=label.setter('text_size')) 
        layout.add_widget(label)
        
        btn = Button(text=boton_texto, size_hint=(1, 0.2))
        btn.bind(on_press=lambda x: self.popup_actual.dismiss()) 
        layout.add_widget(btn)

        self.popup_actual = Popup(
            title=titulo,
            content=layout,
            size_hint=(0.5, 0.3),  
            auto_dismiss=False 
        )
        self.popup_actual.open()

        if auto_close_time:
            Clock.schedule_once(lambda dt: self.popup_actual.dismiss(), auto_close_time)

    def abrir_datepicker_fabricacion(self, instance):
        layout = DatePicker(on_select=self.set_fecha_fabricacion)
        popup = Popup(title='Seleccionar Fecha de Fabricación', content=layout, size_hint=(0.8, 0.6))
        layout.parent = popup  
        popup.open()

    def abrir_datepicker_vencimiento(self, instance):
        layout = DatePicker(on_select=self.set_fecha_vencimiento)
        popup = Popup(title='Seleccionar Fecha de Vencimiento', content=layout, size_hint=(0.8, 0.6))
        layout.parent = popup  
        popup.open()

    def set_fecha_fabricacion(self, fecha):
        self.fecha_fabricacion_input.text = fecha

    def set_fecha_vencimiento(self, fecha):
        self.fecha_vencimiento_input.text = fecha

#!=============================PARTE DE FUSION=======================
    def combinar_imagenes(self, qr_id):
   
        base_desktop = r"C:\Users\Lgistica\Desktop"
        img_folder = os.path.join(base_desktop, 'Imagenes') 

        
        if not os.path.exists(img_folder):
            os.makedirs(img_folder)

     
        entrada_path = f"{qr_id}_ENTRADA.png"
        salida_path = f"{qr_id}_SALIDA.png"
        imagen_final_path = os.path.join(img_folder, f"{qr_id}_combinada.png") 

        if not (os.path.exists(entrada_path) and os.path.exists(salida_path)):
            print("Error: Una o ambas imágenes no existen.")
            return

        entrada_img = cv2.imread(entrada_path)
        salida_img = cv2.imread(salida_path)

        entrada_img = cv2.resize(entrada_img, (800, 600))
        salida_img = cv2.resize(salida_img, (800, 600))

    
        imagen_combinada = cv2.vconcat([entrada_img, salida_img])

        cv2.putText(imagen_combinada, "ENTRADA", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        cv2.putText(imagen_combinada, "SALIDA", (10, 650), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

        cv2.imwrite(imagen_final_path, imagen_combinada)
        print(f"Imagen combinada guardada en: {imagen_final_path}")

            # Eliminar imágenes parciales
        try:
            os.remove(entrada_path)
            os.remove(salida_path)
            print("Imágenes parciales eliminadas correctamente.")
        except OSError as e:
            print(f"Error al eliminar las imágenes parciales: {e}")

    def verificar_destruccion(self, qr_value):
        """Realiza el proceso completo de destrucción del chaleco."""
        try:
            print(f"Comenzando el proceso de destrucción para QR: {qr_value}")

  
            self.enviar_senal_arduino()

            time.sleep(20)
            print("Esperando 20 segundos antes de abrir la cámara 2.")

            if not self.verificar_qr_con_camara_2(qr_value):
                print("Error: No se detectó el QR después de 60 segundos.")
                self.mostrar_popup("Error", "QR no detectado. Proceso fallido.")
                return

            qr_parts = qr_value.split(", ")
            qr_id = qr_parts[0].split(": ")[1]
            qr_lote = qr_parts[1].split(": ")[1]
            qr_serie = qr_parts[2].split(": ")[1]
            self.capturar_imagen_con_texto(f"{qr_id}_SALIDA.png", qr_id, qr_lote, qr_serie)

            cursor = self.conn.cursor()
            fecha_actual = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  
            cursor.execute("""
                UPDATE chalecos_receptora 
                SET destruido = 1, fecha_destruido = ?
                WHERE id = ? AND lote = ? AND numero_serie = ?
            """, (fecha_actual, qr_id, qr_lote, qr_serie))
            self.conn.commit()

            self.combinar_imagenes(qr_id)


            Clock.schedule_once(lambda dt: self.habilitar_boton_escanear_qr(), 0)
            print(f"Proceso de destrucción para QR {qr_value} completado con éxito.")

        except Exception as e:
            print(f"Error en el proceso de destrucción: {e}")

    def enviar_senal_arduino(self):
        """Envía una señal al Arduino para activar el relé."""
        try:
            if self.arduino:
                self.arduino.write(b'ACTIVATE\n')
                print("Señal enviada al Arduino para activar el relé.")
            else:
                print("Arduino no conectado.")
        except Exception as e:
            print(f"Error al enviar señal al Arduino: {e}")

    def verificar_qr_con_camara_2(self, qr_value):
        """Abre la cámara 2 y verifica la presencia del QR. Si el QR no aparece en 60 segundos, genera un error."""
        print("Abriendo cámara 2 para verificar QR...")
        #! Camara de salida
        cam = cv2.VideoCapture(2)  # Cámara 2
        start_time = time.time()

        if not cam.isOpened():
            print("Error: No se puede abrir la cámara 2.")
            return False

        while time.time() - start_time < 60:  
            ret, frame = cam.read()
            if not ret:
                print("Error al capturar imagen de la cámara 2.")
                continue

            qr_value_detectado = self.decode_qr(frame)
            if qr_value_detectado == qr_value:
                print(f"QR detectado correctamente: {qr_value_detectado}")
                
                if self.arduino:
                    self.arduino.write(b'STOP\n')
                    print("Señal de parada enviada al Arduino.")
                cam.release()
                return True

        cam.release()
        return False
    def decode_qr(self, frame):
        """Decodifica el QR de una imagen y devuelve su valor."""
        try:
            scan_manager = ScanManager()  
            if scan_manager.count_barcodes(frame) > 0:
                result = scan_manager.reader.decode_buffer(frame)[0].barcode_text
                return result
            return ""
        except Exception as e:
            print(f"Error al decodificar QR: {e}")
            return ""
    
    def capturar_imagen_con_texto(self, nombre_archivo, qr_id, qr_lote, qr_serie):
#! ACA TIENE QUE IR LA CAMARA DE SALIDA        
        cam = cv2.VideoCapture(2)  # Abre la cámara

        if not cam.isOpened():
            print("Error: No se puede abrir la cámara.")
            return

        ret, frame = cam.read()
        if not ret:
            print("Error al capturar la imagen.")
            cam.release()
            return

        frame = cv2.resize(frame, (800, 600))
        
        fecha_hora_actual = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # Text details (normal color)
        texto_normal = f"ID: {qr_id}, Lote: {qr_lote}, Serie: {qr_serie}\nFecha: {fecha_hora_actual}"
        
        # "DESTRUIDO" (in red)
        texto_destruido = "DESTRUIDO"
        
        # Escribir el texto normal (ID, Lote, Serie, Fecha) en blanco (or another color)
        y0, dy = 50, 30 
        color_normal = (255, 255, 255)  
        for i, line in enumerate(texto_normal.split('\n')):
            y = y0 + i * dy
            cv2.putText(frame, line, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 1, color_normal, 2, cv2.LINE_AA)
        
        y_destruido = y0 + len(texto_normal.split('\n')) * dy
        cv2.putText(frame, texto_destruido, (10, y_destruido), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, cv2.LINE_AA)


        cv2.imwrite(nombre_archivo, frame)
        cam.release()
        cv2.destroyAllWindows()

        print(f"Captura guardada como: {nombre_archivo}")

    def habilitar_boton_escanear_qr(self):
        """Rehabilita el botón de escaneo de QR."""
        self.scan_qr_button.disabled = False
        print("Botón de escaneo QR habilitado nuevamente.")

    def scan_qr(self, instance):
        global qr_last_seen, qr_last_time, qr_timer_started
        
        if not self.arduino or not self.arduino.is_open:
            self.mostrar_popup("Error", "Arduino no conectado. No se puede iniciar el escaneo.")
            return
        
#! ACA TIENE QUE IR LA CAMARA DE ENTRADA         
        cap = cv2.VideoCapture(1)  # Abre la cámara local
        scan_manager = ScanManager()  

        if not cap.isOpened():
            print("Error: No se puede abrir la cámara.")
            return

        qr_accumulated_time = 0  
        threshold_5_seconds = False  
        stop_scan = False  

        while not stop_scan:
            ret, frame = cap.read()
            if not ret:
                print("Error al capturar la imagen")
                break

            frame = cv2.resize(frame, (640, 480))

            frame_with_qr = scan_manager.frame_overlay(frame)

            if frame_with_qr is not None:
                qr_value = scan_manager.reader.decode_buffer(frame)[0].barcode_text if scan_manager.count_barcodes(frame) > 0 else ""

                if qr_value:
                    if qr_value == qr_last_seen:
                        if not qr_timer_started:
                            qr_last_time = time.time()
                            qr_timer_started = True
                        else:
                            qr_accumulated_time += time.time() - qr_last_time
                            qr_last_time = time.time()

                            if qr_accumulated_time >= 5 and not threshold_5_seconds:
                                chaleco_existe, esta_destruido = self.is_qr_in_database(qr_value)
                                if chaleco_existe:
                                    if esta_destruido:
                                        self.mostrar_popup('Información', 'El chaleco ya está destruido.')
                                        self.destruction_button.disabled = True  
                                        self.scan_qr_button.disabled = False  

                                        text = "DESTRUIDO"
                                        font = cv2.FONT_HERSHEY_SIMPLEX
                                        font_scale = 2
                                        thickness = 4
                                        color = (0, 0, 255) 
                                        text_size = cv2.getTextSize(text, font, font_scale, thickness)[0]
                                        text_x = (frame_with_qr.shape[1] - text_size[0]) // 2  
                                        text_y = (frame_with_qr.shape[0] + text_size[1]) // 2  

                                        cv2.putText(frame_with_qr, text, (text_x, text_y), font, font_scale, color, thickness)    
                                        time.sleep(3)
                                        cap.release()
                                        cv2.destroyAllWindows()
                                    else:
                                        print("QR detectado y estable por 5 segundos. Habilitando botón de destrucción.")
                                        self.destruction_button.disabled = False  
                                        self.scan_qr_button.disabled = True  
                                        cv2.putText(frame_with_qr, "QR válido", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                                        threshold_5_seconds = True
                                        stop_scan = True  
                                else:
                                    print("QR no válido, no se habilitará la destrucción.")
                                    threshold_5_seconds = False
                    else:
                        qr_last_seen = qr_value
                        qr_timer_started = False
                        qr_accumulated_time = 0
                        threshold_5_seconds = False

                    if self.is_qr_in_database(qr_value):
                        cv2.putText(frame_with_qr, f"QR: {qr_value}", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                    else:
                        cv2.putText(frame_with_qr, "QR no existe", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

                else:
                    qr_last_seen = ""
                    qr_timer_started = False
                    qr_accumulated_time = 0

                cv2.imshow('QR Scanner', frame_with_qr)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                stop_scan = True

        cap.release()
        cv2.destroyAllWindows()
    
    def habilitar_boton_destruccion(self):
        """Habilita el botón de destrucción y deshabilita el de escanear QR."""
        self.destruction_button.disabled = False
        self.scan_qr_button.disabled = True  
        print("Botón de destrucción habilitado y botón de escaneo deshabilitado.")

    def obtener_datos_chaleco(self, qr_value):

        qr_parts = qr_value.split(", ")
        qr_id = qr_parts[0].split(": ")[1]
        qr_lote = qr_parts[1].split(": ")[1]
        qr_serie = qr_parts[2].split(": ")[1]
        

        cursor = self.conn.cursor()
        cursor.execute("SELECT id, lote, numero_serie FROM chalecos_receptora WHERE id = ? AND lote = ? AND numero_serie = ?", (qr_id, qr_lote, qr_serie))
        data = cursor.fetchone()

        if data:
            return data
        else:
            print("No se encontró el chaleco en la base de datos.")
            return None

    def on_destruction_button(self, instance):
        global qr_last_seen
        print("Destrucción en proceso...")
        print(f"QR último visto: {qr_last_seen}")
        
        self.destruction_button.disabled = True
        self.scan_qr_button.disabled = True

        chaleco_data = self.obtener_datos_chaleco(qr_last_seen)
        if chaleco_data:
            id, lote, numero_serie = chaleco_data
            nombre_archivo = f"{id}_ENTRADA.png"
            
            self.capturar_imagen(nombre_archivo, chaleco_data)

            destruccion_thread = threading.Thread(target=self.verificar_destruccion, args=(qr_last_seen,))
            destruccion_thread.start()
    
    def is_qr_in_database(self, qr_value):
        try:

            qr_parts = qr_value.split(", ")

            if len(qr_parts) < 3:
                print(f"Error: QR no tiene suficientes partes. Valor QR: {qr_value}")
                return False, False 
            

            qr_id = qr_parts[0].split(": ")
            qr_lote = qr_parts[1].split(": ")
            qr_serie = qr_parts[2].split(": ")


            if len(qr_id) < 2 or len(qr_lote) < 2 or len(qr_serie) < 2:
                print(f"Error: Formato incorrecto en alguna parte del QR. Valor QR: {qr_value}")
                return False, False
            

            qr_id = qr_id[1]
            qr_lote = qr_lote[1]
            qr_serie = qr_serie[1]

            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM chalecos_receptora WHERE id = ? AND lote = ? AND numero_serie = ?", 
                        (qr_id, qr_lote, qr_serie))
            data = cursor.fetchone()

            return data is not None, data[12] == 1 if data else False
        
        except IndexError:
            print(f"Error de índice: Formato del QR no es válido. Valor QR: {qr_value}")
            return False, False 
        except Exception as e:
            print(f"Error al verificar el QR en la base de datos: {e}")
            return False, False


    def capturar_imagen(self, nombre_archivo, chaleco_data):
        id, lote, numero_serie = chaleco_data
        cam = cv2.VideoCapture(1)  # Abre la cámara

        if not cam.isOpened():
            print("Error: No se puede abrir la cámara.")
            return

        ret, frame = cam.read()
        if not ret:
            print("Error al capturar la imagen.")
            cam.release()
            return

        frame = cv2.resize(frame, (800, 600))
        texto = f"ID: {id}, Lote: {lote}, Serie: {numero_serie}, Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        cv2.putText(frame, texto, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        cv2.imwrite(nombre_archivo, frame)
        cam.release()
        cv2.destroyAllWindows()

class ScanManager:
    def __init__(self):
        self.reader = BarcodeReader()
        

        self.settings = self.reader.get_runtime_settings()
        self.settings.barcode_format_ids = EnumBarcodeFormat.BF_QR_CODE  
        self.settings.expected_barcodes_count = 1  
        self.settings.min_result_confidence = 30  
        

        self.reader.update_runtime_settings(self.settings)

    def count_barcodes(self, frame):
        """Decodifica los códigos QR en el frame"""
        results = self.reader.decode_buffer(frame)
        if results is None:
            return 0
        return len(results)

    def frame_overlay(self, frame):
        """Dibuja el QR en el frame si lo detecta"""
        frame_cp = frame.copy()
        try:
            results = self.reader.decode_buffer(frame_cp)
            if results is not None:
                for result in results:
                    points = result.localization_result.localization_points
                    cv2.line(frame_cp, points[0], points[1], (0, 255, 0), 2)
                    cv2.line(frame_cp, points[1], points[2], (0, 255, 0), 2)
                    cv2.line(frame_cp, points[2], points[3], (0, 255, 0), 2)
                    cv2.line(frame_cp, points[3], points[0], (0, 255, 0), 2)
                    cv2.putText(frame_cp, result.barcode_text, points[0], cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255))
            return frame_cp
        except BarcodeReaderError as e:
            print(e)
            return None

if __name__ == '__main__':
    ChalecoApp().run()
