import datetime
import random
import socket
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.core.window import Window

class ChalecoApp(App):

    def build(self):
        self.root = BoxLayout(orientation='vertical')
        self.create_widgets()

        # Habilitar el uso de Tab para moverse entre los campos de texto
        Window.bind(on_key_down=self.on_key_down)
        
        return self.root

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

        # Asociar los botones a sus funciones
        self.comenzar_lote_button.bind(on_press=self.comenzar_lote)
        self.add_chaleco_button.bind(on_press=self.agregar_chaleco)
        self.finalizar_lote_button.bind(on_press=self.finalizar_lote)
        self.ver_registro_button.bind(on_press=self.ver_registro)

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
        self.root.add_widget(self.ver_registro_button)

    def comenzar_lote(self, instance):
        # Generar automáticamente el número de lote
        lote_id = random.randint(1000, 9999)
        fecha_actual = datetime.datetime.now().strftime("%Y%m%d")
        lote_numero = f"L{lote_id}-{fecha_actual}"
        self.lote_input.text = lote_numero

        # Habilitar los campos de texto y botones
        self.add_chaleco_button.disabled = False
        self.finalizar_lote_button.disabled = False
        self.comenzar_lote_button.disabled = True

    def agregar_chaleco(self, instance):
        if not self.campos_llenos():
            # Mostrar un popup si faltan campos
            popup = Popup(title='Error', content=Label(text='Complete todos los campos antes de agregar un chaleco'), size_hint=(None, None), size=(400, 200))
            popup.open()
            return

        # Guardar los datos del chaleco y transmitir por WiFi
        self.guardar_chaleco()
        self.transmitir_wifi("Chaleco agregado correctamente.")
        
        # Limpiar los campos de texto después de agregar el chaleco
        self.limpiar_campos()

        # Mostrar un popup indicando que el chaleco fue registrado exitosamente
        popup = Popup(title='Registro Exitoso', content=Label(text='Chaleco registrado correctamente'), size_hint=(None, None), size=(400, 200))
        popup.open()

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
        # Obtener datos de los campos
        lote = self.lote_input.text
        numero_serie = self.numero_serie_input.text
        fabricante = self.fabricante_input.text
        fecha_fabricacion = self.fecha_fabricacion_input.text
        fecha_vencimiento = self.fecha_vencimiento_input.text
        tipo_modelo = self.tipo_modelo_input.text
        peso = self.peso_input.text
        talla = self.talla_input.text
        procedencia = self.procedencia_input.text

        # Simulación: Imprimir los datos (reemplazar por lógica real de almacenamiento)
        print(f"Lote: {lote}, Serie: {numero_serie}, Fabricante: {fabricante}, Fecha Fabricación: {fecha_fabricacion}, Fecha Vencimiento: {fecha_vencimiento}, Tipo: {tipo_modelo}, Peso: {peso}, Talla: {talla}, Procedencia: {procedencia}")
        
        # Guardar en archivo (simulación)
        with open("registro_chalecos.txt", "a") as file:
            file.write(f"Lote: {lote}, Serie: {numero_serie}, Fabricante: {fabricante}, Fecha Fabricación: {fecha_fabricacion}, Fecha Vencimiento: {fecha_vencimiento}, Tipo: {tipo_modelo}, Peso: {peso}, Talla: {talla}, Procedencia: {procedencia}\n")

    def finalizar_lote(self, instance):
        if not self.campos_llenos():
            # Mostrar un popup si faltan campos
            popup = Popup(title='Error', content=Label(text='Complete todos los campos antes de finalizar el lote'), size_hint=(None, None), size=(400, 200))
            popup.open()
            return

        # Guardar los datos del chaleco y transmitir por WiFi
        self.guardar_chaleco()
        self.transmitir_wifi("Lote finalizado correctamente.")
        
        # Bloquear los campos de texto y botones
        self.add_chaleco_button.disabled = True
        self.finalizar_lote_button.disabled = True
        self.comenzar_lote_button.disabled = False

        # Mostrar un popup indicando que el lote fue finalizado
        popup = Popup(title='Lote Finalizado', content=Label(text='El lote ha sido finalizado y los chalecos han sido registrados.'), size_hint=(None, None), size=(400, 200))
        popup.open()

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

    def transmitir_wifi(self, mensaje):
        # Simular transmisión de datos por WiFi usando sockets
        HOST = '0.0.0.0'  # Dirección IP del servidor
        PORT = 12345  # Puerto del servidor

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((HOST, PORT))
            s.sendall(mensaje.encode())
            print(f"Transmisión por WiFi: {mensaje}")

    def ver_registro(self, instance):
        # Leer archivo de registros y mostrar en un popup
        try:
            with open("registro_chalecos.txt", "r") as file:
                contenido = file.read()
        except FileNotFoundError:
            contenido = "No hay registros disponibles."

        popup = Popup(title='Registros de Chalecos', content=Label(text=contenido), size_hint=(None, None), size=(400, 400))
        popup.open()

    def on_key_down(self, window, key, *args):
        if key == 9:  # Código de la tecla 'Tab'
            self.focus_next_widget()
        return True

    def focus_next_widget(self):
        # Mover el foco al siguiente widget de texto
        focus_widget = self.numero_serie_input if self.numero_serie_input.focus else \
                       self.fabricante_input if self.fabricante_input.focus else \
                       self.fecha_fabricacion_input if self.fecha_fabricacion_input.focus else \
                       self.fecha_vencimiento_input if self.fecha_vencimiento_input.focus else \
                       self.tipo_modelo_input if self.tipo_modelo_input.focus else \
                       self.peso_input if self.peso_input.focus else \
                       self.talla_input if self.talla_input.focus else \
                       self.procedencia_input
        focus_widget.focus = True

if __name__ == '__main__':
    ChalecoApp().run()
