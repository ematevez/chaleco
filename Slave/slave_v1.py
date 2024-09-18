import socket

def iniciar_servidor():
    HOST = '0.0.0.0'  # Escucha en todas las interfaces de red
    PORT = 12345  # Debe coincidir con el puerto en el cliente

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()  # Escuchar conexiones
        print(f"Servidor escuchando en el puerto {PORT}...")

        conn, addr = s.accept()  # Aceptar una conexión
        with conn:
            print(f"Conectado con {addr}")
            while True:
                data = conn.recv(1024)  # Tamaño del buffer de recepción
                if not data:
                    break
                registro = data.decode()  # Decodificar los datos recibidos
                print(f"Registro recibido: {registro.strip()}")

                # Guardar los registros en un archivo
                with open("registros_recibidos.txt", "a") as file:
                    file.write(registro)
            print("Conexión cerrada")

# Ejecutar el servidor
if __name__ == "__main__":
    iniciar_servidor()


"""    
quiro hacer un codigo en python para pasar desde una pc a otra informacion por medio de un boton de bluetooth, estos datos van a estar guardados en un base de datos de sqlite, siempre y cuando no esten tildado como archivo no pasado, el programa cliiente debe mostrar la certesa de la recepcion de los datos
"""