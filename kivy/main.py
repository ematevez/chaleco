from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
import threading
from jnius import autoclass
from kivy.clock import Clock

BluetoothAdapter = autoclass('android.bluetooth.BluetoothAdapter')
BluetoothDevice = autoclass('android.bluetooth.BluetoothDevice')
UUID = autoclass('java.util.UUID')

class MyBluetoothApp(App):
    def build(self):
        layout = BoxLayout(orientation='vertical')
        
        self.lote_input = TextInput(hint_text='Lote')
        self.numero_serie_input = TextInput(hint_text='Número de Serie')
        self.fabricante_input = TextInput(hint_text='Fabricante')
        self.fecha_fabricacion_input = TextInput(hint_text='Fecha de Fabricación')
        self.fecha_vencimiento_input = TextInput(hint_text='Fecha de Vencimiento')
        self.tipo_modelo_input = TextInput(hint_text='Tipo de Modelo')
        self.peso_input = TextInput(hint_text='Peso')
        self.talla_input = TextInput(hint_text='Talla')
        self.procedencia_input = TextInput(hint_text='Procedencia')

        save_button = Button(text='Guardar y Enviar por Bluetooth')
        save_button.bind(on_press=self.guardar_y_enviar)

        layout.add_widget(self.lote_input)
        layout.add_widget(self.numero_serie_input)
        layout.add_widget(self.fabricante_input)
        layout.add_widget(self.fecha_fabricacion_input)
        layout.add_widget(self.fecha_vencimiento_input)
        layout.add_widget(self.tipo_modelo_input)
        layout.add_widget(self.peso_input)
        layout.add_widget(self.talla_input)
        layout.add_widget(self.procedencia_input)
        layout.add_widget(save_button)

        return layout

    def guardar_y_enviar(self, instance):
        chaleco_data = f"Lote: {self.lote_input.text}, Serie: {self.numero_serie_input.text}, " \
                       f"Fabricante: {self.fabricante_input.text}, Fecha de Fabricación: {self.fecha_fabricacion_input.text}, " \
                       f"Fecha de Vencimiento: {self.fecha_vencimiento_input.text}, Tipo: {self.tipo_modelo_input.text}, " \
                       f"Peso: {self.peso_input.text}, Talla: {self.talla_input.text}, Procedencia: {self.procedencia_input.text}"

        # Iniciar la transmisión de datos Bluetooth en un hilo separado
        threading.Thread(target=self.send_data_via_bluetooth, args=(chaleco_data,)).start()

    def send_data_via_bluetooth(self, data):
        adapter = BluetoothAdapter.getDefaultAdapter()
        if not adapter:
            print("El dispositivo no tiene soporte para Bluetooth")
            return

        if not adapter.isEnabled():
            print("Bluetooth está desactivado, por favor actívalo")
            return

        paired_devices = adapter.getBondedDevices().toArray()
        target_device = None

        # Encuentra el dispositivo Bluetooth al que deseas enviar los datos
        for device in paired_devices:
            if device.getName() == "NombreDelDispositivoBluetooth":  # Cambia el nombre aquí
                target_device = device
                break

        if not target_device:
            print("Dispositivo no encontrado")
            return

        # Crear conexión Bluetooth
        uuid = UUID.fromString("00001101-0000-1000-8000-00805f9b34fb")
        socket = target_device.createRfcommSocketToServiceRecord(uuid)
        socket.connect()

        try:
            output_stream = socket.getOutputStream()
            output_stream.write(data.encode())
            output_stream.flush()
            print("Datos enviados correctamente")
        except Exception as e:
            print(f"Error al enviar datos: {e}")
        finally:
            socket.close()

if __name__ == '__main__':
    MyBluetoothApp().run()
