import kivy
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.core.window import Window
import sqlite3
from datetime import datetime
import random
import qrcode
from io import BytesIO
from kivy.uix.image import Image as KivyImage
from kivy.core.image import Image as CoreImage
import os

# Función para convertir texto a mayúsculas
def convertir_a_mayusculas(instance, value):
    instance.text = value.upper()

# Función para cambiar el foco con teclas (Up y Down)
def cambiar_foco_con_tecla(widget_list):
    def manejar_tecla(instance, keyboard, keycode, text, modifiers):
        if keycode == 40 or keycode == 13:  # Enter or Down key
            focus_index = widget_list.index(instance)
            next_focus = widget_list[(focus_index + 1) % len(widget_list)]
            next_focus.focus = True
        elif keycode == 38:  # Up key
            focus_index = widget_list.index(instance)
            next_focus = widget_list[(focus_index - 1) % len(widget_list)]
            next_focus.focus = True
        return True
    return manejar_tecla

# DatePicker para seleccionar fechas
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
            popup = Popup(
                title='Error',
                content=Label(text='Debe seleccionar Año, Mes y Día.'),
                size_hint=(None, None),
                size=(400, 200)
            )
            popup.open()


class ChalecoApp(App):
    def build(self):
        self.conn = sqlite3.connect('estacion_A.db')  # Cambia el nombre de la estación aquí
        self.create_db()

        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        # Campos de texto para los datos (inicialmente deshabilitados)
        self.lote_input = TextInput(hint_text='Lote (autogenerado)', disabled=True)
        self.numero_serie_input = TextInput(hint_text='Número de Serie', disabled=True)
        self.fabricante_input = TextInput(hint_text='Fabricante', disabled=True)

        # Botones para seleccionar las fechas (inicialmente deshabilitados)
        self.fecha_fabricacion_input = TextInput(hint_text='Fecha de Fabricación (YYYY-MM-DD)', readonly=True, disabled=True)
        self.btn_fecha_fabricacion = Button(text='Seleccionar Fecha de Fabricación', on_press=self.abrir_datepicker_fabricacion, disabled=True)
        self.fecha_vencimiento_input = TextInput(hint_text='Fecha de Vencimiento (YYYY-MM-DD)', readonly=True, disabled=True)
        self.btn_fecha_vencimiento = Button(text='Seleccionar Fecha de Vencimiento', on_press=self.abrir_datepicker_vencimiento, disabled=True)

        self.tipo_modelo_input = TextInput(hint_text='Tipo/Modelo', disabled=True)
        self.peso_input = TextInput(hint_text='Peso', disabled=True)
        self.talla_spinner = Spinner(text='Seleccionar Talla', values=('XS', 'S', 'M', 'L', 'XL', 'XXL'), disabled=True)
        self.procedencia_input = TextInput(hint_text='Procedencia', disabled=True)

        # Lista de los widgets para el enfoque
        widgets = [
            self.numero_serie_input,
            self.fabricante_input,
            self.fecha_fabricacion_input,
            self.fecha_vencimiento_input,
            self.tipo_modelo_input,
            self.peso_input,
            self.talla_spinner,
            self.procedencia_input
        ]

        # Añadir manejador de eventos para teclas y texto en mayúsculas
        for widget in widgets:
            if isinstance(widget, TextInput):
                widget.bind(text=convertir_a_mayusculas)  # Convertir a mayúsculas
                widget.bind(on_text_validate=cambiar_foco_con_tecla(widgets))  # Cambiar foco con Enter o Down
                widget.bind(focus=cambiar_foco_con_tecla(widgets))

        # Añadir los campos y botones al layout
        layout.add_widget(self.lote_input)
        layout.add_widget(self.numero_serie_input)
        layout.add_widget(self.fabricante_input)

        layout.add_widget(self.fecha_fabricacion_input)
        layout.add_widget(self.btn_fecha_fabricacion)
        layout.add_widget(self.fecha_vencimiento_input)
        layout.add_widget(self.btn_fecha_vencimiento)

        layout.add_widget(self.tipo_modelo_input)
        layout.add_widget(self.peso_input)
        layout.add_widget(self.talla_spinner)
        layout.add_widget(self.procedencia_input)

        # Botones de acción
        self.btn_comenzar_lote = Button(text="Comenzar Lote", on_press=self.comenzar_lote)
        self.btn_agregar_chaleco = Button(text="Agregar Chaleco", on_press=self.agregar_chaleco, disabled=True)
        self.btn_finalizar_lote = Button(text="Finalizar Lote", on_press=self.finalizar_lote, disabled=True)
        self.btn_ver_registros = Button(text="Ver Registros", on_press=self.ver_registros)

        # Añadir los botones al layout
        layout.add_widget(self.btn_comenzar_lote)
        layout.add_widget(self.btn_agregar_chaleco)
        layout.add_widget(self.btn_finalizar_lote)
        layout.add_widget(self.btn_ver_registros)

        return layout

    def create_db(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chalecos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lote TEXT,
                numero_serie TEXT,
                fabricante TEXT,
                fecha_fabricacion TEXT,
                fecha_vencimiento TEXT,
                tipo_modelo TEXT,
                peso TEXT,
                talla TEXT,
                procedencia TEXT,
                estacion TEXT
            )
        ''')
        self.conn.commit()

    def comenzar_lote(self, instance):
        estacion = 'A'  # Cambia la estación según sea A, B o C
        lote_id = random.randint(1000, 9999)
        fecha_actual = datetime.now().strftime("%Y%m%d")
        self.lote_numero = f"{estacion}{lote_id}-{fecha_actual}"
        self.lote_input.text = self.lote_numero

        self.btn_comenzar_lote.disabled = True
        self.habilitar_campos()

    def agregar_chaleco(self, instance):
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
            INSERT INTO chalecos (lote, numero_serie, fabricante, fecha_fabricacion, fecha_vencimiento, tipo_modelo, peso, talla, procedencia, estacion)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (self.lote_numero, numero_serie, fabricante, fecha_fabricacion, fecha_vencimiento, tipo_modelo, peso, talla, procedencia, 'A'))

        self.conn.commit()
        self.limpiar_campos()

    def finalizar_lote(self, instance):
        if not self.validar_campos_llenos():
            popup = Popup(title='Error', content=Label(text='Debe llenar todos los campos.'), size_hint=(None, None), size=(400, 200))
            popup.open()
            return
        self.generar_qr()
        self.limpiar_campos()
        self.deshabilitar_campos()
        self.btn_agregar_chaleco.disabled = True
        self.btn_finalizar_lote.disabled = True
        self.btn_comenzar_lote.disabled = False

    def generar_qr(self):
        qr_data = f"Lote: {self.lote_numero}"
        qr = qrcode.make(qr_data)
        buffer = BytesIO()
        qr.save(buffer, format="PNG")
        buffer.seek(0)

        # Guardar la imagen del QR en un archivo temporal
        qr_file = f"qr_{self.lote_numero}.png"
        with open(qr_file, 'wb') as f:
            f.write(buffer.getvalue())

        # Mostrar la imagen del QR en la interfaz
        image_texture = CoreImage(buffer, ext="png").texture
        image = KivyImage(texture=image_texture, size_hint=(1, 1))

        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        layout.add_widget(Label(text=f'QR del lote: {self.lote_numero}'))
        layout.add_widget(image)

        # Botón para abrir el QR en el explorador de archivos
        btn_abrir = Button(text="Abrir en el explorador", size_hint=(1, None), height=44)
        btn_abrir.bind(on_press=lambda instance: self.abrir_qr_en_explorador(qr_file))

        layout.add_widget(btn_abrir)

        popup = Popup(title='QR Generado', content=layout, size_hint=(0.6, 0.6))
        popup.open()

    def abrir_qr_en_explorador(self, qr_file):
        # Abrir el archivo en el explorador
        if os.name == 'nt':  # Windows
            os.startfile(qr_file)
        elif os.name == 'posix':  # Linux/Mac
            os.system(f"xdg-open {qr_file}")

    def ver_registros(self, instance):
        # Crear una ventana emergente para mostrar los registros de la base de datos
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        scroll_view = ScrollView(size_hint=(1, 1))

        # Crear una tabla para mostrar los registros
        table = BoxLayout(orientation='vertical', size_hint_y=None)
        table.bind(minimum_height=table.setter('height'))

        # Agregar encabezados de columna
        headers = BoxLayout(orientation='horizontal', size_hint_y=None, height=30)
        headers.add_widget(Label(text='Lote', size_hint_x=0.2))
        headers.add_widget(Label(text='Número de Serie', size_hint_x=0.2))
        headers.add_widget(Label(text='Fabricante', size_hint_x=0.2))
        headers.add_widget(Label(text='Fecha Fab.', size_hint_x=0.2))
        headers.add_widget(Label(text='Fecha Venc.', size_hint_x=0.2))
        table.add_widget(headers)

        # Consultar los registros de la base de datos
        cursor = self.conn.cursor()
        cursor.execute("SELECT lote, numero_serie, fabricante, fecha_fabricacion, fecha_vencimiento FROM chalecos")
        registros = cursor.fetchall()

        # Agregar cada registro a la tabla
        for registro in registros:
            row = BoxLayout(orientation='horizontal', size_hint_y=None, height=30)
            for item in registro:
                row.add_widget(Label(text=str(item), size_hint_x=0.2))
            table.add_widget(row)

        # Añadir la tabla al scroll view
        scroll_view.add_widget(table)
        layout.add_widget(scroll_view)

        # Mostrar los registros en un popup
        popup = Popup(title='Registros de Chalecos', content=layout, size_hint=(0.9, 0.9))
        popup.open()

    def limpiar_campos(self):
        self.numero_serie_input.text = ''
        self.fabricante_input.text = ''
        self.fecha_fabricacion_input.text = ''
        self.fecha_vencimiento_input.text = ''
        self.tipo_modelo_input.text = ''
        self.peso_input.text = ''
        self.talla_spinner.text = 'Seleccionar Talla'
        self.procedencia_input.text = ''
        self.lote_input.text = ''

    def habilitar_campos(self):
        self.numero_serie_input.disabled = False
        self.fabricante_input.disabled = False
        self.fecha_fabricacion_input.disabled = False
        self.btn_fecha_fabricacion.disabled = False
        self.fecha_vencimiento_input.disabled = False
        self.btn_fecha_vencimiento.disabled = False
        self.tipo_modelo_input.disabled = False
        self.peso_input.disabled = False
        self.talla_spinner.disabled = False
        self.procedencia_input.disabled = False
        self.btn_agregar_chaleco.disabled = False
        self.btn_finalizar_lote.disabled = False

    def deshabilitar_campos(self):
        self.numero_serie_input.disabled = True
        self.fabricante_input.disabled = True
        self.fecha_fabricacion_input.disabled = True
        self.btn_fecha_fabricacion.disabled = True
        self.fecha_vencimiento_input.disabled = True
        self.btn_vencimiento_input.disabled = True
        self.tipo_modelo_input.disabled = True
        self.peso_input.disabled = True
        self.talla_spinner.disabled = True
        self.procedencia_input.disabled = True

    def validar_campos_llenos(self):
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
