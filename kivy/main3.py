from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.clock import Clock
import threading
import json
import os
import random
from jnius import autoclass

# Bluetooth Android Classes
BluetoothAdapter = autoclass('android.bluetooth.BluetoothAdapter')
UUID = autoclass('java.util.UUID')

class MyBluetoothApp(App):
    def build(self):
        self.lote = None  # Variable para almacenar el número de lote
        self.chalecos = []  # Lista de chalecos agregados
        self.no_transmitidos = []  # Lista de chalecos no transmitidos
        self.mac_addresses = ["ac:74:b1:ec:0b:17", "ac:74:b1:ec:0b:1b", "50:a1:32:2b:cc:c3"]  # MACs permitidas

        layout = BoxLayout(orientation='vertical')

        # Botón para comenzar el lote
        self.lote_label = Label(text='Lote: No iniciado')
        start_lote_button = Button(text='Comenzar Lote')
        start_lote_button.bind(on_press=self.comenzar_lote)

        # Inputs de los datos del chaleco
        self.numero_serie_input = TextInput(hint_text='Número de Serie')
        self.fabricante_input = TextInput(hint_text='Fabricante')
        self.fecha_fabricacion_input = TextInput(hint_text='Fecha de Fabricación')
        self.fecha_vencimiento_input = TextInput(hint_text='Fecha de Vencimiento')
        self.tipo_modelo_input = TextInput(hint_text='Tipo de Modelo')
        self.peso_input = TextInput(hint_text='Peso')
        self.talla_input = TextInput(hint_text='Talla')
        self.procedencia_input = TextInput(hint_text='Procedencia')

        # Botón para agregar chaleco
        self.add_chaleco_button = Button(text='Agregar Chaleco', disabled=True)
        self.add_chaleco_button.bind(on_press=self.agregar_chaleco)

        # Botón para finalizar lote
        self.finalize_lote_button = Button(text='Finalizar Lote', disabled=True)
        self.finalize_lote_button.bind(on_press=self.finalizar_lote)

        # Botón para ver registros no transmitidos
        view_records_button = Button(text='Ver Registro No Transmitido')
        view_records_button.bind(on_press=self.ver_registro_no_transmitido)

        # Añadir widgets al layout
        layout.add_widget(self.lote_label)
        layout.add_widget(self.numero_serie_input)
        layout.add_widget(self.fabricante_input)
        layout.add_widget(self.fecha_fabricacion_input)
        layout.add_widget(self.fecha_vencimiento_input)
        layout.add_widget(self.tipo_modelo_input)
        layout.add_widget(self.peso_input)
        layout.add_widget(self.talla_input)
        layout.add_widget(self.procedencia_input)
        layout.add_widget(start_lote_button)
        layout.add_widget(self.add_chaleco_button)
        layout.add_widget(self.finalize_lote_button)
        layout.add_widget(view_records_button)

        return layout

    def comenzar_lote(self, instance):
        # Generar un número de lote único basado en un número aleatorio o fecha
        self.lote = f"Lote-{random.randint(1000, 9999)}"
        self.lote_label.text = f"Lote: {self.lote}"
        self.add_chaleco_button.disabled = False  # Habilitar el botón de agregar chaleco
        self.finalize_lote_button.disabled = False  # Habilitar el botón de finalizar lote

    def agregar_chaleco(self, instance):
        # Guardar los datos del chaleco
        chaleco_data = {
            "Lote": self.lote,
            "NumeroSerie": self.numero_serie_input.text,
            "Fabricante": self.fabricante_input.text,
            "FechaFabricacion": self.fecha_fabricacion_input.text,
            "FechaVencimiento": self.fecha_vencimiento_input.text,
            "Tipo": self.tipo_modelo_input.text,
            "Peso": self.peso_input.text,
            "Talla": self.talla_input.text,
            "Procedencia": self.procedencia_input.text
        }

        # Limpiar los inputs después de agregar el chaleco
        self.limpiar_inputs()

        # Añadir chaleco a la lista y tratar de enviar los datos por Bluetooth
        self.chalecos.append(chaleco_data)
        threading.Thread(target=self.enviar_datos_bluetooth, args=(chaleco_data,)).start()

    def enviar_datos_bluetooth(self, chaleco_data):
        adapter = BluetoothAdapter.getDefaultAdapter()

        if not adapter:
            Clock.schedule_once(lambda dt: self.show_popup("Error", "Este dispositivo no tiene soporte Bluetooth"))
            return

        if not adapter.isEnabled():
            Clock.schedule_once(lambda dt: self.show_popup("Error", "Bluetooth está desactivado, por favor actívalo"))
            return

        # Intentar conectar y enviar datos a una de las tres MACs permitidas
        for mac in self.mac_addresses:
            paired_devices = adapter.getBondedDevices().toArray()
            target_device = None

            for device in paired_devices:
                if device.getAddress().lower() == mac:
                    target_device = device
                    break

            if target_device:
                try:
                    uuid = UUID.fromString("00001101-0000-1000-8000-00805f9b34fb")
                    socket = target_device.createRfcommSocketToServiceRecord(uuid)
                    socket.connect()
                    output_stream = socket.getOutputStream()
                    output_stream.write(json.dumps(chaleco_data).encode())
                    output_stream.flush()
                    Clock.schedule_once(lambda dt: self.show_popup("Éxito", f"Datos enviados a {target_device.getName()}"))
                    socket.close()
                    return  # Salir si el envío fue exitoso
                except Exception as e:
                    Clock.schedule_once(lambda dt: self.show_popup("Error", f"Error al enviar a {mac}: {e}"))

        # Si no se pudo transmitir, guardar en no_transmitidos
        self.no_transmitidos.append(chaleco_data)
        self.guardar_no_transmitidos_localmente()

    def guardar_no_transmitidos_localmente(self):
        with open('no_transmitidos.json', 'w') as f:
            json.dump(self.no_transmitidos, f)

    def ver_registro_no_transmitido(self, instance):
        # Cargar y mostrar el registro no transmitido
        if os.path.exists('no_transmitidos.json'):
            with open('no_transmitidos.json', 'r') as f:
                self.no_transmitidos = json.load(f)

        if not self.no_transmitidos:
            self.show_popup("Info", "No hay registros pendientes de transmisión")
        else:
            registros = "\n".join([json.dumps(chaleco) for chaleco in self.no_transmitidos])
            self.show_popup("Registros No Transmitidos", registros)

    def finalizar_lote(self, instance):
        # Finalizar el lote actual
        self.show_popup("Finalizado", "Lote finalizado")
        self.lote = None
        self.lote_label.text = 'Lote: No iniciado'
        self.add_chaleco_button.disabled = True
        self.finalize_lote_button.disabled = True
        self.chalecos = []  # Reiniciar la lista de chalecos para un nuevo lote

    def limpiar_inputs(self):
        self.numero_serie_input.text = ''
        self.fabricante_input.text = ''
        self.fecha_fabricacion_input.text = ''
        self.fecha_vencimiento_input.text = ''
        self.tipo_modelo_input.text = ''
        self.peso_input.text = ''
        self.talla_input.text = ''
        self.procedencia_input.text = ''

    def show_popup(self, title, message):
        # Mostrar ventana emergente con el mensaje
        popup_layout = BoxLayout(orientation='vertical', padding=10)
        popup_label = Label(text=message)
        popup_button = Button(text='Cerrar', size_hint=(1, 0.25))

        popup_layout.add_widget(popup_label)
        popup_layout.add_widget(popup_button)

        popup = Popup(title=title, content=popup_layout, size_hint=(0.75, 0.5))
        popup_button.bind(on_press=popup.dismiss)
        popup.open()

if __name__ == '__main__':
    MyBluetoothApp().run()
