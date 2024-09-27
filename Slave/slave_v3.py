import socket
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.popup import Popup
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.core.window import Window
import sqlite3
from datetime import datetime
import threading

# Comentado para hacer pruebas en tamaño normal
# Window.fullscreen = True

class MainApp(App):
    def build(self):
        self.title = "Sistema de Registro y QR"

        # Crear la conexión a la base de datos
        self.conn = sqlite3.connect('registros.db')
        self.crear_tabla_chalecos()

        # ScrollView para que los elementos sean desplazables
        root_layout = ScrollView(size_hint=(1, None), size=(Window.width, Window.height))
        main_layout = BoxLayout(orientation="vertical", padding=20, spacing=20, size_hint_y=None)
        main_layout.bind(minimum_height=main_layout.setter('height'))

        # Layout del formulario
        form_layout = GridLayout(cols=2, spacing=10, size_hint_y=None, height=600)
        form_layout.bind(minimum_height=form_layout.setter('height'))

        # Campos del formulario con tamaño dinámico
        self.form_data = {}
        fields = [
            ("Número de Serie", TextInput(size_hint=(1, None), height=40)),
            ("Número de Lote", TextInput(size_hint=(1, None), height=40)),
            ("Fabricante", TextInput(size_hint=(1, None), height=40)),
            ("Fecha de Fabricación", TextInput(size_hint=(1, None), height=40)),
            ("Fecha de Vencimiento", TextInput(size_hint=(1, None), height=40)),
            ("Tipo de Modelo", TextInput(size_hint=(1, None), height=40)),
            ("Peso", TextInput(size_hint=(1, None), height=40)),
            ("Talla", TextInput(size_hint=(1, None), height=40)),
            ("Proveniente de", TextInput(size_hint=(1, None), height=40))
        ]

        for label, widget in fields:
            form_layout.add_widget(Label(text=label, size_hint=(1, None), height=40))
            form_layout.add_widget(widget)
            self.form_data[label] = widget

        main_layout.add_widget(form_layout)

        # Botones para iniciar y finalizar la escucha
        button_layout = BoxLayout(size_hint_y=None, height=50, spacing=10)

        # Botón para iniciar la escucha
        self.btn_iniciar_escucha = Button(text="Iniciar Escucha", on_press=self.iniciar_escucha, size_hint=(1, None), height=50)
        button_layout.add_widget(self.btn_iniciar_escucha)

        # Botón para finalizar la escucha
        self.btn_finalizar_escucha = Button(text="Finalizar Escucha", on_press=self.finalizar_escucha, size_hint=(1, None), height=50, disabled=True)
        button_layout.add_widget(self.btn_finalizar_escucha)

        main_layout.add_widget(button_layout)
        root_layout.add_widget(main_layout)

        # Variable de control para el hilo de escucha
        self.escuchando = False
        self.hilo_escucha = None

        return root_layout

    def crear_tabla_chalecos(self):
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
                transmitido INTEGER DEFAULT 0,
                fecha_recepcion TEXT
            )
        ''')
        self.conn.commit()

    def iniciar_escucha(self, instance):
        self.escuchando = True
        self.btn_iniciar_escucha.disabled = True
        self.btn_finalizar_escucha.disabled = False
        self.hilo_escucha = threading.Thread(target=self.recibir_datos_del_master)
        self.hilo_escucha.start()

    def finalizar_escucha(self, instance):
        self.escuchando = False
        self.btn_iniciar_escucha.disabled = False
        self.btn_finalizar_escucha.disabled = True
        if self.hilo_escucha:
            self.hilo_escucha.join()

    def recibir_datos_del_master(self):
        try:
            # Conectar al Master para recibir datos
            # ip_master = '192.168.10.10'
            ip_master = '192.168.10.114'
            # ip_master = '0.0.0.0'
            puerto_master = 8000
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((ip_master, puerto_master))

            while self.escuchando:
                # Recibir datos
                datos_recibidos = sock.recv(4096).decode()
                if not datos_recibidos:
                    break

                # Descomponer y guardar los datos en la base de datos
                registros = datos_recibidos.split('\n')
                fecha_actual = datetime.now().strftime("%Y-%m-%d")

                cursor = self.conn.cursor()
                for registro in registros:
                    partes = registro.split(", ")
                    datos = {
                        'lote': partes[0].split(": ")[1],
                        'numero_serie': partes[1].split(": ")[1],
                        'fabricante': partes[2].split(": ")[1]
                    }
                    # Insertar en la base de datos con fecha de recepción
                    cursor.execute('''
                        INSERT INTO chalecos (lote, numero_serie, fabricante, fecha_recepcion, transmitido)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (datos['lote'], datos['numero_serie'], datos['fabricante'], fecha_actual, 1))
                self.conn.commit()

            self.mostrar_popup("Éxito", "Datos recibidos y guardados con éxito")
            sock.close()

        except Exception as e:
            self.mostrar_popup("Error", f"No se pudo conectar al Master: {str(e)}")

    def mostrar_popup(self, titulo, mensaje):
        popup = Popup(title=titulo, content=Label(text=mensaje), size_hint=(0.6, 0.3))
        popup.open()

if __name__ == '__main__':
    MainApp().run()
