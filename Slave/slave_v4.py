import socket
import sqlite3
import json
from datetime import datetime
from kivy.app import App
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView

class ChalecoReceiverApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.conn = self.create_new_db()

    # Crear la nueva base de datos donde se guardarán los chalecos
    def create_new_db(self):
        conn = sqlite3.connect('chalecos_receptora.db')
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chalecos_receptora (
                lote TEXT,
                numero_serie TEXT,
                fabricante TEXT,
                fecha_fabricacion TEXT,
                fecha_vencimiento TEXT,
                tipo_modelo TEXT,
                peso TEXT,
                talla TEXT,
                procedencia TEXT,
                qr_image BLOB,  
                fecha_recepcion TEXT
            )
        ''')
        conn.commit()
        return conn

    # Insertar los datos en la base de datos receptora
    def insert_data(self, data):
        cursor = self.conn.cursor()
        for chaleco in data:
            fecha_recepcion = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute('''
                INSERT INTO chalecos_receptora 
                (lote, numero_serie, fabricante, fecha_fabricacion, fecha_vencimiento, 
                 tipo_modelo, peso, talla, procedencia, qr_image, fecha_recepcion)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (chaleco['lote'], chaleco['numero_serie'], chaleco['fabricante'], 
                  chaleco['fecha_fabricacion'], chaleco['fecha_vencimiento'], 
                  chaleco['tipo_modelo'], chaleco['peso'], chaleco['talla'], 
                  chaleco['procedencia'], chaleco['qr_image'], fecha_recepcion))
        self.conn.commit()

    # Escuchar por el puerto 8000 y recibir datos

    def start_server(self):
        host = '0.0.0.0'
        port = 8000

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.bind((host, port))
            server_socket.listen()
            print(f'Servidor escuchando en {host}:{port}...')

            while True:
                client_socket, address = server_socket.accept()
                with client_socket:
                    print(f'Conexión recibida de {address}')
                    data = client_socket.recv(1024)
                    
                    if data:
                        try:
                            # Intentar decodificar los datos como JSON
                            chaleco_data = json.loads(data.decode('utf-8'))
                            print("Datos recibidos y decodificados correctamente:", chaleco_data)
                            
                            # Crear una nueva conexión en este hilo para la base de datos
                            conn = sqlite3.connect('nombre_de_tu_base_de_datos.db')
                            
                            # Insertar los datos en la base de datos
                            self.insert_data(chaleco_data['data'], conn)
                            
                            # Enviar confirmación al cliente
                            confirmacion = 'OK'
                            client_socket.sendall(confirmacion.encode())
                            print(f"Mensaje enviado al cliente: '{confirmacion}'")
                            
                            # Cerrar la conexión SQLite después de procesar
                            conn.close()
                            
                        except json.JSONDecodeError:
                            print("Error al decodificar los datos recibidos como JSON")
                            client_socket.sendall("Error: datos no válidos".encode())
                        except Exception as e:
                            print(f"Error al procesar los datos: {e}")
                            client_socket.sendall(f"Error: {str(e)}".encode())


    # Mostrar los datos en una tabla usando Kivy
    def build(self):
        layout = GridLayout(cols=5, spacing=10, size_hint_y=None)
        layout.bind(minimum_height=layout.setter('height'))

        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM chalecos_receptora")
        chalecos = cursor.fetchall()

        # Agregar encabezados de columna
        headers = ['Lote', 'Número de Serie', 'Fabricante', 'Fecha Fabricación', 'Fecha Recepción']
        for header in headers:
            layout.add_widget(Label(text=header, bold=True))

        # Agregar datos de la tabla
        for chaleco in chalecos:
            layout.add_widget(Label(text=chaleco[0]))  # lote
            layout.add_widget(Label(text=chaleco[1]))  # numero_serie
            layout.add_widget(Label(text=chaleco[2]))  # fabricante
            layout.add_widget(Label(text=chaleco[3]))  # fecha_fabricacion
            layout.add_widget(Label(text=chaleco[-1]))  # fecha_recepcion

        scrollview = ScrollView(size_hint=(1, None), size=(800, 600))
        scrollview.add_widget(layout)
        return scrollview

if __name__ == '__main__':
    app = ChalecoReceiverApp()
    
    # Puedes ejecutar el servidor en un hilo separado para que funcione junto con la UI de Kivy
    import threading
    server_thread = threading.Thread(target=app.start_server)
    server_thread.daemon = True
    server_thread.start()
    
    app.run()
