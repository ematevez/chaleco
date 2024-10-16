import tempfile
import os
import base64
import json
import datetime
import random
import socket
import sqlite3
import qrcode

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
from kivy.uix.image import Image
from kivy.core.image import Image as CoreImage
from kivy.uix.spinner import Spinner


from kivy.clock import Clock
from reportlab.pdfgen import canvas
from io import BytesIO
from dateutil import parser
from reportlab.lib.pagesizes import letter

from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.fernet import Fernet


def cargar_clave():
    # Contraseña almacenada en el código (menos seguro)
    password = b'I9O0OKFRGYHJ4EP9AJIK7MA3J'
        
    with open('encryption_key.key', 'rb') as key_file:
        salt = key_file.readline().strip()
        encrypted_key = key_file.readline().strip()

    # Derivar la clave a partir de la contraseña y la sal
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    key_encrypted = base64.urlsafe_b64encode(kdf.derive(password))

    # Usar la clave derivada para descifrar la clave Fernet
    fernet = Fernet(key_encrypted)
    key = fernet.decrypt(encrypted_key)
    
    return Fernet(key)

# Cargar la clave de encriptación
fernet = cargar_clave()

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
            # Mostrar mensaje de error o manejar selección incompleta
            popup = Popup(
                title='Error',
                content=Label(text='Debe seleccionar Año, Mes y Día.'),
                size_hint=(None, None),
                size=(400, 200)
            )
            popup.open()

class ChalecoApp(App):

    def build(self):
        # Configurar la ventana en pantalla completa
        Window.fullscreen = True  # Puedes usar 'auto' o True
        self.conn = sqlite3.connect('chalecos.db', check_same_thread=False)
        self.create_db()
        self.root = BoxLayout(orientation='vertical', padding=10, spacing=10)
        self.create_widgets()

        # IP por defecto para transmitir WiFi
        self.ip_destino = '192.168.10.142'  # Esta es la IP inicial por defecto
        
        # Habilitar el uso de las teclas de flecha para moverse entre los campos de texto
        Window.bind(on_key_down=self.on_key_down)
        
        return self.root

    # Añadir columna qr_imagen en la tabla si no existe
    def create_db(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chalecos (
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
                transmitido INTEGER DEFAULT 0
            )
        ''')
        self.conn.commit()


    def create_widgets(self):
        # Crear campos de texto con botones para seleccionar fecha
        self.lote_input = TextInput(hint_text='Lote (autogenerado)', disabled=True)
        self.numero_serie_input = TextInput(hint_text='Número de Serie')
        self.fabricante_input = TextInput(hint_text='Fabricante')
        
        # Fecha de Fabricación
        self.fecha_fabricacion_input = TextInput(hint_text='Fecha de Fabricación (YYYY-MM-DD)', readonly=True)
        self.btn_fecha_fabricacion = Button(text='Seleccionar Fecha', size_hint=(None, None), size=(150, 44))
        self.btn_fecha_fabricacion.bind(on_press=self.abrir_datepicker_fabricacion)
        
        # Fecha de Vencimiento
        self.fecha_vencimiento_input = TextInput(hint_text='Fecha de Vencimiento (YYYY-MM-DD)', readonly=True)
        self.btn_fecha_vencimiento = Button(text='Seleccionar Fecha', size_hint=(None, None), size=(150, 44))
        self.btn_fecha_vencimiento.bind(on_press=self.abrir_datepicker_vencimiento)
        
        self.tipo_modelo_input = TextInput(hint_text='Tipo/Modelo')
        self.peso_input = TextInput(hint_text='Peso')
        self.talla_spinner = Spinner(text='Seleccionar Talla',values=('XS', 'S', 'M', 'L', 'XL', 'XXL'),size_hint=(1, None), height=40)
        self.procedencia_input = TextInput(hint_text='Procedencia')

        # Crear botones
        self.comenzar_lote_button = Button(text='Comenzar Lote')
        self.add_chaleco_button = Button(text='Agregar Chaleco', disabled=True)
        self.finalizar_lote_button = Button(text='Finalizar Lote', disabled=True)
        self.ver_registro_button = Button(text='Ver Registro')
        self.transmitir_wifi_button = Button(text='Transmitir WiFi')
        
        # Botón con el ícono de engranaje
        self.boton_config_ip = Button(size_hint=(None, None), size=(20, 20), background_normal='engranaje.png')
        self.boton_config_ip.bind(on_press=self.solicitar_clave)

        # Asociar los botones a sus funciones
        self.comenzar_lote_button.bind(on_press=self.comenzar_lote)
        self.add_chaleco_button.bind(on_press=self.agregar_chaleco)
        self.finalizar_lote_button.bind(on_press=self.finalizar_lote)
        self.ver_registro_button.bind(on_press=self.ver_registro)
        self.transmitir_wifi_button.bind(on_press=self.abrir_pantalla_transmision)  # Nuevo popup para transmisión

        # Añadir widgets a la interfaz
        self.root.add_widget(self.lote_input)
        self.root.add_widget(self.numero_serie_input)
        self.root.add_widget(self.fabricante_input)
        
        # Layout para Fecha de Fabricación
        fecha_fabricacion_layout = BoxLayout(orientation='horizontal', size_hint=(1, None), height=40, spacing=10)
        fecha_fabricacion_layout.add_widget(self.fecha_fabricacion_input)
        fecha_fabricacion_layout.add_widget(self.btn_fecha_fabricacion)
        self.root.add_widget(fecha_fabricacion_layout)
        
        # Layout para Fecha de Vencimiento
        fecha_vencimiento_layout = BoxLayout(orientation='horizontal', size_hint=(1, None), height=40, spacing=10)
        fecha_vencimiento_layout.add_widget(self.fecha_vencimiento_input)
        fecha_vencimiento_layout.add_widget(self.btn_fecha_vencimiento)
        self.root.add_widget(fecha_vencimiento_layout)
        
        self.root.add_widget(self.tipo_modelo_input)
        self.root.add_widget(self.peso_input)
        # self.root.add_widget(self.talla_input)
        self.root.add_widget(self.talla_spinner)
        self.root.add_widget(self.procedencia_input)
        self.root.add_widget(self.comenzar_lote_button)
        self.root.add_widget(self.add_chaleco_button)
        self.root.add_widget(self.finalizar_lote_button)
        self.root.add_widget(self.transmitir_wifi_button)
        self.root.add_widget(self.ver_registro_button)
        self.root.add_widget(self.boton_config_ip)
        
    # Función que muestra el popup para solicitar la clave
    def solicitar_clave(self, instance):
        popup_content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        clave_input = TextInput(hint_text='Ingrese clave', password=True, multiline=False)

        btn_confirmar = Button(text='Confirmar')
        btn_confirmar.bind(on_press=lambda x: self.verificar_clave(clave_input.text))

        popup_content.add_widget(clave_input)
        popup_content.add_widget(btn_confirmar)

        self.popup_clave = Popup(title='Ingresar clave', content=popup_content, size_hint=(0.6, 0.4))
        self.popup_clave.open()

    # Función para verificar la clave
    def verificar_clave(self, clave_ingresada):
        if clave_ingresada == '31521775':
            self.popup_clave.dismiss()  # Cerrar el popup de clave
            self.mostrar_popup_config_ip()  # Mostrar el popup para configurar la IP
        else:
            self.mostrar_popup('Error', 'Clave incorrecta')

    # Función para mostrar el popup de configuración de IP
    def mostrar_popup_config_ip(self):
        popup_content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        ip_input = TextInput(hint_text='Ingrese nueva IP', text=self.ip_destino, multiline=False)

        btn_guardar = Button(text='Guardar IP')
        btn_guardar.bind(on_press=lambda x: self.guardar_ip(ip_input.text))

        popup_content.add_widget(ip_input)
        popup_content.add_widget(btn_guardar)

        self.popup_ip = Popup(title='Configurar IP', content=popup_content, size_hint=(0.6, 0.4))
        self.popup_ip.open()

    # Función para guardar la nueva IP
    def guardar_ip(self, nueva_ip):
        self.ip_destino = nueva_ip  # Actualizar la IP de destino
        self.popup_ip.dismiss()  # Cerrar el popup de configuración
        self.mostrar_popup('Éxito', f'IP actualizada a {nueva_ip}')



# Validar que la fecha de vencimiento sea mayor a la fecha de fabricación
    def validar_orden_fechas(self):
        """Valida que la fecha de vencimiento sea mayor que la de fabricación"""
        try:
            # Asegúrate de usar datetime.datetime.strptime, no datetime.strptime
            fecha_fabricacion = datetime.datetime.strptime(self.fecha_fabricacion_input.text, '%Y-%m-%d')
            fecha_vencimiento = datetime.datetime.strptime(self.fecha_vencimiento_input.text, '%Y-%m-%d')
            
            # La fecha de vencimiento debe ser mayor a la de fabricación
            if fecha_vencimiento > fecha_fabricacion:
                return True
            else:
                return False
        except ValueError:
            # Manejo de error en caso de que el formato de fecha sea incorrecto
            self.mostrar_popup('Error', 'Formato de fecha incorrecto. Use YYYY-MM-DD')
            return False


    # Función para verificar duplicados
    def verificar_lote_existente(self, lote):
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM chalecos WHERE lote=?", (lote,))
        count = cursor.fetchone()[0]
        return count > 0
    
    # Modificar la función comenzar_lote para evitar duplicados
    def comenzar_lote(self, instance):
        lote_id = random.randint(1000, 9999)
        fecha_actual = datetime.datetime.now().strftime("%Y%m%d")
        lote_numero = f"L{lote_id}-{fecha_actual}"
        
        # Verificar si el lote ya existe
        if self.verificar_lote_existente(lote_numero):
            self.mostrar_popup('Error', 'Número de lote ya existe, intenta nuevamente.')
            return
        
        self.lote_input.text = lote_numero

        self.add_chaleco_button.disabled = False
        self.finalizar_lote_button.disabled = False
        self.transmitir_wifi_button.disabled = False
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
            
            # Guardar el chaleco y obtener su ID
            chaleco_id = self.guardar_chaleco()

            # Generar QR con la información del chaleco
            self.generar_qr(chaleco_id)  # Ahora se pasa el ID como argumento

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
        self.talla_spinner.text = ''
        self.procedencia_input.text = ''

    def guardar_chaleco(self):
        lote = self.lote_input.text
        numero_serie = self.numero_serie_input.text
        fabricante = self.fabricante_input.text
        fecha_fabricacion = self.fecha_fabricacion_input.text
        fecha_vencimiento = self.fecha_vencimiento_input.text
        tipo_modelo = self.tipo_modelo_input.text
        peso = self.peso_input.text
        talla = self.talla_spinner.text
        procedencia = self.procedencia_input.text

        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO chalecos (lote, numero_serie, fabricante, fecha_fabricacion, fecha_vencimiento, tipo_modelo, peso, talla, procedencia)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (lote, numero_serie, fabricante, fecha_fabricacion, fecha_vencimiento, tipo_modelo, peso, talla, procedencia))
        self.conn.commit()
        
        chaleco_id = cursor.lastrowid
        return chaleco_id

    def generar_qr(self, chaleco_id):
        # Extraer los datos del chaleco desde la base de datos utilizando el ID
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT id, lote, numero_serie  FROM chalecos  WHERE id = ?
        ''', (chaleco_id,))  # Ahora se busca por ID
        chaleco = cursor.fetchone()

        if chaleco:
            # Descomponer los datos del chaleco para formar el string del código QR
            id_chaleco, lote, numero_serie = chaleco

            # Incluir el `id` en los datos del código QR
            datos_qr = f"ID: {id_chaleco}, Lote: {lote}, Serie: {numero_serie}"

            # Generar el código QR con todos los datos extraídos
            qr = qrcode.make(datos_qr)
            buffer = BytesIO()
            qr.save(buffer, format="PNG")
            buffer.seek(0)

            # Guardar la imagen del QR en la base de datos (opcional)
            self.guardar_imagen_qr(buffer.getvalue(), id_chaleco)

            # Mostrar la imagen del QR en la interfaz
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

            

    def crear_pdf_qr(self, qr_image_data, lote):
        # Crear un archivo temporal para el PDF
        temp_pdf_path = os.path.join(tempfile.gettempdir(), f"qr_chaleco_{lote}.pdf")
        
        # Crear el lienzo de PDF
        c = canvas.Canvas(temp_pdf_path, pagesize=letter)
        width, height = letter
        
        # Agregar texto y el código QR
        c.setFont("Helvetica", 12)
        c.drawString(100, height - 100, f"Chaleco - Lote: {lote}")
        
        # Guardar la imagen del código QR en el PDF
        qr_temp_path = os.path.join(tempfile.gettempdir(), f"qr_{lote}.png")
        with open(qr_temp_path, 'wb') as f:
            f.write(qr_image_data.getvalue())

        
        # Colocar la imagen en el PDF
        c.drawImage(qr_temp_path, 200, height - 300, 150, 150)
        
        # Finalizar y guardar el PDF
        c.showPage()
        c.save()
        
        # Eliminar el archivo temporal del QR si ya no es necesario
        os.remove(qr_temp_path)
        
        return temp_pdf_path

    def guardar_imagen_qr(self, qr_bytes, chaleco_id):
        """Guardar la imagen del código QR en la base de datos usando el id del chaleco"""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE chalecos SET qr_image = ? WHERE id = ?
        ''', (sqlite3.Binary(qr_bytes), chaleco_id))  # Usar el id del chaleco para actualizar el registro
        self.conn.commit()

    def imprimir_qr(self, qr_image_data, popup):
        # Obtener el número de lote para el nombre del archivo PDF
        lote = self.lote_input.text
        
        # Generar el PDF con el QR
        pdf_path = self.crear_pdf_qr(qr_image_data, lote)
        
        # Intentar abrir el PDF para imprimir (dependiendo del sistema operativo)
        try:
            if os.name == 'nt':  # Windows
                os.startfile(pdf_path, "print")
            elif os.name == 'posix':  # Linux/Mac
                os.system(f"lpr {pdf_path}")
            else:
                self.mostrar_popup('Error', 'No se pudo abrir el archivo para imprimir.')
        except Exception as e:
            self.mostrar_popup('Error', f'Error al intentar imprimir: {str(e)}')

        # Cerrar el popup de éxito
        popup.dismiss()


    def finalizar_lote(self, instance):
        if not self.campos_llenos():
            self.mostrar_popup('Error', 'Complete todos los campos antes de finalizar el lote')
            return

        if not self.validar_fechas():
            self.mostrar_popup('Error', 'Formato de fecha incorrecto. Use YYYY-MM-DD')
            return

        self.guardar_chaleco()
        self.add_chaleco_button.disabled = True
        self.finalizar_lote_button.disabled = True
        self.comenzar_lote_button.disabled = False

        self.mostrar_popup('Lote Finalizado', 'El lote ha sido finalizado y los chalecos han sido registrados.')
    

    def abrir_pantalla_transmision(self, instance):
        # Crear la nueva ventana para seleccionar los registros
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        scroll_view = ScrollView(size_hint=(1, 0.9))
        grid_layout = GridLayout(cols=1, size_hint_y=None, spacing=10)
        grid_layout.bind(minimum_height=grid_layout.setter('height'))

        # Título de la lista
        titulo_layout = BoxLayout(orientation='horizontal', size_hint=(1, None), height=40)
        titulo_checkbox = Label(text='', size_hint=(0.1, 1))
        titulo_lote = Label(text='Lote', bold=True, size_hint=(0.3, 1))
        titulo_numero = Label(text='Número de Serie', bold=True, size_hint=(0.3, 1))
        titulo_fabricante = Label(text='Fabricante', bold=True, size_hint=(0.3, 1))
        titulo_layout.add_widget(titulo_checkbox)
        titulo_layout.add_widget(titulo_lote)
        titulo_layout.add_widget(titulo_numero)
        titulo_layout.add_widget(titulo_fabricante)
        grid_layout.add_widget(titulo_layout)

        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM chalecos WHERE transmitido=0")
        registros = cursor.fetchall()

        self.checkboxes = []

        for registro in registros:
            registro_layout = BoxLayout(orientation='horizontal', size_hint=(1, None), height=40)
            checkbox = CheckBox(size_hint=(0.1, 1))
            label_lote = Label(text=str(registro[0]), size_hint=(0.3, 1))
            label_numero = Label(text=str(registro[1]), size_hint=(0.3, 1))
            label_fabricante = Label(text=str(registro[2]), size_hint=(0.3, 1))
            registro_layout.add_widget(checkbox)
            registro_layout.add_widget(label_lote)
            registro_layout.add_widget(label_numero)
            registro_layout.add_widget(label_fabricante)
            grid_layout.add_widget(registro_layout)
            self.checkboxes.append((checkbox, registro))

        scroll_view.add_widget(grid_layout)
        layout.add_widget(scroll_view)

        # Botón de enviar
        enviar_button = Button(text='Enviar', size_hint=(1, 0.1), height=50)
        enviar_button.bind(on_press=self.enviar_seleccion)
        layout.add_widget(enviar_button)

        self.popup_transmision = Popup(
            title='Transmitir Registros',
            content=layout,
            size_hint=(0.8, 0.8)
        )
        self.popup_transmision.open()

    def enviar_seleccion(self, instance):
        # Obtener los registros seleccionados donde los checkboxes están activos
        registros_seleccionados = [registro for checkbox, registro in self.checkboxes if checkbox.active]

        if registros_seleccionados:
            datos_transmitir = []
            for reg in registros_seleccionados:
                # Verificar si el campo de la imagen QR no es None
                if isinstance(reg[9], bytes):
                    qr_image_base64 = base64.b64encode(reg[9]).decode('utf-8')
                elif isinstance(reg[9], str):
                    qr_image_base64 = reg[9]  # Asumimos que ya es un string Base64
                else:
                    qr_image_base64 = 'No QR available'


                # Agregar los datos como un diccionario (más fácil de convertir a JSON)
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

            # Transmitir los datos seleccionados vía Wi-Fi o el método deseado
            self.transmitir_wifi(datos_transmitir)
            
            # Marcar los registros como transmitidos en la base de datos
            self.marcar_registros_como_transmitidos(registros_seleccionados)

            # Mostrar mensaje de éxito
            self.mostrar_popup('Éxito', 'Registros empaquetado transmitiendo ...', auto_close_time=2)
        else:
            # Mostrar mensaje de error si no se seleccionó ningún registro
            self.mostrar_popup('Error', 'No se seleccionaron registros para transmitir')





    def marcar_registros_como_transmitidos(self, registros_seleccionados):
        cursor = self.conn.cursor()
        for registro in registros_seleccionados:
            print(f"Marcando transmitido=1 para ID: {registro[0]}, Lote: {registro[1]}")  # Depuración
            cursor.execute("UPDATE chalecos SET transmitido=1 WHERE id=? AND lote=?", (registro[0], registro[1]))
        self.conn.commit()

    def transmitir_wifi(self, datos):
        try:
            puerto_destino = 8000
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            sock.settimeout(5) 

            # Conectar al servidor
            sock.connect((self.ip_destino, puerto_destino))

            # Convertir la lista de datos en JSON
            datos_json = json.dumps({"data": datos})

            # Mostrar datos JSON para depuración===========
            print("=================datos_json=========")
            print(datos_json)
            #================================================
            # Enviar los datos al servidor
            sock.sendall(datos_json.encode('utf-8'))

            # Recibir confirmación del servidor
            try:
                respuesta = sock.recv(1024)  # Reducido a 5 segundos
                if respuesta.decode() == "OK":
                    self.mostrar_popup('Éxito', 'Datos transmitidos y confirmados por el servidor')
                else:
                    self.mostrar_popup('Error', f'Error en la confirmación del servidor: {respuesta.decode()}')
            except socket.timeout:
                # self.mostrar_popup('Error', 'Error de tiempo de espera en la confirmación del servidor', auto_close_time=2)
                self.mostrar_popup('Finalizados', 'Ok', auto_close_time=2)
                

            # Cerrar el socket después de recibir respuesta
            print("______sock.close_____________")
            sock.close()

        except socket.timeout:
            # Manejo del timeout si no se logra conectar
            self.mostrar_popup('Error', 'Error de tiempo de espera en la transmisión (timeout)', auto_close_time=2)
        except Exception as e:
            # Manejo general de errores
            self.mostrar_popup('Error', f'Error al transmitir: {str(e)}', auto_close_time=5)
        finally:
            # Cierre seguro del socket en caso de cualquier excepción
            sock.close()
        return
        
    def ver_registro(self, instance):
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        scroll_view = ScrollView(size_hint=(1, 0.9))
        
        # GridLayout con 4 columnas para los campos seleccionados
        grid_layout = GridLayout(cols=4, size_hint_y=None, spacing=10)
        grid_layout.bind(minimum_height=grid_layout.setter('height'))

        # Añadir títulos para cada columna
        titulos = ["Lote", "Número de Serie", "Fabricante", "Tipo/Modelo"]
        
        for titulo in titulos:
            label = Label(text=titulo, bold=True, size_hint_y=None, height=40, halign='center')
            label.bind(size=label.setter('text_size'))  # Para centrar el texto
            grid_layout.add_widget(label)

        # Obtener los registros de la base de datos
        cursor = self.conn.cursor()
        cursor.execute("SELECT lote, numero_serie, fabricante, tipo_modelo FROM chalecos")
        registros = cursor.fetchall()

        # Añadir cada registro a la tabla
        for registro in registros:
            for campo in registro:
                label = Label(text=str(campo), size_hint_y=None, height=40, halign='center')
                label.bind(size=label.setter('text_size'))  # Para centrar el texto
                grid_layout.add_widget(label)

        scroll_view.add_widget(grid_layout)
        layout.add_widget(scroll_view)

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
        elif key == 274:  # Código de tecla para Flecha abajo o Enter
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

        # Find the current focused widget
        current_focus = next(
            (widget for widget in focus_order if hasattr(widget, 'focus') and widget.focus), None
        )

        if current_focus:
            current_index = focus_order.index(current_focus)
            next_index = (current_index + direction) % len(focus_order)
            
            # Check if the next widget has a focus attribute and set it if it does
            next_widget = focus_order[next_index]
            if hasattr(next_widget, 'focus'):
                next_widget.focus = True
            else:
                # If the next widget doesn't have focus attribute, find the next one in the order
                # without using recursion, just loop to find the next valid widget
                for i in range(1, len(focus_order)):
                    next_index = (current_index + direction + i) % len(focus_order)
                    next_widget = focus_order[next_index]
                    if hasattr(next_widget, 'focus'):
                        next_widget.focus = True
                        break  # Salir del bucle cuando encontramos un widget válido


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




# Validar fechas (vencimiento mayor a fabricación)
    def validar_fechas(self):
        """Valida que las fechas tengan el formato correcto"""
        try:
            parser.parse(self.fecha_fabricacion_input.text)
            parser.parse(self.fecha_vencimiento_input.text)
            return True
        except ValueError:
            self.mostrar_popup('Error', 'El formato de fecha es incorrecto. Por favor use el formato YYYY-MM-DD')
            return False


    def mostrar_popup(self, titulo, mensaje, boton_texto='Cerrar', boton_callback=None, auto_close_time=None):
        # Crear el layout del popup
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        label = Label(text=mensaje, size_hint=(1, 0.8), halign='center', valign='middle')
        label.bind(size=label.setter('text_size'))  # Para alinear el texto
        layout.add_widget(label)
        
        # Crear el botón y asignar la acción de cierre o el callback personalizado
        btn = Button(text=boton_texto, size_hint=(1, 0.2))
        
        # Si se proporciona un callback personalizado, usarlo
        if boton_callback:
            btn.bind(on_press=boton_callback)
        else:
            # Si no hay callback, cerrar el popup
            btn.bind(on_press=lambda x: self.popup_actual.dismiss())
        layout.add_widget(btn)

        # Crear el popup
        self.popup_actual = Popup(
            title=titulo,
            content=layout,
            size_hint=(0.5, 0.3),  # 50% de ancho, 30% de alto de la ventana
            auto_dismiss=False
        )
        self.popup_actual.open()

        # Si se ha definido un tiempo para cerrarse automáticamente
        if auto_close_time:
            Clock.schedule_once(lambda dt: self.popup_actual.dismiss(), auto_close_time)


    def abrir_datepicker_fabricacion(self, instance):
        layout = DatePicker(on_select=self.set_fecha_fabricacion)
        popup = Popup(title='Seleccionar Fecha de Fabricación', content=layout, size_hint=(0.8, 0.6))
        layout.parent = popup  # Para permitir el cierre desde DatePicker
        popup.open()

    def abrir_datepicker_vencimiento(self, instance):
        layout = DatePicker(on_select=self.set_fecha_vencimiento)
        popup = Popup(title='Seleccionar Fecha de Vencimiento', content=layout, size_hint=(0.8, 0.6))
        layout.parent = popup  # Para permitir el cierre desde DatePicker
        popup.open()

    def set_fecha_fabricacion(self, fecha):
        self.fecha_fabricacion_input.text = fecha

    def set_fecha_vencimiento(self, fecha):
        self.fecha_vencimiento_input.text = fecha

if __name__ == '__main__':
    ChalecoApp().run()
