"""
Funcional

"""


import sqlite3
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.image import Image
from kivy.core.image import Image as CoreImage
import qrcode
import io
import asyncio
import threading
from bleak import BleakClient
import datetime

# Clase para manejar la base de datos
class Database:
    def __init__(self, db_name="chalecos.db"):
        self.conn = sqlite3.connect(db_name)
        self.create_table()

    def create_table(self):
        self.conn.execute('''CREATE TABLE IF NOT EXISTS chalecos
                            (id INTEGER PRIMARY KEY AUTOINCREMENT,
                            lote TEXT,
                            numero_serie TEXT,
                            nombre_fabricante TEXT,
                            fecha_fabricacion TEXT,
                            fecha_vencimiento TEXT,
                            tipo_modelo TEXT,
                            peso TEXT,
                            talla TEXT,
                            procedencia TEXT,
                            fecha_registro TEXT,
                            qr BLOB,
                            transmitido BOOLEAN DEFAULT 0)''')

    def add_chaleco(self, lote, numero_serie, nombre_fabricante, fecha_fabricacion, fecha_vencimiento, tipo_modelo, peso, talla, procedencia, qr):
        fecha_registro = str(datetime.datetime.now())
        self.conn.execute("INSERT INTO chalecos (lote, numero_serie, nombre_fabricante, fecha_fabricacion, fecha_vencimiento, tipo_modelo, peso, talla, procedencia, fecha_registro, qr) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                          (lote, numero_serie, nombre_fabricante, fecha_fabricacion, fecha_vencimiento, tipo_modelo, peso, talla, procedencia, fecha_registro, qr))
        self.conn.commit()

    def marcar_transmitido(self, chaleco_id):
        self.conn.execute("UPDATE chalecos SET transmitido = 1 WHERE id = ?", (chaleco_id,))
        self.conn.commit()

    def obtener_chalecos(self):
        cursor = self.conn.execute("SELECT * FROM chalecos")
        return cursor.fetchall()

    def obtener_chalecos_no_transmitidos(self):
        cursor = self.conn.execute("SELECT * FROM chalecos WHERE transmitido = 0")
        return cursor.fetchall()

# Clase para generar y guardar QR
class QRGenerator:
    def generate_qr(self, data):
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)

        img = qr.make_image(fill="black", back_color="white")

        # Guardar QR en memoria en formato binario
        img_byte_array = io.BytesIO()
        img.save(img_byte_array, format='PNG')
        return img_byte_array.getvalue()  # Devolver como binario

# Clase para cargar la interfaz Kivy
class MyBluetoothApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.db = Database()
        self.qr_gen = QRGenerator()

    def build(self):
        self.layout = BoxLayout(orientation='vertical')

        # Entradas de texto
        self.lote_input = TextInput(hint_text='Número de Lote', disabled=True)
        self.layout.add_widget(self.lote_input)

        self.numero_serie_input = TextInput(hint_text='Número de Serie', disabled=True)
        self.layout.add_widget(self.numero_serie_input)

        self.fabricante_input = TextInput(hint_text='Nombre Fabricante', disabled=True)
        self.layout.add_widget(self.fabricante_input)

        self.fecha_fabricacion_input = TextInput(hint_text='Fecha de Fabricación (YYYY-MM-DD)', disabled=True)
        self.layout.add_widget(self.fecha_fabricacion_input)

        self.fecha_vencimiento_input = TextInput(hint_text='Fecha de Vencimiento (YYYY-MM-DD)', disabled=True)
        self.layout.add_widget(self.fecha_vencimiento_input)

        self.tipo_modelo_input = TextInput(hint_text='Tipo y Modelo', disabled=True)
        self.layout.add_widget(self.tipo_modelo_input)

        self.peso_input = TextInput(hint_text='Peso', disabled=True)
        self.layout.add_widget(self.peso_input)

        self.talla_input = TextInput(hint_text='Talla', disabled=True)
        self.layout.add_widget(self.talla_input)

        self.procedencia_input = TextInput(hint_text='Procedencia', disabled=True)
        self.layout.add_widget(self.procedencia_input)

        # Botón para comenzar el lote
        self.comenzar_lote_button = Button(text='Comenzar Lote')
        self.comenzar_lote_button.bind(on_press=self.comenzar_lote)
        self.layout.add_widget(self.comenzar_lote_button)

        # Botón para agregar chaleco
        self.add_chaleco_button = Button(text='Agregar Chaleco', disabled=True)
        self.add_chaleco_button.bind(on_press=self.agregar_chaleco)
        self.layout.add_widget(self.add_chaleco_button)

        # Botón para finalizar el lote
        self.finalizar_lote_button = Button(text='Finalizar Lote', disabled=True)
        self.finalizar_lote_button.bind(on_press=self.finalizar_lote)
        self.layout.add_widget(self.finalizar_lote_button)

        # Botón para transmitir por Bluetooth (siempre activo)
        self.transmit_button = Button(text='Transmitir por Bluetooth')
        self.transmit_button.bind(on_press=self.start_send_data_thread)
        self.layout.add_widget(self.transmit_button)

        # Botón para ver registro
        self.ver_registro_button = Button(text='Ver Registro')
        self.ver_registro_button.bind(on_press=self.ver_registro)
        self.layout.add_widget(self.ver_registro_button)

        return self.layout

    def comenzar_lote(self, instance):
        # Habilitar los campos de texto y botones
        self.lote_input.disabled = False
        self.numero_serie_input.disabled = False
        self.fabricante_input.disabled = False
        self.fecha_fabricacion_input.disabled = False
        self.fecha_vencimiento_input.disabled = False
        self.tipo_modelo_input.disabled = False
        self.peso_input.disabled = False
        self.talla_input.disabled = False
        self.procedencia_input.disabled = False
        self.add_chaleco_button.disabled = False
        self.finalizar_lote_button.disabled = False
        self.comenzar_lote_button.disabled = True  # Deshabilitar "Comenzar Lote"

    def finalizar_lote(self, instance):
        # Verificar si los campos están llenos antes de finalizar
        if not self.campos_llenos():
            popup = Popup(title='Error', content=Label(text='Complete todos los campos antes de finalizar el lote'), size_hint=(None, None), size=(400, 200))
            popup.open()
            return

        # Guardar el último chaleco antes de finalizar
        self.guardar_chaleco()

        # Generar QR con los datos actuales
        lote = self.lote_input.text
        numero_serie = self.numero_serie_input.text
        fabricante = self.fabricante_input.text
        fecha_fabricacion = self.fecha_fabricacion_input.text
        fecha_vencimiento = self.fecha_vencimiento_input.text
        tipo_modelo = self.tipo_modelo_input.text
        peso = self.peso_input.text
        talla = self.talla_input.text
        procedencia = self.procedencia_input.text

        qr_data = f"Lote: {lote}, Serie: {numero_serie}, Fabricante: {fabricante}, Fecha Fabricación: {fecha_fabricacion}, Fecha Vencimiento: {fecha_vencimiento}, Tipo: {tipo_modelo}, Peso: {peso}, Talla: {talla}, Procedencia: {procedencia}"
        qr_image = self.qr_gen.generate_qr(qr_data)

        # Convertir QR en una imagen Kivy (CoreImage)
        qr_io = io.BytesIO(qr_image)
        core_image = CoreImage(qr_io, ext="png")

        # Crear un Popup para mostrar el QR
        qr_popup = Popup(
            title='QR Generado',
            content=Image(texture=core_image.texture),
            size_hint=(None, None),
            size=(400, 400)
        )
        qr_popup.open()

        # Deshabilitar los campos de texto
        self.lote_input.disabled = True
        self.numero_serie_input.disabled = True
        self.fabricante_input.disabled = True
        self.fecha_fabricacion_input.disabled = True
        self.fecha_vencimiento_input.disabled = True
        self.tipo_modelo_input.disabled = True
        self.peso_input.disabled = True
        self.talla_input.disabled = True
        self.procedencia_input.disabled = True
        self.add_chaleco_button.disabled = True
        self.finalizar_lote_button.disabled = True
        self.comenzar_lote_button.disabled = False  # Habilitar "Comenzar Lote"

    def agregar_chaleco(self, instance):
        # Verificar si todos los campos están llenos
        if not self.campos_llenos():
            popup = Popup(title='Error', content=Label(text='Complete todos los campos'), size_hint=(None, None), size=(400, 200))
            popup.open()
            return

        # Guardar el chaleco actual
        self.guardar_chaleco()

        # Mostrar advertencia de que el chaleco fue guardado
        popup = Popup(title='Éxito', content=Label(text='Chaleco guardado correctamente'), size_hint=(None, None), size=(400, 200))
        popup.open()

        # Borrar todos los campos, excepto el número de lote
        self.numero_serie_input.text = ""
        self.fabricante_input.text = ""
        self.fecha_fabricacion_input.text = ""
        self.fecha_vencimiento_input.text = ""
        self.tipo_modelo_input.text = ""
        self.peso_input.text = ""
        self.talla_input.text = ""
        self.procedencia_input.text = ""

    def campos_llenos(self):
        return all([
            self.lote_input.text,
            self.numero_serie_input.text,
            self.fabricante_input.text,
            self.fecha_fabricacion_input.text,
            self.fecha_vencimiento_input.text,
            self.tipo_modelo_input.text,
            self.peso_input.text,
            self.talla_input.text,
            self.procedencia_input.text
        ])

    def guardar_chaleco(self):
        # Obtener los datos de los campos
        lote = self.lote_input.text
        numero_serie = self.numero_serie_input.text
        fabricante = self.fabricante_input.text
        fecha_fabricacion = self.fecha_fabricacion_input.text
        fecha_vencimiento = self.fecha_vencimiento_input.text
        tipo_modelo = self.tipo_modelo_input.text
        peso = self.peso_input.text
        talla = self.talla_input.text
        procedencia = self.procedencia_input.text

        # Generar el QR con los datos
        qr_data = f"Lote: {lote}, Serie: {numero_serie}, Fabricante: {fabricante}, Fecha Fabricación: {fecha_fabricacion}, Fecha Vencimiento: {fecha_vencimiento}, Tipo: {tipo_modelo}, Peso: {peso}, Talla: {talla}, Procedencia: {procedencia}"
        qr_image = self.qr_gen.generate_qr(qr_data)

        # Guardar el chaleco en la base de datos
        self.db.add_chaleco(lote, numero_serie, fabricante, fecha_fabricacion, fecha_vencimiento, tipo_modelo, peso, talla, procedencia, qr_image)

    def ver_registro(self, instance):
        # Obtener todos los chalecos de la base de datos
        chalecos = self.db.obtener_chalecos()
        registro_texto = ""
        for chaleco in chalecos:
            registro_texto += f"Lote: {chaleco[1]}, Serie: {chaleco[2]}, Fabricante: {chaleco[3]}, Fecha Fabricación: {chaleco[4]}, Fecha Vencimiento: {chaleco[5]}, Tipo: {chaleco[6]}, Peso: {chaleco[7]}, Talla: {chaleco[8]}, Procedencia: {chaleco[9]}\n"

        # Mostrar los datos en un Popup
        popup = Popup(title='Registro de Chalecos', content=Label(text=registro_texto), size_hint=(None, None), size=(400, 400))
        popup.open()

    def start_send_data_thread(self, instance):
        thread = threading.Thread(target=self.run_asyncio_in_thread)
        thread.start()

    def run_asyncio_in_thread(self):
        asyncio.run(self.send_data_async())

    async def send_data_async(self):
        chalecos_no_transmitidos = self.db.obtener_chalecos_no_transmitidos()
        mac_address = "XX:XX:XX:XX:XX:XX"  # Cambia esto por la MAC de tu PC
        characteristic_uuid = "0000xxxx-0000-1000-8000-00805f9b34fb"  # UUID de la característica a la que enviar datos

        for chaleco in chalecos_no_transmitidos:
            try:
                async with BleakClient(mac_address) as client:
                    data = f"Lote: {chaleco[1]}, Serie: {chaleco[2]}, Fabricante: {chaleco[3]}"
                    await client.write_gatt_char(characteristic_uuid, data.encode('utf-8'))
                    self.db.marcar_transmitido(chaleco[0])
                    print(f"Chaleco {chaleco[0]} transmitido correctamente.")
            except Exception as e:
                print(f"Error al enviar chaleco {chaleco[0]}: {e}")

if __name__ == "__main__":
    MyBluetoothApp().run()
