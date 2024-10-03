from __future__ import print_function
import cv2
import socket
import json
import sqlite3
import base64
import time
import threading
from datetime import datetime
from kivy.app import App
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from multiprocessing.pool import ThreadPool
from collections import deque
from dbr import *
import time
from util import *

# Inicializar licencia de Dynamsoft Barcode Reader (DBR)
BarcodeReader.init_license("DLS2eyJoYW5kc2hha2VDb2RlIjoiMjAwMDAxLTE2NDk4Mjk3OTI2MzUiLCJvcmdhbml6YXRpb25JRCI6IjIwMDAwMSIsInNlc3Npb25QYXNzd29yZCI6IndTcGR6Vm05WDJrcEQ5YUoifQ==")

server_running = True  # Controla si el servidor está activo
# Variables globales para el seguimiento de QR
qr_last_seen = ""
qr_last_time = 0
qr_timer_started = False
qr_hold_time = 5  # Tiempo requerido para habilitar la destrucción
scan_thread = None
# =================================================================================
class ScanManager:
    MODE_AUTO_STITCH = 0
    MODE_MANUAL_STITCH = 1
    MODE_CAMERA_ONLY = 2

    def __init__(self):
        modes = (cv2.Stitcher_PANORAMA, cv2.Stitcher_SCANS)
        self.stitcher = cv2.Stitcher.create(modes[1])
        self.stitcher.setPanoConfidenceThresh(0.1)
        self.panorama = []
        self.isPanoramaDone = False
        self.reader = BarcodeReader()
        
        # Ajustar los modos de escaneo
        self.settings = self.reader.get_runtime_settings()
        self.settings.barcode_format_ids = EnumBarcodeFormat.BF_QR_CODE  # Limitar al formato de código QR
        self.settings.expected_barcodes_count = 1  # Ajustar si esperas un solo código
        self.settings.min_result_confidence = 30  # Incrementar la confianza mínima

        # Configurar resolución (Si la imagen es muy pequeña)
        self.settings.scale_down_threshold = 1200  # Solo escalar si la imagen es más grande de 1200px

        # Aplicar configuración ajustada
        self.reader.update_runtime_settings(self.settings)

    def count_barcodes(self, frame):
        # Decodifica los códigos QR del frame
        results = self.reader.decode_buffer(frame)
        
        # Si no se detectan códigos (results es None), devolvemos 0
        if results is None:
            return 0
        
        # Retornamos la cantidad de códigos QR detectados
        return len(results)


    def save_frame(self, frame):
        filename = str(time.time()) + "_panorama.jpg"
        cv2.imwrite(filename, frame)
        print("Saved to " + filename)

    def frame_overlay(self, frame):
        frame_cp = frame.copy()
        try:
            results = self.reader.decode_buffer(frame_cp)
            if results is not None:
                for result in results:
                    points = result.localization_result.localization_points
                    cv2.line(frame_cp, points[0], points[1], (0, 255, 0), 2)
                    cv2.line(frame_cp, points[1], points[2], (0, 255, 0), 2)
                    cv2.line(frame_cp, points[2], points[3], (0, 255, 0), 2)
                    cv2.line(frame_cp, points[3], points[0], (0, 255, 0), 2)
                    cv2.putText(frame_cp, result.barcode_text, points[0], cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255))
                    
            return frame_cp
        except BarcodeReaderError as e:
            print(e)
            return None

    def stitch_frame(self, frame):
        try:
            results = self.reader.decode_buffer(frame)
            if results is not None:
                frame_cp = frame.copy()
                for result in results:
                    points = result.localization_result.localization_points
                    cv2.line(frame_cp, points[0], points[1], (0, 255, 0), 2)
                    cv2.line(frame_cp, points[1], points[2], (0, 255, 0), 2)
                    cv2.line(frame_cp, points[2], points[3], (0, 255, 0), 2)
                    cv2.line(frame_cp, points[3], points[0], (0, 255, 0), 2)
                    cv2.putText(frame_cp, result.barcode_text, points[0], cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255))

                if len(self.panorama) == 0:
                    self.panorama.append((frame, results, frame_cp))
                else:
                    preFrame = self.panorama[0][0]
                    preResults = self.panorama[0][1]
                    preFrameCp = self.panorama[0][2]

                    while len(results) > 0:
                        result = results.pop()
                        for preResult in preResults:
                            if preResult.barcode_text == result.barcode_text and preResult.barcode_format == result.barcode_format:
                                prePoints = preResult.localization_result.localization_points
                                points = result.localization_result.localization_points

                                preFrame = preFrame[0: preFrame.shape[0], 0: max(prePoints[0][0], prePoints[1][0], prePoints[2][0], prePoints[3][0]) + 10]
                                frame = frame[0: frame.shape[0], max(points[0][0], points[1][0], points[2][0], points[3][0]): frame.shape[1] + 10]

                                preFrameCp = preFrameCp[0: preFrameCp.shape[0], 0: max(prePoints[0][0], prePoints[1][0], prePoints[2][0], prePoints[3][0]) + 10]
                                frame_cp = frame_cp[0: frame_cp.shape[0], max(points[0][0], points[1][0], points[2][0], points[3][0]): frame_cp.shape[1] + 10]

                                frame = concat_images([preFrame, frame])
                                frame_cp = concat_images([preFrameCp, frame_cp])

                                results = self.reader.decode_buffer(frame)

                                self.panorama = [(frame, results, frame_cp)]
                                return frame, frame_cp

                return self.panorama[0][0], self.panorama[0][2]
                    
        except BarcodeReaderError as e:
            print(e)
            return None, None

        return None, None


    def process_frame(self, frame):
        results = None
        try:
            results = self.reader.decode_buffer(frame)
        except BarcodeReaderError as bre:
            print(bre)
        
        return results

    def clean_deque(self, tasks):
        while len(tasks) > 0:
            tasks.popleft()

    def close_window(self, window_name):
        try:
            cv2.destroyWindow(window_name)
        except:
            pass

    def run(self):
        import sys
        try:
            fn = sys.argv[1]
        except:
            fn = 0
        cap = cv2.VideoCapture(fn)

        threadn = 1
        barcodePool = ThreadPool(processes=threadn)
        panoramaPool = ThreadPool(processes=threadn)
        cameraTasks = deque()
        panoramaTask = deque()
        mode = self.MODE_CAMERA_ONLY
        image = None
        imageCp = None
        panoramaImage = None
        panoramaImageCp = None

        while True:
            ret, frame = cap.read()
            frame_cp = frame.copy()
            cv2putText(frame, 'A: auto pano, M: manual pano, C: capture, O: camera, S: stop', (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255))
            cv2.putText(frame, 'Barcode & QR Code Scanning ...', (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0))

            while len(cameraTasks) > 0 and cameraTasks[0].ready():
                results = cameraTasks.popleft().get()
                if results is not None:
                    for result in results:
                        points = result.localization_result.localization_points
                        cv2.line(frame, points[0], points[1], (0, 255, 0), 2)
                        cv2.line(frame, points[1], points[2], (0, 255, 0), 2)
                        cv2.line(frame, points[2], points[3], (0, 255, 0), 2)
                        cv2.line(frame, points[3], points[0], (0, 255, 0), 2)
                        cv2.putText(frame, result.barcode_text, points[0], cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255))
                
            if len(cameraTasks) < threadn:
                task = barcodePool.apply_async(self.process_frame, (frame_cp,))
                cameraTasks.append(task)

            if mode == self.MODE_MANUAL_STITCH:
                cv2.putText(frame, 'Manual Panorama ...', (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0))
            elif mode == self.MODE_AUTO_STITCH:
                cv2.putText(frame, 'Auto Panorama ...', (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0))
                if not self.isPanoramaDone and len(panoramaTask) < threadn:
                    task = panoramaPool.apply_async(self.stitch_frame, (frame_cp,))
                    panoramaTask.append(task)

            if mode == self.MODE_MANUAL_STITCH or mode == self.MODE_AUTO_STITCH:
                while len(panoramaTask) > 0 and panoramaTask[0].ready():
                    image, imageCp = panoramaTask.popleft().get()
                    if image is not None:
                        panoramaImage = image.copy()
                        panoramaImageCp = imageCp.copy()
                        cv2.imshow('panorama', panoramaImageCp)
            
            ch = cv2.waitKey(1)
            if ch == ord('q'):
                break
            elif ch == ord('o'):
                mode = self.MODE_CAMERA_ONLY
                self.isPanoramaDone = False
                self.close_window('panorama')
            elif ch == ord('a'):
                mode = self.MODE_AUTO_STITCH
                self.isPanoramaDone = False
                self.close_window('panorama')
            elif ch == ord('m'):
                mode = self.MODE_MANUAL_STITCH
                self.isPanoramaDone = False
                self.close_window('panorama')
            elif ch == ord('c'):
                self.isPanoramaDone = True
                if mode == self.MODE_MANUAL_STITCH or mode == self.MODE_AUTO_STITCH:
                    self.save_frame(panoramaImage)
            elif ch == ord('s'):
                self.isPanoramaDone = False
                self.close_window('panorama')

            cv2.imshow('camera', frame)

        cap.release()
        cv2.destroyAllWindows()

# ========================================================================
# Modificar la función de escaneo de QR para usar Dynamsoft Barcode Reader
def scan_qr():
    global qr_last_seen, qr_last_time, qr_timer_started, qr_hold_time
    cap = cv2.VideoCapture(0)  # Abre la cámara local
    # cap = cv2.VideoCapture("rtsp://admin:Cotn2024@192.168.10.108:554/Streaming/Channels/801")  # Abre la cámara remota 2
    
    scan_manager = ScanManager()  # Instanciar el gestor de escaneo

    if not cap.isOpened():
        print("Error: No se puede abrir la cámara.")
        return

    qr_accumulated_time = 0
    threshold_5_seconds = False
    threshold_20_seconds = False

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error al capturar la imagen")
            break

        frame = cv2.resize(frame, (640, 480))

        # Usar el método de frame_overlay de ScanManager para detectar y dibujar el QR
        frame_with_qr = scan_manager.frame_overlay(frame)

        # Decodificar el QR y verificar si es el mismo que el anterior
        if frame_with_qr is not None:
            # Obtener el primer QR detectado en el frame
            qr_value = scan_manager.reader.decode_buffer(frame)[0].barcode_text if scan_manager.count_barcodes(frame) > 0 else ""

            if qr_value:
                print(f"QR Decoded: {qr_value}")  # Imprimir el valor del QR escaneado
                if qr_value == qr_last_seen:
                    if not qr_timer_started:
                        qr_last_time = time.time()
                        qr_timer_started = True
                    else:
                        qr_accumulated_time += time.time() - qr_last_time
                        qr_last_time = time.time()

                        if qr_accumulated_time >= 5 and not threshold_5_seconds:
                            print(f"QR detectado y estable por {qr_hold_time} segundos. Habilitando botón de destrucción.")
                            app_instance.enable_destruction_button()
                            threshold_5_seconds = True

                        if qr_accumulated_time >= 20 and not threshold_20_seconds:
                            print(f"QR detectado durante 20 segundos. Marcando chaleco como destruido.")
                            update_chaleco_status(qr_value, 1)
                            threshold_20_seconds = True
                else:
                    qr_last_seen = qr_value
                    qr_timer_started = False
                    qr_accumulated_time = 0
                    threshold_5_seconds = False
                    threshold_20_seconds = False

                if is_qr_in_database(qr_value):
                    cv2.putText(frame_with_qr, f"QR: {qr_value}", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                else:
                    cv2.putText(frame_with_qr, "QR no existe", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

            else:
                print("No QR detected")
                qr_last_seen = ""
                qr_timer_started = False
                qr_accumulated_time = 0
                cv2.putText(frame_with_qr, "No QR detected", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

            cv2.imshow('QR Scanner', frame_with_qr)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


# Función para verificar si el QR existe en la base de datos
def is_qr_in_database(qr_value):
    conn = sqlite3.connect('chalecos.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM chalecos_receptora WHERE id = ?", (qr_value.strip(),)) 
    data = cursor.fetchone()
    conn.close()
    return data is not None

# Función para actualizar el estado del chaleco en la base de datos
def update_chaleco_status(qr_value, destruido):
    conn = sqlite3.connect('chalecos.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE chalecos_receptora SET destruido = ? WHERE id = ?", (destruido, qr_value))
    conn.commit()
    conn.close()
    print(f"Chaleco con QR {qr_value} actualizado a destruido={destruido}")

# Modificar la clase ChalecoApp para incluir el botón de escanear QR
class ChalecoApp(App):
    def enable_destruction_button(self):
        self.destruction_button.disabled = False

    def build(self):
        layout = BoxLayout(orientation='vertical')
        
        # Botón para destruir chaleco
        self.destruction_button = Button(text='Destruir Chaleco', disabled=True, on_press=self.on_destruction_button)
        layout.add_widget(self.destruction_button)

        # Botón para escanear QR
        scan_qr_button = Button(text="Escanear QR", on_press=self.on_scan_qr)
        layout.add_widget(scan_qr_button)

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
            update_chaleco_status(qr_last_seen, 1)
            self.update_chaleco_list()  # Actualizar la lista tras la destrucción

    def on_scan_qr(self, instance):
        scan_thread = threading.Thread(target=scan_qr)
        scan_thread.start()

    def on_start_server(self, instance):
        global scan_thread
        scan_thread = threading.Thread(target=start_server)
        scan_thread.start()

    def on_stop_server(self, instance):
        stop_server()

    def on_generate_report(self, instance):
        generate_pdf_report()
    @staticmethod
    def create_table_if_not_exists():
        try:
            conn = sqlite3.connect('chalecos.db')
            cursor = conn.cursor()

            # Crear la tabla si no existe
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS chalecos_receptora (
                    id INTEGER,
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
                    fecha_entrada TEXT,
                    destruido INTEGER DEFAULT 0
                )
            ''')

            conn.commit()
        except sqlite3.Error as e:
            print(f"Error al crear la tabla: {e}")
        finally:
            conn.close()

    def update_chaleco_list(self, *args):
        self.chaleco_list.clear_widgets()

        # Verificar y crear la tabla si es necesario
        self.create_table_if_not_exists()

        chalecos = []
        try:
            conn = sqlite3.connect('chalecos.db')
            cursor = conn.cursor()
            cursor.execute("SELECT id, numero_serie, fecha_entrada FROM chalecos_receptora WHERE destruido = 0")
            chalecos = cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Error al acceder a la base de datos: {e}")
        finally:
            conn.close()

        if chalecos:
            for chaleco in chalecos:
                numero_serie = chaleco[0]
                destruido = chaleco[1]
                chaleco_label = Label(text=f"ID:{id} - Chaleco: {numero_serie} - Destruido: {'No' if destruido == 0 else 'Sí'}")
                self.chaleco_list.add_widget(chaleco_label)
        else:
            empty_label = Label(text="No hay chalecos disponibles.")
            self.chaleco_list.add_widget(empty_label)

# Función para decodificar Base64 a binario (para imágenes)
def convert_base64_to_image(base64_string):
    try:
        # Intentar decodificar la cadena Base64
        return base64.b64decode(base64_string)
    except Exception as e:
        print(f"Error al decodificar la imagen QR: {str(e)}")
        return None

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
        (id, lote, numero_serie, fabricante, fecha_fabricacion, fecha_vencimiento, 
         tipo_modelo, peso, talla, procedencia, qr_image, fecha_entrada, destruido)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,?)''', 
        (
            chaleco.get('Id', ''), 
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
            fecha_entrada, 
            0
        )
    )
    
    conn.commit()
    conn.close()
    print("Datos insertados correctamente en la base de datos.")
def start_server():
    global server_running
    host = '0.0.0.0'
    port = 8000

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(20)

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
                # Enviar confirmación "OK" para marcarlo como transmitido
                client_socket.sendall("OK".encode('utf-8'))
            else:
                print("Error: formato de datos incorrecto, 'data' debe ser una lista de chalecos")
                client_socket.sendall("Formato de datos incorrecto".encode('utf-8'))

        except json.JSONDecodeError as e:
            print(f"Error al decodificar JSON: {e}")
            print("Datos que causaron el error:", data.decode('utf-8'))
            client_socket.sendall("Error al decodificar JSON".encode('utf-8'))

        client_socket.close()

    server_socket.close()
    print("Servidor detenido.")

# Función para detener el servidor
def stop_server():
    global server_running
    server_running = False

def generate_pdf_report():
    print("Informe PDF generado")

# Instanciar la aplicación
app_instance = ChalecoApp()

if __name__ == "__main__":
    app_instance.run()

