"""
02/10/2024 
!!!TODO
Licencia hasta 03/11/2024 -> -20111 error
Verificar filtro ID

Ver camara 1 sacarfoto y guardar con numero id+numerolote+inicio o id+numeroserie+inicio (en la foto guardar qr fehca y hora)

ver camara 2 para finalizar proceso sacar foto grardar id+numerolote+fin o id+numeroserie+fin (en la foto guardar qr fehca y hora)

Parar el servidor cuando reciba los datos.
"""

from __future__ import print_function
import cv2
import socket
import json
import sqlite3
import base64
import time
import threading
import numpy as np
from datetime import datetime
from kivy.app import App
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.clock import Clock
from multiprocessing.pool import ThreadPool
from collections import deque
from dbr import *
from util import *

# Inicializar licencia de Dynamsoft Barcode Reader (DBR)
BarcodeReader.init_license(
    "DLS2eyJoYW5kc2hha2VDb2RlIjoiMTAzMjc1MDExLVRYbFFjbTlxIiwibWFpblNlcnZlclVSTCI6Imh0dHBzOi8vbWRscy5keW5hbXNvZnRvbmxpbmUuY29tIiwib3JnYW5pemF0aW9uSUQiOiIxMDMyNzUwMTEiLCJzdGFuZGJ5U2VydmVyVVJMIjoiaHR0cHM6Ly9zZGxzLmR5bmFtc29mdG9ubGluZS5jb20iLCJjaGVja0NvZGUiOjE2MTEzODUyMTd9")

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
            #Esto sirve para la captura pero no se ve en la pantalla
            cv2.putText(frame, 'A: auto pano, M: manual pano, C: capture, O: camera, S: stop', (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255))
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
# Función de escaneo de QR para usar Dynamsoft Barcode Reader
def scan_qr():
    global qr_last_seen, qr_last_time, qr_timer_started
    cap = cv2.VideoCapture(0)  # Abre la cámara local
    # cap = cv2.VideoCapture("rtsp://admin:Cotn2024@192.168.10.108:554/Streaming/Channels/801")  # Abre la cámara remota 2
    
    scan_manager = ScanManager()  # Instanciar el gestor de escaneo

    if not cap.isOpened():
        print("Error: No se puede abrir la cámara.")
        return

    qr_accumulated_time = 0  # Tiempo acumulado para el QR detectado
    threshold_5_seconds = False  # Indica si ya se cumplió el tiempo de 5 segundos

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error al capturar la imagen")
            break

        frame = cv2.resize(frame, (640, 480))

        # Usar el método de frame_overlay de ScanManager para detectar y dibujar el QR
        frame_with_qr = scan_manager.frame_overlay(frame)

        # Decodificar el QR
        if frame_with_qr is not None:
            qr_value = scan_manager.reader.decode_buffer(frame)[0].barcode_text if scan_manager.count_barcodes(frame) > 0 else ""

            if qr_value:
                #print(f"QR Decoded: {qr_value}")  # Imprimir el valor del QR escaneado

                if qr_value == qr_last_seen:
                    if not qr_timer_started:
                        # Inicia el temporizador cuando el QR se ve por primera vez
                        qr_last_time = time.time()
                        qr_timer_started = True
                    else:
                        # Calcular el tiempo acumulado en que el mismo QR ha estado visible
                        qr_accumulated_time += time.time() - qr_last_time
                        qr_last_time = time.time()

                        if qr_accumulated_time >= 5 and not threshold_5_seconds:
                            print("QR detectado y estable por 5 segundos. Habilitando botón de destrucción.")
                            if is_qr_in_database(qr_value):
                                app_instance.enable_destruction_button()
                                threshold_5_seconds = True
                            else:
                                print("QR no válido, no se habilitará la destrucción.")
                                threshold_5_seconds = False
                else:
                    # Si el QR cambia, restablecer los valores
                    qr_last_seen = qr_value
                    qr_timer_started = False
                    qr_accumulated_time = 0
                    threshold_5_seconds = False

                if is_qr_in_database(qr_value):
                    cv2.putText(frame_with_qr, f"QR: {qr_value}", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                else:
                    cv2.putText(frame_with_qr, "QR no existe", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

            else:
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
    # Extrae partes relevantes del QR si es necesario
    qr_parts = qr_value.split(", ")
    qr_id = qr_parts[0].split(": ")[1]
    qr_lote = qr_parts[1].split(": ")[1]
    qr_serie = qr_parts[2].split(": ")[1]

    conn = sqlite3.connect('chalecos.db')
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM chalecos_receptora WHERE id = ? AND lote = ? AND numero_serie = ?", (qr_id, qr_lote, qr_serie))
        data = cursor.fetchone()
        return data is not None
    except sqlite3.Error as e:
        print(f"Error al acceder a la base de datos: {e}")
        return False
    finally:
        conn.close()
        
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
        self.scan_qr_button = Button(text="Escanear QR", on_press=self.on_scan_qr)
        layout.add_widget(self.scan_qr_button)

        # Botón para iniciar el servidor
        # Guardamos el botón como un atributo de la clase para poder acceder después
        self.start_server_button = Button(text="Iniciar servidor", background_color=(1, 0, 0, 1))
        self.start_server_button.bind(on_press=self.on_start_server)
        layout.add_widget(self.start_server_button)
        
        # Botón para detener el servidor
        self.stop_server_button = Button(text="Detener servidor", on_press=self.on_stop_server, background_color=(1, 0, 0, 1))
        layout.add_widget(self.stop_server_button)

        # Botón para generar el informe PDF
        self.generate_report_button = Button(text="Generar informe PDF", on_press=self.on_generate_report)
        layout.add_widget(self.generate_report_button)

        # Sección para mostrar chalecos no destruidos
        self.chaleco_list = GridLayout(cols=1, spacing=10, size_hint_y=None)
        self.chaleco_list.bind(minimum_height=self.chaleco_list.setter('height'))
        
        scroll = ScrollView(size_hint=(1, 1))
        scroll.add_widget(self.chaleco_list)
        layout.add_widget(scroll)

        # Actualizar la lista de chalecos no destruidos cada 5 segundos
        Clock.schedule_interval(self.update_chaleco_list, 5)

        return layout

    def on_scan_qr(self, instance):
        # Deshabilitar el botón de escaneo mientras se ejecuta el escaneo
        self.scan_qr_button.disabled = True

        def scan_and_reenable():
            scan_qr()  # Ejecutar la función de escaneo
            # Habilitar el botón de nuevo cuando termine el escaneo
            self.scan_qr_button.disabled = False

        # Crear un hilo para no bloquear la interfaz mientras escanea
        scan_thread = threading.Thread(target=scan_and_reenable)
        scan_thread.start()
    
    # Función para mostrar el popup desde el hilo principal
    def show_popup(self, message, title="Información"):
        popup = Popup(
            title=title,
            content=Label(text=message),
            size_hint=(0.6, 0.4)
        )
        popup.open()
        return popup  # Agrega esta línea para retornar el objeto popup

        
    def obtener_imagen_qr(self, qr_value):
        conn = sqlite3.connect('chalecos.db')
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT qr_image FROM chalecos_receptora WHERE id = ?", (qr_value,))
            result = cursor.fetchone()
            if result:
                return result[0]
        except sqlite3.Error as e:
            print(f"Error al obtener imagen QR: {e}")
        finally:
            conn.close()
        return None
        
        
    def marcar_como_destruido(self, qr_value):
        conn = sqlite3.connect('chalecos.db')
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE chalecos_receptora SET destruido = 1 WHERE id = ?", (qr_value,))
            conn.commit()
            print(f"Chaleco con QR {qr_value} marcado como destruido.")
        except sqlite3.Error as e:
            print(f"Error al actualizar la base de datos: {e}")
        finally:
            conn.close()

    def capturar_imagen_con_destruccion(self, nombre_archivo, chaleco_data):
        id, lote, numero_serie = chaleco_data
        cam = cv2.VideoCapture(0)  # Abre la cámara de nuevo si es necesario

        if not cam.isOpened():
            print("Error: No se puede abrir la cámara.")
            return

        ret, frame = cam.read()
        if not ret:
            print("Error al capturar la imagen.")
            cam.release()
            return

        # Redimensionar la imagen
        frame = cv2.resize(frame, (800, 600))

        # Agregar texto de identificación y fecha/hora actual, junto con "DESTRUIDO"
        texto = f"ID: {id}, Lote: {lote}, Serie: {numero_serie}, Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}, DESTRUIDO"
        cv2.putText(frame, texto, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        # Guardar la imagen en un archivo .png
        cv2.imwrite(nombre_archivo, frame)
        print(f"Captura guardada como: {nombre_archivo}")

        # Cerrar la cámara
        cam.release()
        cv2.destroyAllWindows()


    def actualizar_estado_destruccion(self, qr_value):
        conn = sqlite3.connect('chalecos.db')
        cursor = conn.cursor()
        try:
            # Incrementar el campo 'destruido' en la base de datos
            cursor.execute("UPDATE chalecos_receptora SET destruido = destruido + 1 WHERE id = ?", (qr_value,))
            conn.commit()
            print(f"El chaleco con QR {qr_value} ha sido actualizado como destruido.")
        except sqlite3.Error as e:
            print(f"Error al actualizar el estado de destrucción: {e}")
        finally:
            conn.close()

    
    #!===========================CHANGE IP NAMES===========================================================
    def verificar_destruccion(self, qr_value):
        # Abre la segunda cámara (cambiar a cámara IP2 si es necesario)
        # cam = cv2.VideoCapture("rtsp://usuario:contraseña@192.168.1.2:554/Streaming/Channels/2")  # Cambiar a la URL de la cámara IP2
        cam = cv2.VideoCapture(0)
        lector_qr = BarcodeReader()

        if not cam.isOpened():
            print("Error: No se puede abrir la cámara IP2.")
            return

        # Intentamos leer el primer frame
        ret, frame = cam.read()
        if not ret:
            print("Error al capturar la imagen en la cámara IP2.")
            cam.release()
            return

        # Procesamos el frame para verificar el QR
        results = lector_qr.decode_buffer(frame)
        if results and results[0].barcode_text == qr_value:
            print("QR detectado en la cámara IP2. Procediendo a la destrucción.")

            # Capturamos la primera imagen
            chaleco_data = self.obtener_datos_chaleco(qr_value)
            if chaleco_data:
                nombre_archivo_inicial = f"{chaleco_data[0]}_{chaleco_data[1]}_{chaleco_data[2]}_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
                self.capturar_imagen(nombre_archivo_inicial, chaleco_data)

                # Esperar 10 segundos y leer nuevamente el QR
                print("Esperando 10 segundos para verificar nuevamente el QR...")
                time.sleep(10)  # Esperar 10 segundos

                # Volver a intentar leer la cámara y el QR
                ret, frame = cam.read()
                if not ret:
                    print("Error al capturar la imagen después de 10 segundos.")
                    cam.release()
                    return

                # Procesamos nuevamente el frame para verificar el QR
                results = lector_qr.decode_buffer(frame)
                if results and results[0].barcode_text == qr_value:
                    print("QR detectado nuevamente después de 10 segundos. Marcando como destruido.")

                    # Capturar la segunda imagen con la palabra "DESTRUIDO"
                    nombre_archivo_final = f"IMG/{chaleco_data[0]}_{chaleco_data[1]}_{chaleco_data[2]}_DESTRUIDO_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
                    self.capturar_imagen_con_destruccion(nombre_archivo_final, chaleco_data)

                    # Actualizar el estado del chaleco en la base de datos
                    self.actualizar_estado_destruccion(qr_value)

        # Cerrar la cámara después de la captura y el procesamiento
        cam.release()
        cv2.destroyAllWindows()

    
    def capturar_imagen(self, nombre_archivo, chaleco_data):
        id, lote, numero_serie = chaleco_data
        cam = cv2.VideoCapture(0)  # Abre la cámara

        if not cam.isOpened():
            print("Error: No se puede abrir la cámara.")
            return

        ret, frame = cam.read()
        if not ret:
            print("Error al capturar la imagen.")
            cam.release()
            return

        # Redimensionar la imagen a un tamaño adecuado
        frame = cv2.resize(frame, (800, 600))

        # Agregar texto de identificación y fecha/hora actual a la imagen
        texto = f"ID: {id}, Lote: {lote}, Serie: {numero_serie}, Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        cv2.putText(frame, texto, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        # Guardar la imagen en un archivo .png
        cv2.imwrite(nombre_archivo, frame)
        print(f"Captura guardada como: {nombre_archivo}")

        # Cerrar la cámara
        cam.release()
        cv2.destroyAllWindows()

    
    
    def obtener_datos_chaleco(self, qr_value):
        # Extraer las partes del QR
        try:
            qr_parts = qr_value.split(", ")
            qr_id = qr_parts[0].split(": ")[1]
            qr_lote = qr_parts[1].split(": ")[1]
            qr_serie = qr_parts[2].split(": ")[1]
        except IndexError:
            print("Error al extraer las partes del QR")
            return None

        conn = sqlite3.connect('chalecos.db')
        cursor = conn.cursor()
        try:
            print(f"Buscando chaleco con ID: {qr_id}, Lote: {qr_lote}, Serie: {qr_serie}")
            # Buscar el chaleco en la base de datos usando los valores extraídos
            cursor.execute(
                "SELECT id, lote, numero_serie FROM chalecos_receptora WHERE id = ? AND lote = ? AND numero_serie = ?",
                (qr_id, qr_lote, qr_serie)
            )
            data = cursor.fetchone()

            if data:
                print(f"Chaleco encontrado: {data}")
            else:
                print("Chaleco no encontrado en la base de datos")

            return data
        except sqlite3.Error as e:
            print(f"Error al acceder a la base de datos: {e}")
            return None
        finally:
            conn.close()


    def on_destruction_button(self, instance):
        global qr_last_seen
        print("Destrucción en proceso...")
        print(f"QR último visto: {qr_last_seen}")
        
        popup = self.show_popup("Comenzando destrucción del chaleco...")
        self.destruction_button.disabled = True
        
        chaleco_data = self.obtener_datos_chaleco(qr_last_seen)
        print(f"Datos del chaleco: {chaleco_data}")
        
        if chaleco_data:
            id, lote, numero_serie = chaleco_data
            nombre_archivo = f"{id}_{lote}_{numero_serie}_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
            
            # Capturar imagen de la cámara y guardarla
            self.capturar_imagen(nombre_archivo, chaleco_data)

            # Iniciar el proceso de destrucción en un hilo separado
            destruccion_thread = threading.Thread(target=self.verificar_destruccion, args=(qr_last_seen,))
            destruccion_thread.start()

        if popup:
            popup.dismiss()


            
    def scan_qr():
        global qr_last_seen, qr_last_time, qr_timer_started
        cap = cv2.VideoCapture(0)  # Abre la cámara local

        scan_manager = ScanManager()  # Instanciar el gestor de escaneo

        if not cap.isOpened():
            print("Error: No se puede abrir la cámara.")
            return

        qr_accumulated_time = 0  # Tiempo acumulado para el QR detectado
        threshold_5_seconds = False  # Indica si ya se cumplió el tiempo de 5 segundos

        while True:
            ret, frame = cap.read()
            if not ret:
                print("Error al capturar la imagen")
                break

            frame = cv2.resize(frame, (640, 480))
            frame_with_qr = scan_manager.frame_overlay(frame)  # Usar el método de frame_overlay

            if frame_with_qr is not None:
                qr_value = scan_manager.reader.decode_buffer(frame)[0].barcode_text if scan_manager.count_barcodes(frame) > 0 else ""

                if qr_value:
                    if qr_value == qr_last_seen:
                        if not qr_timer_started:
                            qr_last_time = time.time()
                            qr_timer_started = True
                        else:
                            qr_accumulated_time += time.time() - qr_last_time
                            qr_last_time = time.time()

                            if qr_accumulated_time >= 5 and not threshold_5_seconds:
                                print("QR detectado y estable por 5 segundos. Habilitando botón de destrucción.")
                                if is_qr_in_database(qr_value):
                                    app_instance.enable_destruction_button()
                                    threshold_5_seconds = True
                                else:
                                    print("QR no válido, no se habilitará la destrucción.")
                                    threshold_5_seconds = False
                    else:
                        qr_last_seen = qr_value
                        qr_timer_started = False
                        qr_accumulated_time = 0
                        threshold_5_seconds = False

                else:
                    qr_last_seen = ""
                    qr_timer_started = False
                    qr_accumulated_time = 0

                cv2.imshow('QR Scanner', frame_with_qr)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()  # Cerrar la ventana correctamente después de presionar 'q'



    def on_start_server(self, instance):
        global scan_thread, server_running
        # Reinicia la variable server_running
        server_running = True
        # Cambiamos el color del botón a verde cuando se presiona y lo deshabilitamos
        self.start_server_button.background_color = (0, 1, 0, 1)
        self.start_server_button.text = "Servidor en ejecución"
        self.start_server_button.disabled = True

        # Iniciamos el servidor en un hilo separado para no bloquear la interfaz
        scan_thread = threading.Thread(target=start_server, args=(self,))
        scan_thread.start()
        
    def on_stop_server(self, instance):
        global server_running
        server_running = False
        print("Deteniendo el servidor...")
        self.start_server_button.background_color = (1, 0, 0, 1)
        self.start_server_button.text = "Iniciar servidor"
        self.start_server_button.disabled = False
        self.show_popup("El servidor se ha detenido correctamente", "Servidor Detenido")

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
                    destruido INTEGER DEFAULT 0,
                    informe INTEGER DEFAULT 0
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
            # Mostrar los chalecos en un formato más visual
            for chaleco in chalecos:
                id, numero_serie, fecha_entrada = chaleco
                chaleco_label = Label(text=f"ID: {id} - Serie: {numero_serie} - Fecha Entrada: {fecha_entrada}", size_hint_y=None, height=40)
                self.chaleco_list.add_widget(chaleco_label)
        else:
            empty_label = Label(text="No hay chalecos disponibles.", size_hint_y=None, height=40)
            self.chaleco_list.add_widget(empty_label)

# Función para decodificar Base64 a binario (para imágenes)
def convert_base64_to_image(base64_string):
    # Añadir padding si es necesario
    while len(base64_string) % 4 != 0:
        base64_string += '='

    try:
        decoded_data = base64.b64decode(base64_string)
        return decoded_data
    except Exception as e:
        print(f"Error al decodificar la imagen QR: {e}")
        return None

# Función para insertar datos en la base de datos
def insert_data(chaleco):
    conn = sqlite3.connect('chalecos.db')
    cursor = conn.cursor()
    
    fecha_entrada = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    qr_image_base64 = chaleco.get('QR Image', None)  # Verifica que 'QR Image' tenga el nombre correcto en tu JSON

    informe = chaleco.get('Informe', '') 
    
    if qr_image_base64 and isinstance(qr_image_base64, str):
        qr_image_blob = convert_base64_to_image(qr_image_base64)
    else:
        qr_image_blob = None

    cursor.execute('''INSERT INTO chalecos_receptora 
        (id, lote, numero_serie, fabricante, fecha_fabricacion, fecha_vencimiento, 
        tipo_modelo, peso, talla, procedencia, qr_image, fecha_entrada, destruido)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
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
    print("Datos insertados correctamente en la base de datos.")
    conn.close()
    
    return True

def show_popup_data(message, title="Datos"):
        def create_popup(dt):
            popup = Popup(title=title,
                        content=Label(text=message),
                        size_hint=(0.6, 0.4))
            popup.open()
        # Usar Clock para que el popup se ejecute en el hilo principal
        Clock.schedule_once(create_popup)



def start_server(app_instance):
    global server_running
    host = '0.0.0.0'
    port = 8000

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(20)
    
    app_instance.start_server_button.background_color = (0, 1, 0, 1)  # Verde cuando el servidor está activo
    app_instance.start_server_button.disabled = True
    print(f"Servidor escuchando en {host}:{port}...")
    
    while server_running:
        try:
            server_socket.settimeout(1)  # Establece un tiempo de espera corto para la escucha
            client_socket, client_address = server_socket.accept()
            print(f"Conexión recibida de {client_address}")
            show_popup_data(f"Servidor escuchando en {host}:{port}...", title="Servidor Iniciado")


            # Mostrar un popup cuando se conecta un cliente
            show_popup_data(f"Cliente conectado desde {client_address[0]}", title="Cliente conectado")

            data = b""
            while True:
                packet = client_socket.recv(1024)
                if not packet:
                    break
                data += packet

            print(f"Datos recibidos: {data.decode('utf-8')}")

            # Intentamos decodificar el JSON
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
                client_socket.sendall("Error al decodificar JSON".encode('utf-8'))

        except socket.timeout:
            continue  # Continuar la espera si no se conecta ningún cliente
        
        except Exception as e:
            print(f"Error en la comunicación con el cliente: {str(e)}")

        finally:
            # Cierra client_socket solo si fue creado
            if 'client_socket' in locals():
                app_instance.start_server_button.background_color = (1, 0, 0, 1)
                app_instance.start_server_button.disabled = False
                # Mostrar un popup cuando se cierra el servidor
                client_socket.close()
    
    server_socket.close()
    print("Servidor detenido.")
    # Mostrar un popup cuando se cierra el servidor
    show_popup_data("Conexión finalizada. El servidor ha sido detenido.", title="Servidor detenido")
    
def generate_pdf_report():
    print("Informe PDF generado")

# Instanciar la aplicación
app_instance = ChalecoApp()

if __name__ == "__main__":
    app_instance.run()

