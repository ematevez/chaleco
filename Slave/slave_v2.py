import socket
import sqlite3
import datetime

# Configuración del servidor
HOST = '0.0.0.0'  # Aceptar conexiones en todas las interfaces de red
PORT = 8000  # El mismo puerto que se usa en la app Kivy

# Conexión a la base de datos SQLite
def conectar_db():
    conn = sqlite3.connect('registros_chalecos.db')
    cursor = conn.cursor()
    # Crear la tabla si no existe
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
            fecha_recibido TEXT
        )
    ''')
    conn.commit()
    return conn

def guardar_en_db(conn, registro):
    cursor = conn.cursor()

    # Asegurarse de que el registro esté en formato de tupla y tenga 10 valores
    if isinstance(registro, str):
        # Convertir la cadena de texto a tupla quitando paréntesis y comas
        registro = eval(registro)  # Evalúa la cadena y la convierte a tupla (asegúrate de que sea seguro)
    
    if len(registro) != 10:
        print("El registro no tiene 10 valores:", registro)
        return

    lote, numero_serie, fabricante, fecha_fabricacion, fecha_vencimiento, tipo_modelo, peso, talla, procedencia, transmitido = registro

    # Fecha de recibido (tomada del sistema)
    fecha_recibido = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Insertar los datos en la tabla
    cursor.execute('''
        INSERT INTO chalecos (lote, numero_serie, fabricante, fecha_fabricacion, fecha_vencimiento,
                              tipo_modelo, peso, talla, procedencia, fecha_recibido)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (lote, numero_serie, fabricante, fecha_fabricacion, fecha_vencimiento,
          tipo_modelo, peso, talla, procedencia, fecha_recibido))

    conn.commit()

def recibir_registros():
    conn = conectar_db()  # Conectar a la base de datos

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()  # Escuchar conexiones entrantes
        print(f"Servidor escuchando en {HOST}:{PORT}...")

        while True:
            cliente_conn, addr = s.accept()
            with cliente_conn:
                print(f"Conexión desde {addr}")
                data = cliente_conn.recv(1024)  # Recibir datos (máximo 1024 bytes por vez)

                if data:
                    registros = data.decode()
                    print(f"Registros recibidos:\n{registros}")


                    # Guardar los registros en la base de datos
                    for registro in registros.split("\n"):
                        if registro.strip():  # Evitar registros vacíos
                            guardar_en_db(conn, registro)

                    # Enviar una respuesta de confirmación al cliente
                    cliente_conn.sendall(b"Registros recibidos correctamente.")
                    
def recibir_registros():
    conn = conectar_db()  # Conectar a la base de datos

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()  # Escuchar conexiones entrantes
        print(f"Servidor escuchando en {HOST}:{PORT}...")

        while True:
            cliente_conn, addr = s.accept()
            with cliente_conn:
                print(f"Conexión desde {addr}")
                data = cliente_conn.recv(1024)  # Recibir datos (máximo 1024 bytes por vez)

                if data:
                    registros = data.decode()
                    print(f"Registros recibidos:\n{registros}")

                    # Guardar los registros en la base de datos
                    for registro in registros.split("\n"):
                        if registro.strip():  # Evitar registros vacíos
                            guardar_en_db(conn, registro)

                    # Enviar una respuesta de confirmación al cliente
                    cliente_conn.sendall(b"Registros recibidos correctamente.")

if __name__ == '__main__':
    recibir_registros()
