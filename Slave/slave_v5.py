import socket
import json
import sqlite3
from datetime import datetime

# Función para crear la tabla si no existe
def create_table():
    conn = sqlite3.connect('chalecos.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS chalecos_receptora (
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
                        qr_image BLOB,
                        fecha_recepcion TEXT)''')
    conn.commit()
    conn.close()

# Función para insertar datos en la base de datos
def insert_data(chaleco_data):
    conn = sqlite3.connect('chalecos.db')
    cursor = conn.cursor()

    # Obtener la fecha de recepción actual
    fecha_recepcion = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for chaleco in chaleco_data['data']:
        # Imprimir cada campo recibido para depurar
        print(f"Lote: {chaleco.get('lote', '')}")
        print(f"Número de Serie: {chaleco.get('numero_serie', '')}")
        print(f"Fabricante: {chaleco.get('fabricante', '')}")
        print(f"Fecha de Fabricación: {chaleco.get('fecha_fabricacion', '')}")
        print(f"Fecha de Vencimiento: {chaleco.get('fecha_vencimiento', '')}")
        print(f"Tipo Modelo: {chaleco.get('tipo_modelo', '')}")
        print(f"Peso: {chaleco.get('peso', '')}")
        print(f"Talla: {chaleco.get('talla', '')}")
        print(f"Procedencia: {chaleco.get('procedencia', '')}")
        print(f"QR Image: {chaleco.get('qr_image', None)}")  # En caso de que no haya imagen

        # Insertar datos en la base de datos
        cursor.execute('''INSERT INTO chalecos_receptora 
            (lote, numero_serie, fabricante, fecha_fabricacion, fecha_vencimiento, 
             tipo_modelo, peso, talla, procedencia, qr_image, fecha_recepcion)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
            (
                chaleco.get('lote', ''), 
                chaleco.get('numero_serie', ''), 
                chaleco.get('fabricante', ''), 
                chaleco.get('fecha_fabricacion', ''), 
                chaleco.get('fecha_vencimiento', ''), 
                chaleco.get('tipo_modelo', ''), 
                chaleco.get('peso', ''), 
                chaleco.get('talla', ''), 
                chaleco.get('procedencia', ''), 
                chaleco.get('qr_image', None),  # Asume que es un blob
                fecha_recepcion
            )
        )

    conn.commit()
    conn.close()
    print("Datos insertados correctamente en la base de datos.")

# Función principal del servidor
def start_server():
    host = '0.0.0.0'  # Escucha en todas las interfaces de red
    port = 8000       # Puerto del servidor

    # Crear la tabla en la base de datos si no existe
    create_table()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((host, port))
        server_socket.listen()
        print(f'Servidor escuchando en {host}:{port}...')

        while True:
            client_socket, address = server_socket.accept()
            with client_socket:
                print(f'Conexión recibida de {address}')
                
                # Recibir datos del cliente
                data = client_socket.recv(1024)

                if data:
                    # Mostrar los datos en bruto (sin procesar)
                    print(f"Datos recibidos en bruto (sin procesar): {data}")

                    try:
                        # Intentar decodificar los datos como JSON
                        chaleco_data = json.loads(data.decode('utf-8'))
                        print(f"Datos JSON decodificados correctamente: {chaleco_data}")

                        # Insertar datos en la base de datos
                        insert_data(chaleco_data)

                    except json.JSONDecodeError as e:
                        print(f"Error al decodificar JSON: {e}")
                    except Exception as e:
                        print(f"Error general: {e}")

# Iniciar el servidor
if __name__ == "__main__":
    start_server()
