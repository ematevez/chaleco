import socket
import json
import base64
import os
from cryptography.fernet import Fernet
import tkinter as tk
from tkinter import messagebox

# Verificar si el archivo clave.key ya existe
if not os.path.exists("clave.key"):
    # Generar y guardar la clave de cifrado (solo haz esto una vez y guarda la clave)
    key = Fernet.generate_key()
    with open("clave.key", "wb") as clave_file:
        clave_file.write(key)
    print("Clave de cifrado generada y guardada en clave.key")
else:
    print("La clave de cifrado ya ha sido generada y se utilizará el archivo existente.")

# Cargar la clave de cifrado
with open("clave.key", "rb") as clave_file:
    key = clave_file.read()

# Verificar que la clave sea válida
try:
    cipher_suite = Fernet(key)
except ValueError:
    print("Error: La clave de cifrado cargada no es válida. Por favor, verifica el archivo clave.key.")
    exit(1)

# Lista de registros de ejemplo (esto debería ser reemplazado con tus datos reales)
registros = [
    [1, "Lote1", "123456", "Fabricante1", "2024-01-01", "2025-01-01", "Modelo1", 10, "M", "Procedencia1"],
    [2, "Lote2", "123457", "Fabricante2", "2024-02-01", "2025-02-01", "Modelo2", 15, "L", "Procedencia2"]
]

def obtener_registros_seleccionados():
    # En un caso real, esta función debería retornar los registros seleccionados por el usuario.
    # Aquí simplemente retornamos todos los registros de ejemplo.
    return registros

def transmitir():
    registros_seleccionados = obtener_registros_seleccionados()
    if registros_seleccionados:
        datos_transmitir = []
        for reg in registros_seleccionados:
            qr_image_base64 = base64.b64encode(reg[9].encode('utf-8')).decode('utf-8') if reg[9] else 'No QR available'
            datos_transmitir.append({
                "Id": reg[0],
                "Lote": reg[1],
                "Número de Serie": reg[2],
                "Fabricante": reg[3],
                "Fecha de Fabricación": reg[4],
                "Fecha de Vencimiento": reg[5],
                "Tipo de Modelo": reg[6],
                "Peso": reg[7],
                "Talla": reg[8],
                "Procedencia": reg[9],
                "QR Image": qr_image_base64
            })

        # Codificar los datos a JSON y luego cifrarlos
        datos_json = json.dumps({"data": datos_transmitir})
        datos_cifrados = cipher_suite.encrypt(datos_json.encode('utf-8'))

        transmitir_wifi(datos_cifrados)

def transmitir_wifi(datos_cifrados):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(("127.0.0.1", 8000))  # Cambia esto por la dirección IP y puerto de tu servidor
        sock.sendall(datos_cifrados)

        respuesta = sock.recv(1024)
        if respuesta.decode() == "OK":
            messagebox.showinfo("Éxito", "Datos transmitidos y confirmados por el servidor")
        else:
            messagebox.showerror("Error", f"Error en la confirmación del servidor: {respuesta.decode()}")

    except Exception as e:
        messagebox.showerror("Error", f"Error al transmitir: {str(e)}")
    finally:
        sock.close()

# Crear la ventana de la interfaz gráfica
ventana = tk.Tk()
ventana.title("Transmisor de Datos")

# Botón para transmitir datos
boton_transmitir = tk.Button(ventana, text="Transmitir Datos", command=transmitir)
boton_transmitir.pack(pady=20)

# Iniciar la interfaz gráfica
ventana.mainloop()

