import sqlite3
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
import qrcode
from kivy.uix.image import Image
import io
import asyncio
import threading
from jnius import autoclass, PythonJavaClass, java_method
import datetime

# Importar clases de Android
BluetoothAdapter = autoclass('android.bluetooth.BluetoothAdapter')
BluetoothDevice = autoclass('android.bluetooth.BluetoothDevice')
BluetoothGatt = autoclass('android.bluetooth.BluetoothGatt')
Context = autoclass('android.content.Context')
UUID = autoclass('java.util.UUID')

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

# Clase para manejar eventos de Bluetooth
class BluetoothHandler(PythonJavaClass):
    __javainterfaces__ = ['android/bluetooth/BluetoothGattCallback']
    
    @java_method('(Landroid/bluetooth/BluetoothGatt;II)V')
    def onConnectionStateChange(self, gatt, status, new_state):
        if new_state == 2:  # BluetoothProfile.STATE_CONNECTED
            print("Conectado al dispositivo Bluetooth")
            gatt.discoverServices()
        elif new_state == 0:  # BluetoothProfile.STATE_DISCONNECTED
            print("Desconectado del dispositivo Bluetooth")

    @java_method('(Landroid/bluetooth/BluetoothGatt;Ljava/util/List;)V')
    def onServicesDiscovered(self, gatt, services):
        print("Servicios descubiertos")
        # Aquí puedes manejar los servicios descubiertos

    # Agrega más métodos de callback según sea necesario

# Clase para cargar la interfaz Kivy
class MyBluetoothApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.db = Database()
        self.qr_gen = QRGenerator()
        self.bluetooth_adapter = BluetoothAdapter.getDefaultAdapter()
        self.bluetooth_gatt = None

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

        # Botón para transmitir por Bluetooth
        self.transmit_button = Button(text='Transmitir por Bluetooth', disabled=True)
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
        self.transmit_button.disabled = False
        self.comenzar_lote_button.disabled = True  # Deshabilitar "Comenzar Lote"

    def finalizar_lote(self, instance):
        # Verificar si los campos están llenos antes de finalizar
        if not self.campos_llenos():
            popup = Popup(title='Error', content=Label(text='Complete todos los campos antes de finalizar el lote'), size_hint=(None, None), size=(400, 200))
            popup.open()
            return

        # Guardar el último chaleco antes de finalizar
        self.guardar_chaleco()

        # Deshabilitar todos los campos de texto y botones
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
        self.transmit_button.disabled = True
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
        # Verifica si todos los campos están llenos (excepto el número de lote)
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
        thread = threading.Thread(target=self.run_bluetooth_connection)
        thread.start()

    def run_bluetooth_connection(self):
        # Asegurarse de que el Bluetooth esté habilitado
        if not self.bluetooth_adapter.isEnabled():
            self.bluetooth_adapter.enable()
            # Esperar a que el Bluetooth se habilite
            while not self.bluetooth_adapter.isEnabled():
                pass

        # Obtener el dispositivo Bluetooth al que te deseas conectar
        mac_address = "XX:XX:XX:XX:XX:XX"  # Cambia esto por la MAC de tu dispositivo Bluetooth
        device = self.bluetooth_adapter.getRemoteDevice(mac_address)

        # Crear una instancia de BluetoothHandler
        bluetooth_handler = BluetoothHandler()

        # Conectarse al dispositivo
        self.bluetooth_gatt = device.connectGatt(None, False, bluetooth_handler)

        # Esperar un tiempo para establecer la conexión y descubrir servicios
        # Puedes implementar una lógica más robusta aquí
        import time
        time.sleep(5)

        # Aquí deberías interactuar con los servicios y características deseadas
        # Por ejemplo, escribir datos a una característica específica
        # Esto requerirá conocer el UUID de la característica a la que deseas escribir

        # Cerrar la conexión después de la transmisión
        if self.bluetooth_gatt:
            self.bluetooth_gatt.close()

    # Puedes implementar métodos adicionales para interactuar con servicios y características

if __name__ == "__main__":
    MyBluetoothApp().run()
