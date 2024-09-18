import datetime
import random
import socket
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
        lote = self.lote_input.text
        numero_serie = self.numero_serie_input.text
        fabricante = self.fabricante_input.text
        fecha_fabricacion = self.fecha_fabricacion_input.text
        fecha_vencimiento = self.fecha_vencimiento_input.text
        tipo_modelo = self.tipo_modelo_input.text
        peso = self.peso_input.text
        talla = self.talla_input.text
        procedencia = self.procedencia_input.text

        with open("registro_chalecos.txt", "a") as file:
            file.write(f"Lote: {lote}, Serie: {numero_serie}, Fabricante: {fabricante}, Fecha Fabricación: {fecha_fabricacion}, Fecha Vencimiento: {fecha_vencimiento}, Tipo: {tipo_modelo}, Peso: {peso}, Talla: {talla}, Procedencia: {procedencia}\n")

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

        # Leer registros
        registros = []
        try:
            with open("registro_chalecos.txt", "r") as file:
                registros = file.readlines()
        except FileNotFoundError:
            registros = []

        self.checkboxes = []

        # Mostrar los registros con un checkbox para seleccionar
        for registro in registros:
            checkbox = CheckBox()
            label = Label(text=registro.strip(), size_hint_y=None, height=40)
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
            self.transmitir_wifi("\n".join(registros_seleccionados))

            # Marcar como transmitidos
            for checkbox, _ in self.checkboxes:
                if checkbox.active:
                    checkbox.disabled = True

            popup = Popup(title='Éxito', content=Label(text='Registros transmitidos con éxito'), size_hint=(None, None), size=(400, 200))
            popup.open()
        else:
            popup = Popup(title='Error', content=Label(text='No hay registros seleccionados'), size_hint=(None, None), size=(400, 200))
            popup.open()

        self.popup_transmision.dismiss()

    def transmitir_wifi(self, mensaje):
        HOST = '192.168.10.10'  # IP del servidor que recibirá los datos
        PORT = 8000  # Puerto del servidor

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((HOST, PORT))
            s.sendall(mensaje.encode())
            respuesta = s.recv(1024)

        print(f"Respuesta del servidor: {respuesta.decode()}")

    def ver_registro(self, instance):
        try:
            with open("registro_chalecos.txt", "r") as file:
                registro = file.read()
        except FileNotFoundError:
            registro = "No hay registros disponibles."

        popup = Popup(title='Registro de Chalecos', content=Label(text=registro), size_hint=(None, None), size=(600, 400))
        popup.open()

    def campos_llenos(self):
        return all([self.numero_serie_input.text, self.fabricante_input.text, self.fecha_fabricacion_input.text, self.fecha_vencimiento_input.text, self.tipo_modelo_input.text, self.peso_input.text, self.talla_input.text, self.procedencia_input.text])

    def on_key_down(self, window, key, *args):
        if key == 9:  # Tab key
            self.focus_next()

    def focus_next(self):
        focusable_elements = [
            self.numero_serie_input, self.fabricante_input, self.fecha_fabricacion_input,
            self.fecha_vencimiento_input, self.tipo_modelo_input, self.peso_input,
            self.talla_input, self.procedencia_input
        ]
        current_focus = None
        for element in focusable_elements:
            if element.focus:
                current_focus = element
                break

        if current_focus:
            index = focusable_elements.index(current_focus)
            next_index = (index + 1) % len(focusable_elements)
            focusable_elements[next_index].focus = True


if __name__ == '__main__':
    ChalecoApp().run()
