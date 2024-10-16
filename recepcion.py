import socket
import json
import base64
import sqlite3
from datetime import datetime
from cryptography.fernet import Fernet

# Cargar la clave de cifrado
with open("clave.key", "rb") as clave_file:
    key = clave_file.read()

cipher_suite = Fernet(key)

def convert_base64_to_image(base64_string):
    try:
        return base64.b64decode(base64_string)
    except Exception as e:
        print(f"Error al decodificar la imagen QR: {str(e)}")
        return None

def insert_data(chaleco):
    conn = sqlite3.connect('chalecos.db')
    cursor = conn.cursor()
    
    fecha_entrada = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    qr_image_base64 = chaleco.get('QR Image', None)
    qr_image_blob = convert_base64_to_image(qr_image_base64) if qr_image_base64 else None

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
    conn.close()
    print("Datos insertados correctamente en la base de datos.")

def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('0.0.0.0', 8000))
    server_socket.listen(20)

    print("Servidor escuchando...")

    while True:
        client_socket, addr = server_socket.accept()
        print(f"Conexión aceptada de {addr}")
        data = b""
        
        while True:
            packet = client_socket.recv(1024)
            if not packet:
                break
            data += packet

        try:
            datos_descifrados = cipher_suite.decrypt(data)
            chaleco_data = json.loads(datos_descifrados.decode('utf-8'))

            if isinstance(chaleco_data['data'], list):
                for chaleco in chaleco_data['data']:
                    insert_data(chaleco)

                client_socket.sendall("OK".encode('utf-8'))
                print("Datos recibidos y procesados correctamente.")
            else:
                client_socket.sendall("Formato de datos incorrecto".encode('utf-8'))
                print("Formato de datos incorrecto recibido.")

        except Exception as e:
            print(f"Error: {e}")
            client_socket.sendall("Error al procesar los datos".encode('utf-8'))
        finally:
            client_socket.close()

if __name__ == "__main__":
    start_server()
