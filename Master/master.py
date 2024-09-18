"""
Servidor  17/08/24 -> Primer test


"""
import socket

# Definir la IP y el puerto del servidor
HOST = '0.0.0.0'  # Escuchar en todas las interfaces de red
PORT = 12345  # Puedes elegir otro puerto si es necesario

# Crear un socket TCP/IP
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Enlazar el socket a la dirección y el puerto
server_socket.bind((HOST, PORT))

# Escuchar conexiones entrantes
server_socket.listen(1)
print(f"Servidor escuchando en el puerto {PORT}...")

# Esperar una conexión
conn, addr = server_socket.accept()
print(f"Conectado por {addr}")

# Recibir datos
with conn:
    while True:
        data = conn.recv(1024)
        if not data:
            break
        print(f"Datos recibidos: {data.decode()}")

# Cerrar la conexión
server_socket.close()
