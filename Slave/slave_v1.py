

"""    
quiro hacer un codigo en python para pasar desde una pc a otra informacion por medio de un boton de bluetooth, estos datos van a estar guardados en un base de datos de sqlite, siempre y cuando no esten tildado como archivo no pasado, el programa cliiente debe mostrar la certesa de la recepcion de los datos
"""

import socket

# Configuración del servidor
HOST = '0.0.0.0'  # Aceptar conexiones en todas las interfaces de red
PORT = 12345  # El mismo puerto que se usa en la app Kivy

def recibir_registros():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()  # Escuchar conexiones entrantes
        print(f"Servidor escuchando en {HOST}:{PORT}...")

        while True:
            conn, addr = s.accept()
            with conn:
                print(f"Conexión desde {addr}")
                data = conn.recv(1024)  # Recibir datos (máximo 1024 bytes por vez)
                
                if data:
                    registros = data.decode()
                    print(f"Registros recibidos:\n{registros}")
                    
                    # Guardar registros en un archivo
                    with open("registros_recibidos.txt", "a") as file:
                        file.write(registros + "\n\n")

                    # Enviar una respuesta al cliente
                    conn.sendall(b"Registros recibidos correctamente.")

if __name__ == '__main__':
    recibir_registros()
