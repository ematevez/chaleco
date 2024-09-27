import cv2
import sqlite3
import time
import threading
from kivy.app import App
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock

# Variables globales para el seguimiento de QR
qr_last_seen = ""
qr_last_time = 0
qr_timer_started = False
qr_hold_time = 5  # Tiempo requerido para habilitar la destrucción
scan_thread = None

# Función para escanear QR y medir el tiempo de visibilidad
def scan_qr():
    global qr_last_seen, qr_last_time, qr_timer_started, qr_hold_time
    cap = cv2.VideoCapture(0)  # Abre la cámara
    qr_detector = cv2.QRCodeDetector()

    if not cap.isOpened():
        print("Error: No se puede abrir la cámara.")
        return

    # Variables de tiempo acumulado
    qr_accumulated_time = 0
    threshold_5_seconds = False  # Indica si ha alcanzado los 5 segundos
    threshold_20_seconds = False  # Indica si ha alcanzado los 20 segundos

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error al capturar la imagen")
            break
        
        # Redimensionar la imagen para mejorar el rendimiento
        frame = cv2.resize(frame, (640, 480))

        # Aplicar suavizado (blur) para reducir el ruido en la detección
        
        blurred_frame = cv2.GaussianBlur(frame, (5, 5), 0)
        
        # Detectar y decodificar el QR
        qr_value, pts, _ = qr_detector.detectAndDecode(blurred_frame)

        if qr_value:
            if qr_value == qr_last_seen:
                if not qr_timer_started:
                    qr_last_time = time.time()
                    qr_timer_started = True
                else:
                    # Actualizar el tiempo acumulado
                    qr_accumulated_time += time.time() - qr_last_time
                    qr_last_time = time.time()

                    # Verificar si se ha mantenido el QR visible durante al menos 5 segundos
                    if qr_accumulated_time >= 5 and not threshold_5_seconds:
                        print(f"QR detectado y estable por {qr_hold_time} segundos. Habilitando botón de destrucción.")
                        app_instance.enable_destruction_button()
                        threshold_5_seconds = True  # Marcar que ya se alcanzaron los 5 segundos

                    # Verificar si se ha mantenido visible durante 20 segundos
                    if qr_accumulated_time >= 20 and not threshold_20_seconds:
                        print(f"QR detectado durante 20 segundos. Marcando chaleco como destruido.")
                        update_chaleco_status(qr_value, 1)  # Actualizar el chaleco como destruido
                        threshold_20_seconds = True

            else:
                # Restablecer si el QR cambia
                qr_last_seen = qr_value
                qr_timer_started = False
                qr_accumulated_time = 0  # Reiniciar el tiempo acumulado
                threshold_5_seconds = False
                threshold_20_seconds = False

            # Dibujar un recuadro verde si es válido, rojo si no existe en la base de datos
            if is_qr_in_database(qr_value):
                cv2.putText(frame, f"QR: {qr_value}", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                color = (0, 255, 0)
            else:
                cv2.putText(frame, "QR no existe", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                color = (0, 0, 255)

            # Dibujar el recuadro alrededor del QR
            if pts is not None and len(pts) == 4:
                pts = pts.astype(int)
                for i in range(4):
                    pt1 = tuple(pts[i][0])
                    pt2 = tuple(pts[(i + 1) % 4][0])
                    cv2.line(frame, pt1, pt2, color, 2)

            # Mostrar el tiempo acumulado en la pantalla
            cv2.putText(frame, f"Tiempo: {qr_accumulated_time:.1f}s", (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)

        else:
            qr_last_seen = ""
            qr_timer_started = False
            qr_accumulated_time = 0  # Reiniciar tiempo si no se detecta ningún QR
            cv2.putText(frame, "No QR detected", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        cv2.imshow('QR Scanner', frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

# Función para verificar si el QR existe en la base de datos
def is_qr_in_database(qr_value):
    conn = sqlite3.connect('chalecos.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM chalecos_receptora WHERE numero_serie = ?", (qr_value,))
    data = cursor.fetchone()
    conn.close()
    return data is not None

# Función para actualizar el estado del chaleco en la base de datos
def update_chaleco_status(qr_value, destruido):
    conn = sqlite3.connect('chalecos.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE chalecos_receptora SET destruido = ? WHERE numero_serie = ?", (destruido, qr_value))
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

    def update_chaleco_list(self, *args):
        self.chaleco_list.clear_widgets()
        conn = sqlite3.connect('chalecos.db')
        cursor = conn.cursor()
        cursor.execute("SELECT numero_serie, destruido FROM chalecos_receptora WHERE destruido = 0")
        chalecos = cursor.fetchall()
        conn.close()

        for chaleco in chalecos:
            numero_serie = chaleco[0]
            destruido = chaleco[1]
            chaleco_label = Label(text=f"Chaleco: {numero_serie}, Destruido: {destruido}")
            self.chaleco_list.add_widget(chaleco_label)

# Funciones para manejar el servidor y PDF
def start_server():
    print("Servidor iniciado")

def stop_server():
    print("Servidor detenido")

def generate_pdf_report():
    print("Informe PDF generado")

# Instanciar la aplicación
app_instance = ChalecoApp()

if __name__ == "__main__":
    app_instance.run()
