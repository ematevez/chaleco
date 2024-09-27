import socket
import sqlite3
from datetime import datetime
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
import threading
import json
import base64


import cv2
import numpy as np
from pyzbar.pyzbar import decode
from kivy.uix.popup import Popup




# Variables globales
server_running = True  # Controla si el servidor está activo

# Función para crear la base de datos y la tabla
def create_table():
    conn = sqlite3.connect('chalecos.db')
    cursor = conn.cursor()
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS chalecos_receptora (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        lote TEXT NOT NULL,
                        numero_serie TEXT NOT NULL,
                        fabricante TEXT NOT NULL,
                        fecha_fabricacion TEXT,
                        fecha_vencimiento TEXT,
                        tipo_modelo TEXT,
                        peso TEXT,
                        talla TEXT,
                        procedencia TEXT,
                        qr_image BLOB,
                        fecha_recepcion TEXT,
                        fecha_entrada TEXT,
                        destruido INTEGER DEFAULT 0
                    )''')
    
    conn.commit()
    conn.close()

# Función para convertir una imagen a Base64
def convert_image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
    return encoded_string

# Función para decodificar Base64 a binario (para imágenes)
def convert_base64_to_image(base64_string):
    return base64.b64decode(base64_string)

# Función para insertar datos en la base de datos
# Función para insertar datos en la base de datos
def insert_data(chaleco):
    conn = sqlite3.connect('chalecos.db')
    cursor = conn.cursor()
    
    # Obtener la fecha actual para el campo fecha_recepcion y fecha_entrada
    fecha_recepcion = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    fecha_entrada = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Fecha de ingreso actual
    
    # Convertir la imagen QR a binario desde Base64 si es necesario
    qr_image_base64 = chaleco.get('QR Image', None)
    
    if qr_image_base64 and isinstance(qr_image_base64, str):
        qr_image_blob = convert_base64_to_image(qr_image_base64)
    else:
        qr_image_blob = None

    # Insertar los datos en la tabla con todos los campos
    cursor.execute('''INSERT INTO chalecos_receptora 
        (lote, numero_serie, fabricante, fecha_fabricacion, fecha_vencimiento, 
         tipo_modelo, peso, talla, procedencia, qr_image, fecha_recepcion, fecha_entrada, destruido)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
        (
            chaleco.get('Lote', ''), 
            chaleco.get('Número de Serie', ''),  # Cambiado para usar 'Número de Serie'
            chaleco.get('Fabricante', ''), 
            chaleco.get('Fecha de Fabricación', ''),  # Usar formato correcto
            chaleco.get('Fecha de Vencimiento', ''), 
            chaleco.get('Tipo de Modelo', ''), 
            chaleco.get('Peso', ''), 
            chaleco.get('Talla', ''), 
            chaleco.get('Procedencia', ''), 
            qr_image_blob,  # Aquí insertamos el QR como blob
            fecha_recepcion,  # Fecha de recepción actual
            fecha_entrada,  # Fecha de entrada (fecha actual)
            0  # Campo destruido, inicialmente 0 (no destruido)
        )
    )
    
    conn.commit()
    conn.close()
    print("Datos insertados correctamente en la base de datos.")


# Función para manejar el servidor
def start_server():
    global server_running
    host = '0.0.0.0'
    port = 8000

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(5)

    print(f"Servidor escuchando en {host}:{port}...")

    while server_running:
        client_socket, client_address = server_socket.accept()
        print(f"Conexión recibida de {client_address}")

        # Recibir todos los datos del cliente
        data = b""
        while True:
            packet = client_socket.recv(1024)
            if not packet:
                break
            data += packet

        print(f"Datos recibidos: {data.decode('utf-8')}")

        try:
            # Decodificar JSON
            chaleco_data = json.loads(data.decode('utf-8'))
            print(f"Datos JSON decodificados correctamente: {chaleco_data}")

            # Asegurarse de que chaleco_data['data'] sea una lista
            if isinstance(chaleco_data['data'], list):
                # Insertar cada chaleco en la base de datos
                for chaleco in chaleco_data['data']:
                    insert_data(chaleco)
            else:
                print("Error: formato de datos incorrecto, 'data' debe ser una lista de chalecos")

        except json.JSONDecodeError as e:
            print(f"Error al decodificar JSON: {e}")
            print("Datos que causaron el error:", data.decode('utf-8'))

        client_socket.close()

    server_socket.close()
    print("Servidor detenido.")


# Función para detener el servidor
def stop_server():
    global server_running
    server_running = False

# Función para obtener los datos de la base de datos
def get_data_from_db():
    conn = sqlite3.connect('chalecos.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM chalecos_receptora")
    data = cursor.fetchall()
    conn.close()
    return data

# Clase de la aplicación Kivy
class ChalecoApp(App):
    def build(self):
        self.layout = BoxLayout(orientation='vertical')
        self.data_layout = GridLayout(cols=5, size_hint_y=None)
        self.data_layout.bind(minimum_height=self.data_layout.setter('height'))
        self.scroll = ScrollView(size_hint=(1, 0.8))
        self.scroll.add_widget(self.data_layout)
        
        # Botón para actualizar
        self.update_button = Button(text='Actualizar', size_hint=(1, 0.2))
        self.update_button.bind(on_press=self.update_data)
        
        # Añadir todo al layout
        self.layout.add_widget(self.scroll)
        self.layout.add_widget(self.update_button)
        
        # Cargar datos iniciales
        self.update_data(None)
        
        return self.layout
    
    # Función para actualizar los datos en la tabla
    def update_data(self, instance):
        # Limpiar el layout antes de añadir los datos nuevos
        self.data_layout.clear_widgets()
        
        # Obtener datos de la base de datos
        data = get_data_from_db()
        
        # Añadir datos al layout
        for row in data:
            self.data_layout.add_widget(Label(text=row[1]))  # Lote
            self.data_layout.add_widget(Label(text=row[2]))  # Número de serie
            self.data_layout.add_widget(Label(text=row[3]))  # Fabricante
            self.data_layout.add_widget(Label(text=row[4]))  # Fecha de fabricación
            self.data_layout.add_widget(Label(text=row[5]))  # Fecha de vencimiento
            self.data_layout.add_widget(Label(text=row[6]))  # Tipo de modelo
            self.data_layout.add_widget(Label(text=row[7]))  # Peso
            self.data_layout.add_widget(Label(text=row[8]))  # Talla
            self.data_layout.add_widget(Label(text=row[9]))  # Procedencia
            self.data_layout.add_widget(Label(text="QR disponible" if row[10] else 'Sin QR'))  # QR Image
            self.data_layout.add_widget(Label(text=row[11]))  # Fecha de recepción
            self.data_layout.add_widget(Label(text=row[12]))  # Fecha de entrada

# Iniciar la aplicación de Kivy
if __name__ == "__main__":
    create_table()  # Crear la tabla en la base de datos si no existe
    threading.Thread(target=start_server).start()  # Iniciar el servidor en un hilo separado
    ChalecoApp().run()
    stop_server()  # Detener el servidor cuando se cierre la aplicación
