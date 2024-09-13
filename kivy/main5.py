from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.image import Image
import threading
import qrcode
from kivy.core.image import Image as CoreImage
from io import BytesIO
from jnius import autoclass
from kivy.clock import Clock
import traceback

# Clases de Bluetooth de Android
BluetoothAdapter = autoclass('android.bluetooth.BluetoothAdapter')
BluetoothDevice = autoclass('android.bluetooth.BluetoothDevice')
UUID = autoclass('java.util.UUID')

class MyBluetoothApp(App):
    def build(self):
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # Botón de transmisión Bluetooth, colocado arriba
        bluetooth_button = Button(text='Transmisión Bluetooth', size_hint=(1, 0.1))
        bluetooth_button.bind(on_press=self.guardar_y_enviar)
        layout.add_widget(bluetooth_button)
        
        # Inputs de los datos del chaleco
        self.lote_input = TextInput(hint_text='Lote', input_type='text', multiline=False)
        self.numero_serie_input = TextInput(hint_text='Número de Serie', input_type='text', multiline=False)
        self.fabricante_input = TextInput(hint_text='Fabricante', input_type='text', multiline=False)
        self.fecha_fabricacion_input = TextInput(hint_text='Fecha de Fabricación', input_type='text', multiline=False)
        self.fecha_vencimiento_input = TextInput(hint_text='Fecha de Vencimiento', input_type='text', multiline=False)
        self.tipo_modelo_input = TextInput(hint_text='Tipo de Modelo', input_type='text', multiline=False)
        self.peso_input = TextInput(hint_text='Peso', input_type='number', multiline=False)
        self.talla_input = TextInput(hint_text='Talla', input_type='text', multiline=False)
        self.procedencia_input = TextInput(hint_text='Procedencia', input_type='text', multiline=False)
        
        # Añadir inputs al layout
        layout.add_widget(self.lote_input)
        layout.add_widget(self.numero_serie_input)
        layout.add_widget(self.fabricante_input)
        layout.add_widget(self.fecha_fabricacion_input)
        layout.add_widget(self.fecha_vencimiento_input)
        layout.add_widget(self.tipo_modelo_input)
        layout.add_widget(self.peso_input)
        layout.add_widget(self.talla_input)
        layout.add_widget(self.procedencia_input)

        # Botón para generar QR y mostrar datos
        qr_button = Button(text='Generar QR', size_hint=(1, 0.1))
        qr_button.bind(on_press=self.generar_qr)
        layout.add_widget(qr_button)

        return layout

    def guardar_y_enviar(self, instance):
        try:
            # Generar el paquete de datos en formato JSON para ser enviado
            chaleco_data = {
                "Lote": self.lote_input.text,
                "Serie": self.numero_serie_input.text,
                "Fabricante": self.fabricante_input.text,
                "FechaFabricacion": self.fecha_fabricacion_input.text,
                "FechaVencimiento": self.fecha_vencimiento_input.text,
                "Tipo": self.tipo_modelo_input.text,
                "Peso": self.peso_input.text,
                "Talla": self.talla_input.text,
                "Procedencia": self.procedencia_input.text
            }
            
            # Convertir el diccionario a cadena JSON
            import json
            chaleco_json = json.dumps(chaleco_data)
            
            # Iniciar la transmisión de datos Bluetooth en un hilo separado
            threading.Thread(target=self.send_data_via_bluetooth, args=(chaleco_json,)).start()

        except Exception as e:
            # Mostrar mensaje de error detallado
            self.show_popup("Error", f"Error al preparar los datos para enviar: {str(e)}\n{traceback.format_exc()}")

    def send_data_via_bluetooth(self, data):
        try:
            adapter = BluetoothAdapter.getDefaultAdapter()
            
            if not adapter:
                self.show_popup("Error", "El dispositivo no tiene soporte para Bluetooth")
                return

            if not adapter.isEnabled():
                self.show_popup("Error", "Bluetooth está desactivado, por favor actívalo")
                return

            # Buscar dispositivo con una MAC específica
            target_mac_address = "AC:74:B1:EC:0B:1B"  # Cambia esto a tu dirección MAC deseada
            paired_devices = adapter.getBondedDevices().toArray()
            target_device = None

            for device in paired_devices:
                if device.getAddress() == target_mac_address:
                    target_device = device
                    break

            if not target_device:
                self.show_popup("Error", f"Dispositivo con MAC {target_mac_address} no encontrado")
                return

            # Intentar conectar al dispositivo
            try:
                uuid = UUID.fromString("00001101-0000-1000-8000-00805f9b34fb")
                socket = target_device.createRfcommSocketToServiceRecord(uuid)
                socket.connect()
                self.show_popup("Conectado", f"Conexión exitosa con {target_device.getName()} ({target_mac_address})")
            except Exception as e:
                self.show_popup("Error", f"No se pudo conectar al dispositivo: {e}")
                return

            # Intentar enviar los datos
            try:
                output_stream = socket.getOutputStream()
                output_stream.write(data.encode())
                output_stream.flush()
                self.show_popup("Éxito", "Datos enviados correctamente")
            except Exception as e:
                self.show_popup("Error", f"Error al enviar datos: {e}")
            finally:
                socket.close()

        except Exception as e:
            # Mostrar mensaje de error detallado
            self.show_popup("Error", f"Error de Bluetooth: {str(e)}\n{traceback.format_exc()}")

    def generar_qr(self, instance):
        try:
            # Datos para el QR
            chaleco_data = f"Lote: {self.lote_input.text}, Serie: {self.numero_serie_input.text}, " \
                           f"Fabricante: {self.fabricante_input.text}, Fecha de Fabricación: {self.fecha_fabricacion_input.text}, " \
                           f"Fecha de Vencimiento: {self.fecha_vencimiento_input.text}, Tipo: {self.tipo_modelo_input.text}, " \
                           f"Peso: {self.peso_input.text}, Talla: {self.talla_input.text}, Procedencia: {self.procedencia_input.text}"
            
            # Generar QR
            qr = qrcode.make(chaleco_data)
            buffer = BytesIO()
            qr.save(buffer, format='PNG')
            buffer.seek(0)
            
            # Mostrar QR en un popup
            texture = CoreImage(buffer, ext='png').texture
            image = Image(texture=texture)
            self.show_qr_popup(image)
        except Exception as e:
            # Mostrar mensaje de error detallado
            self.show_popup("Error", f"Error al generar el QR: {str(e)}\n{traceback.format_exc()}")

    def show_popup(self, title, message):
        # Mostrar una ventana emergente con el mensaje especificado
        popup_layout = BoxLayout(orientation='vertical', padding=10)
        popup_label = Label(text=message)
        popup_button = Button(text='Cerrar', size_hint=(1, 0.25))

        popup_layout.add_widget(popup_label)
        popup_layout.add_widget(popup_button)

        popup = Popup(title=title, content=popup_layout, size_hint=(0.8, 0.8))
        popup_button.bind(on_press=popup.dismiss)
        popup.open()

    def show_qr_popup(self, image_widget):
        # Mostrar el QR generado en un popup
        popup_layout = BoxLayout(orientation='vertical', padding=10)
        popup_layout.add_widget(image_widget)
        popup_button = Button(text='Cerrar', size_hint=(1, 0.25))
        popup_layout.add_widget(popup_button)

        popup = Popup(title='QR generado', content=popup_layout, size_hint=(0.8, 0.8))
        popup_button.bind(on_press=popup.dismiss)
        popup.open()

if __name__ == '__main__':
    MyBluetoothApp().run()
