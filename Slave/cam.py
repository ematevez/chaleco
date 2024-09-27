import cv2
import threading
import sqlite3
from datetime import datetime
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.clock import Clock
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
import base64
import json
import socket
import uuid
import time
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# Variables globales
server_running = True  # Controla si el servidor está activo
scan_thread = None
qr_last_seen = ""
qr_last_time = 0
qr_hold_time = 5  # Tiempo en segundos que el QR debe mantenerse estable
qr_timer_started = False

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
def insert_data(chaleco):
    conn = sqlite3.connect('chalecos.db')
    cursor = conn.cursor()
    
    fecha_recepcion = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    fecha_entrada = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    qr_image_base64 = chaleco.get('QR Image', None)
    
    if qr_image_base64 and isinstance(qr_image_base64, str):
        qr_image_blob = convert_base64_to_image(qr_image_base64)
    else:
        qr_image_blob = None

    cursor.execute('''INSERT INTO chalecos_receptora 
        (lote, numero_serie, fabricante, fecha_fabricacion, fecha_vencimiento, 
         tipo_modelo, peso, talla, procedencia, qr_image, fecha_recepcion, fecha_entrada, destruido)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
        (
            chaleco.get('Lote', ''), 
            chaleco.get('Número de Serie', ''), 
            chaleco.get('Fabricante', ''), 
            chaleco.get('Fecha de Fabricación', ''), 
            chaleco.get('Fecha de Vencimiento', ''), 
            chaleco.get('Tipo de Modelo', ''), 
            chaleco.get('Peso', ''), 
            chaleco.get('Talla', ''), 
            chaleco.get('Procedencia', ''), 
            qr_image_blob, 
            fecha_recepcion, 
            fecha_entrada, 
            0
        )
    )
    
    conn.commit()
    conn.close()
    print("Datos insertados correctamente en la base de datos.")

# Función para manejar el servidor en un hilo
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

        data = b""
        while True:
            packet = client_socket.recv(1024)
            if not packet:
                break
            data += packet

        print(f"Datos recibidos: {data.decode('utf-8')}")

        try:
            chaleco_data = json.loads(data.decode('utf-8'))
            print(f"Datos JSON decodificados correctamente: {chaleco_data}")

            if isinstance(chaleco_data['data'], list):
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
    cursor.execute("SELECT * FROM chalecos_receptora WHERE destruido = 0")
    data = cursor.fetchall()
    conn.close()
    return data

# Función para obtener los datos necesarios para el informe
def get_data_for_report():
    conn = sqlite3.connect('chalecos.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM chalecos_receptora WHERE destruido IN (1, 2)")
    data = cursor.fetchall()
    conn.close()
    return data

# Función para guardar la imagen con la fecha y hora
def save_image(frame, primary_key):
    datetime_str = get_current_datetime()
    filename = f"{primary_key}_{datetime_str}.png"
    
    cv2.putText(frame, f"Fecha: {datetime_str}", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    
    cv2.imwrite(filename, frame)
    print(f"Imagen guardada como {filename}")
    return filename

# Función para obtener la fecha y hora actual en formato "YYYYMMDD_HHMMSS"
def get_current_datetime():
    return datetime.now().strftime("%Y%m%d_%H%M%S")

# Función modificada para escanear QR con la lógica de tiempo de visibilidad
def scan_qr():
    global qr_last_seen, qr_last_time, qr_timer_started
    cap = cv2.VideoCapture(0)  # Abre la cámara
    qr_detector = cv2.QRCodeDetector()

    if not cap.isOpened():
        print("Error: No se puede abrir la cámara.")
        return

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error al capturar la imagen")
            break

        qr_value, pts, _ = qr_detector.detectAndDecode(frame)

        if qr_value:
            if qr_value == qr_last_seen:
                if not qr_timer_started:
                    qr_last_time = time.time()
                    qr_timer_started = True
                elif time.time() - qr_last_time >= qr_hold_time:
                    print(f"QR detectado y estable por {qr_hold_time} segundos. Habilitando botón de destrucción.")
                    app_instance.enable_destruction_button()
            else:
                qr_last_seen = qr_value
                qr_timer_started = False

            cv2.putText(frame, f"QR: {qr_value}", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

            if pts is not None and len(pts) == 4:
                pts = pts.astype(int)
                for i in range(4):
                    pt1 = tuple(pts[i][0])
                    pt2 = tuple(pts[(i + 1) % 4][0])
                    cv2.line(frame, pt1, pt2, (0, 255, 0), 2)

        else:
            qr_last_seen = ""
            qr_timer_started = False
            cv2.putText(frame, "No QR detected", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        cv2.imshow('QR Scanner', frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

# Función para generar el informe PDF
def generate_pdf_report():
    data = get_data_for_report()
    if not data:
        show_popup("No hay chalecos destruidos para generar el informe.")
        return

    pdf_filename = f"reporte_chalecos_{get_current_datetime()}.pdf"
    c = canvas.Canvas(pdf_filename, pagesize=A4)
    width, height = A4

    y_position = height - 50
    c.drawString(100, y_position, "Informe de Chalecos Destruidos")
    y_position -= 50

    for row in data:
        text = f"Lote: {row[1]}, Serie: {row[2]}, Destruido: {'Sí' if row[12] == 1 else 'No'}"
        c.drawString(100, y_position, text)
        y_position -= 20

        if y_position < 50:
            c.showPage()
            y_position = height - 50

    c.save()
    show_popup(f"Informe PDF generado: {pdf_filename}")

# Clase de la interfaz gráfica
class ChalecoApp(App):
    def enable_destruction_button(self):
        self.destruction_button.disabled = False

    def build(self):
        layout = BoxLayout(orientation='vertical')
        
        # Botón para destruir chaleco
        self.destruction_button = Button(text='Destruir Chaleco', disabled=True, on_press=self.on_destruction_button)
        layout.add_widget(self.destruction_button)

        # Botón para iniciar el servidor
        start_server_button = Button(text="Iniciar servidor", on_press=self.on_start_server)
        layout.add_widget(start_server_button)

        # Botón para detener el servidor
        stop_server_button = Button(text="Detener servidor", on_press=self.on_stop_server)
        layout.add_widget(stop_server_button)

        # Botón para generar el informe PDF
        generate_report_button = Button(text="Generar informe PDF", on_press=self.on_generate_report)
        layout.add_widget(generate_report_button)

        # Sección para mostrar chalecos no destruidos
        self.chaleco_list = GridLayout(cols=1, spacing=10, size_hint_y=None)
        self.chaleco_list.bind(minimum_height=self.chaleco_list.setter('height'))
        
        scroll = ScrollView(size_hint=(1, 1))
        scroll.add_widget(self.chaleco_list)
        layout.add_widget(scroll)

        # Actualizar la lista de chalecos no destruidos cada 5 segundos
        Clock.schedule_interval(self.update_chaleco_list, 5)

        return layout

    def on_destruction_button(self, instance):
        global qr_last_seen
        if qr_last_seen:
            print(f"Chaleco con QR {qr_last_seen} destruido.")
            conn = sqlite3.connect('chalecos.db')
            cursor = conn.cursor()
            cursor.execute("UPDATE chalecos_receptora SET destruido = 1 WHERE numero_serie = ?", (qr_last_seen,))
            conn.commit()
            conn.close()
            self.update_chaleco_list()  # Actualizar la lista tras la destrucción

    def on_start_server(self, instance):
        global scan_thread
        scan_thread = threading.Thread(target=start_server)
        scan_thread.start()

    def on_stop_server(self, instance):
        stop_server()

    def on_generate_report(self, instance):
        generate_pdf_report()

    def update_chaleco_list(self, *args):
        self.chaleco_list.clear_widgets()  # Limpiar lista antes de actualizarla
        data = get_data_from_db()

        if not data:
            self.chaleco_list.add_widget(Label(text="No hay chalecos no destruidos."))
        else:
            for row in data:
                text = f"Lote: {row[1]}, Serie: {row[2]}"
                label = Label(text=text, size_hint_y=None, height=40)
                self.chaleco_list.add_widget(label)

def show_popup(message):
    popup = Popup(title='Mensaje', content=Label(text=message), size_hint=(None, None), size=(400, 200))
    popup.open()

if __name__ == '__main__':
    create_table()
    app_instance = ChalecoApp()
    app_instance.run()
