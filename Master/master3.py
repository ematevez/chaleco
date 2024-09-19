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
from kivy.core.image import Image as CoreImage
from io import BytesIO
import base64

class ChalecoApp(App):

    def build(self):
        self.conn = sqlite3.connect('chalecos.db')
        self.create_db()
        self.root = BoxLayout(orientation='vertical')
        self.create_widgets()

        # Habilitar el uso de las teclas de flecha para moverse entre los campos de texto
        Window.bind(on_key_down=self.on_key_down)
        
        return self.root

    def create_db(self):
        """Crear la tabla chalecos si no existe"""
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chalecos (
                lote TEXT,
                numero_serie TEXT,
                fabricante TEXT,
                fecha_fabricacion TEXT,
                fecha_vencimiento TEXT,
                tipo_modelo TEXT,
                peso TEXT,
                talla TEXT,
                procedencia TEXT,
                transmitido INTEGER DEFAULT 0
            )
        ''')
        self.conn.commit()

    def create_widgets(self):
        # Crear campos de texto
        self.lote_input = TextInput(hint_text='Lote (autogenerado)', disabled=True)
        self.numero_serie_input = TextInput(hint_text='Número de Serie')
        self.fabricante_input = TextInput(hint_text='Fabricante')
        self.fecha_fabricacion_input = TextInput(hint_text='Fecha de Fabricación')
        self.fecha_vencimiento_input = TextInput(hint_text='Fecha de Vencimiento')
        self.tipo_modelo_input = TextInput(hint_text='Tipo/Modelo')
        self.peso_input = TextInput(hint_text='Peso')
        self.talla_input = TextInput(hint_text='Talla')
        self.procedencia_input = TextInput(hint_text='Procedencia')

        # Crear botones
        self.comenzar_lote_button = Button(text='Comenzar Lote')
        self.add_chaleco_button = Button(text='Agregar Chaleco', disabled=True)
        self.finalizar_lote_button = Button(text='Finalizar Lote', disabled=True)
        self.ver_registro_button = Button(text='Ver Registro')
        self.transmitir_wifi_button = Button(text='Transmitir WiFi')  # Nuevo botón

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
        self.root.add_widget(self.fecha_fabricacion_input)
        self.root.add_widget(self.fecha_vencimiento_input)
        self.root.add_widget(self.tipo_modelo_input)
        self.root.add_widget(self.peso_input)
        self.root.add_widget(self.talla_input)
        self.root.add_widget(self.procedencia_input)
        self.root.add_widget(self.comenzar_lote_button)
        self.root.add_widget(self.add_chaleco_button)
        self.root.add_widget(self.finalizar_lote_button)
        self.root.add_widget(self.transmitir_wifi_button)
        self.root.add_widget(self.ver_registro_button)

    def comenzar_lote(self, instance):
        lote_id = random.randint(1000, 9999)
        fecha_actual = datetime.datetime.now().strftime("%Y%m%d")
        lote_numero = f"L{lote_id}-{fecha_actual}"
        self.lote_input.text = lote_numero

        self.add_chaleco_button.disabled = False
        self.finalizar_lote_button.disabled = False
        self.transmitir_wifi_button.disabled = False
        self.comenzar_lote_button.disabled = True

    def agregar_chaleco(self, instance):
        if not self.campos_llenos():
            popup = Popup(title='Error', content=Label(text='Complete todos los campos antes de agregar un chaleco'), size_hint=(None, None), size=(400, 200))
            popup.open()
            return

        self.guardar_chaleco()
        self.limpiar_campos()

        # Generar QR con la información del chaleco
        self.generar_qr(self.lote_input.text, self.numero_serie_input.text)

    def limpiar_campos(self):
        self.numero_serie_input.text = ''
        self.fabricante_input.text = ''
        self.fecha_fabricacion_input.text = ''
        self.fecha_vencimiento_input.text = ''
        self.tipo_modelo_input.text = ''
        self.peso_input.text = ''
        self.talla_input.text = ''
        self.procedencia_input.text = ''

    def guardar_chaleco(self):
        lote = self.lote_input.text
        numero_serie = self.numero_serie_input.text
        fabricante = self.fabricante_input.text
        fecha_fabricacion = self.fecha_fabricacion_input.text
        fecha_vencimiento = self.fecha_vencimiento_input.text
        tipo_modelo = self.tipo_modelo_input.text
        peso = self.peso_input.text
        talla = self.talla_input.text
        procedencia = self.procedencia_input.text

        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO chalecos (lote, numero_serie, fabricante, fecha_fabricacion, fecha_vencimiento, tipo_modelo, peso, talla, procedencia)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (lote, numero_serie, fabricante, fecha_fabricacion, fecha_vencimiento, tipo_modelo, peso, talla, procedencia))
        self.conn.commit()

    def generar_qr(self, lote, numero_serie):
        # Generar el código QR con la información del chaleco
        datos_qr = f'Lote: {lote}, Serie: {numero_serie}'
        qr = qrcode.make(datos_qr)
        buffer = BytesIO()
        qr.save(buffer, format="PNG")
        buffer.seek(0)

        # Mostrar QR en el Popup
        image_texture = CoreImage(buffer, ext="png").texture
        image = KivyImage(texture=image_texture)
        
        popup = Popup(title='Registro Exitoso', content=BoxLayout(orientation='vertical', children=[Label(text='Chaleco registrado correctamente'), image]), size_hint=(None, None), size=(400, 400))
        popup.open()

    def finalizar_lote(self, instance):
        if not self.campos_llenos():
            popup = Popup(title='Error', content=Label(text='Complete todos los campos antes de finalizar el lote'), size_hint=(None, None), size=(400, 200))
            popup.open()
            return

        self.guardar_chaleco()
        self.add_chaleco_button.disabled = True
        self.finalizar_lote_button.disabled = True
        self.transmitir_wifi_button.disabled = True
        self.comenzar_lote_button.disabled = False

        popup = Popup(title='Lote Finalizado', content=Label(text='El lote ha sido finalizado y los chalecos han sido registrados.'), size_hint=(None, None), size=(400, 200))
        popup.open()

    def abrir_pantalla_transmision(self, instance):
        # Crear la nueva ventana para seleccionar los registros
        layout = BoxLayout(orientation='vertical')
        scroll_view = ScrollView(size_hint=(1, 0.8))
        grid_layout = GridLayout(cols=2, size_hint_y=None)
        grid_layout.bind(minimum_height=grid_layout.setter('height'))

        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM chalecos WHERE transmitido=0")
        registros = cursor.fetchall()

        self.checkboxes = []

        # Mostrar los registros con un checkbox para seleccionar
        for registro in registros:
            checkbox = CheckBox()
            label = Label(text=str(registro), size_hint_y=None, height=40)
            self.checkboxes.append((checkbox, registro))
            grid_layout.add_widget(checkbox)
            grid_layout.add_widget(label)

        scroll_view.add_widget(grid_layout)
        layout.add_widget(scroll_view)

        # Botón de enviar
        enviar_button = Button(text='Enviar', size_hint=(1, 0.2))
        enviar_button.bind(on_press=self.enviar_seleccion)
        layout.add_widget(enviar_button)

        self.popup_transmision = Popup(title='Transmitir Registros', content=layout, size_hint=(None, None), size=(600, 600))
        self.popup_transmision.open()

    def enviar_seleccion(self, instance):
        registros_seleccionados = [registro for checkbox, registro in self.checkboxes if checkbox.active]

        if registros_seleccionados:
            # Transmitir los registros seleccionados
            self.transmitir_wifi("\n".join([str(registro) for registro in registros_seleccionados]))

            # Actualizar los registros transmitidos
            self.marcar_registros_como_transmitidos(registros_seleccionados)

            popup = Popup(title='Éxito', content=Label(text='Registros transmitidos con éxito'), size_hint=(None, None), size=(400, 200))
            popup.open()
        else:
            popup = Popup(title='Error', content=Label(text='No se seleccionaron registros para transmitir'), size_hint=(None, None), size=(400, 200))
            popup.open()

    def marcar_registros_como_transmitidos(self, registros_seleccionados):
        cursor = self.conn.cursor()
        for registro in registros_seleccionados:
            cursor.execute("UPDATE chalecos SET transmitido=1 WHERE lote=? AND numero_serie=?", (registro[0], registro[1]))
        self.conn.commit()
 
    def transmitir_wifi(self, datos):
        try:
            # IP y puerto de destino (asegúrate de que estos valores sean correctos)
            ip_destino = '192.168.1.42'  # Cambia esto por la IP del servidor receptor (slave)
            puerto_destino = 8000  # El puerto debe coincidir con el del receptor (slave)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # Cambiado a SOCK_STREAM para usar TCP

            # Conectar al servidor
            sock.connect((ip_destino, puerto_destino))

            # Enviar datos
            sock.sendall(datos.encode())

            # Esperar confirmación del servidor
            sock.settimeout(5)  # Tiempo máximo de espera (5 segundos)
            try:
                respuesta = sock.recv(1024)  # Tamaño máximo de mensaje recibido
                if respuesta.decode() == "Registros recibidos correctamente.":
                    popup = Popup(title='Éxito', content=Label(text='Datos transmitidos y confirmados por el servidor'), size_hint=(None, None), size=(400, 200))
                    popup.open()
                else:
                    popup = Popup(title='Error', content=Label(text='Error en la confirmación del servidor'), size_hint=(None, None), size=(400, 200))
                    popup.open()
            except socket.timeout:
                popup = Popup(title='Error', content=Label(text='Tiempo de espera agotado. El servidor no respondió.'), size_hint=(None, None), size=(400, 200))
                popup.open()
            
            sock.close()

        except Exception as e:
            popup = Popup(title='Error', content=Label(text=f'Error al transmitir: {str(e)}'), size_hint=(None, None), size=(400, 200))
            popup.open()

    
    def ver_registro(self, instance):
        layout = BoxLayout(orientation='vertical')
        scroll_view = ScrollView(size_hint=(1, 0.8))
        
        # GridLayout con número de columnas basado en los campos del chaleco
        grid_layout = GridLayout(cols=9, size_hint_y=None)
        grid_layout.bind(minimum_height=grid_layout.setter('height'))

        # Añadir títulos para cada columna
        titulos = ["Lote", "Número de Serie", "Fabricante", "Fecha de Fabricación", 
                "Fecha de Vencimiento", "Tipo/Modelo", "Peso", "Talla", "Procedencia"]
        
        for titulo in titulos:
            grid_layout.add_widget(Label(text=titulo, bold=True, size_hint_y=None, height=40))

        # Obtener los registros de la base de datos
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM chalecos")
        registros = cursor.fetchall()

        # Añadir cada registro a la tabla
        for registro in registros:
            for campo in registro:
                label = Label(text=str(campo), size_hint_y=None, height=40)
                grid_layout.add_widget(label)

        scroll_view.add_widget(grid_layout)
        layout.add_widget(scroll_view)

        cerrar_button = Button(text='Cerrar', size_hint=(1, 0.2))
        cerrar_button.bind(on_press=lambda x: self.popup_ver_registro.dismiss())
        layout.add_widget(cerrar_button)

        self.popup_ver_registro = Popup(title='Registro de Chalecos', content=layout, size_hint=(None, None), size=(600, 600))
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
            self.talla_input,
            self.procedencia_input
        ]

        current_focus = next((widget for widget in focus_order if widget.focus), None)

        if current_focus:
            current_index = focus_order.index(current_focus)
            next_index = (current_index + direction) % len(focus_order)
            focus_order[next_index].focus = True

    def campos_llenos(self):
        return all([
            self.numero_serie_input.text,
            self.fabricante_input.text,
            self.fecha_fabricacion_input.text,
            self.fecha_vencimiento_input.text,
            self.tipo_modelo_input.text,
            self.peso_input.text,
            self.talla_input.text,
            self.procedencia_input.text
        ])

if __name__ == '__main__':
    ChalecoApp().run()
