import random
import tkinter as tk
from tkinter import messagebox
import serial  # Para la comunicación con el Arduino

# Configuración de la conexión serial con el Arduino
try:
    arduino = serial.Serial("COM3", 9600, timeout=1)  # Reemplaza "COM3" con el puerto correspondiente
except Exception as e:
    print(f"Error al conectar con el Arduino: {e}")
    arduino = None

# Función para generar un CAPTCHA aleatorio
def generar_captcha():
    palabras = ["python", "arduino", "control", "rele", "sensor", "script", "php", "papito", "mamita", "thiaguito"]
    return random.choice(palabras)

# Función para verificar el CAPTCHA
def verificar_captcha():
    respuesta = entrada_captcha.get().strip()
    if respuesta == captcha_correcto:
        messagebox.showinfo("Éxito", "✅ CAPTCHA resuelto correctamente.")
        etiqueta_estado.config(text="Relé ACTIVADO", fg="green")
        if arduino:
            arduino.write(b"ON\n")  # Envía el comando al Arduino
        boton_verificar.config(state="disabled")  # Deshabilita el botón de verificar
        boton_reiniciar.config(state="normal")  # Habilita el botón de reiniciar
    else:
        messagebox.showerror("Error", "❌ CAPTCHA incorrecto. Inténtalo de nuevo.")

# Función para reiniciar el CAPTCHA y desactivar el relé
def reiniciar():
    etiqueta_estado.config(text="Relé DESACTIVADO", fg="red")
    if arduino:
        arduino.write(b"OFF\n")  # Envía el comando al Arduino para desactivar los relés
    nuevo_captcha()
    boton_verificar.config(state="normal")  # Habilita el botón de verificar
    boton_reiniciar.config(state="disabled")  # Deshabilita el botón de reiniciar

# Función para generar un nuevo CAPTCHA
def nuevo_captcha():
    global captcha_correcto
    captcha_correcto = generar_captcha()
    canvas.delete("all")  # Limpia el canvas
    mostrar_captcha(captcha_correcto)
    entrada_captcha.delete(0, tk.END)

# Función para mostrar el CAPTCHA en diferentes alturas, rotaciones y con tachado
def mostrar_captcha(captcha):
    x_pos = 50  # Posición inicial x
    y_base = 50  # Base para las letras
    for letra in captcha:
        angle = random.randint(-30, 30)  # Ángulo de rotación
        y_offset = random.randint(-10, 10)  # Variación de altura
        letra_id = canvas.create_text(
            x_pos, y_base + y_offset, text=letra, font=("Arial", 20, "italic"), fill="gray"
        )
        canvas.itemconfig(letra_id)  # Configura el texto en el canvas

        # Coordenadas para el tachado
        x_start = x_pos - 10  # Inicio de la línea ligeramente a la izquierda
        y_start = y_base + y_offset - 5  # Arriba del centro de la letra
        x_end = x_pos + 10  # Fin de la línea ligeramente a la derecha
        y_end = y_base + y_offset + 5  # Abajo del centro de la letra

        # Dibuja la línea de tachado
        canvas.create_line(x_start, y_start, x_end, y_end, fill="red", width=2)

        x_pos += 30  # Avanza en el eje X

# Configuración inicial
captcha_correcto = generar_captcha()

# Crear la ventana principal
ventana = tk.Tk()
ventana.title("Simulador de Captcha")
ventana.geometry("500x300")
ventana.resizable(False, False)

# Etiqueta del texto "Resuelve el CAPTCHA"
etiqueta_titulo = tk.Label(ventana, text="Resuelve el CAPTCHA", font=("Arial", 14, "bold"))
etiqueta_titulo.pack(pady=10)

# Canvas para el CAPTCHA con rotación, alturas y tachado
canvas = tk.Canvas(ventana, width=400, height=100)
canvas.pack()

# Campo de entrada para el CAPTCHA
entrada_captcha = tk.Entry(ventana, font=("Arial", 12))
entrada_captcha.pack(pady=5)

# Botón para verificar el CAPTCHA
boton_verificar = tk.Button(ventana, text="Verificar", font=("Arial", 12), command=verificar_captcha)
boton_verificar.pack(pady=10)

# Botón para reiniciar
boton_reiniciar = tk.Button(ventana, text="Reiniciar", font=("Arial", 12), command=reiniciar, state="disabled")
boton_reiniciar.pack(pady=10)

# Etiqueta de estado del "relé"
etiqueta_estado = tk.Label(ventana, text="Relé DESACTIVADO", font=("Arial", 12), fg="red")
etiqueta_estado.pack(pady=10)

# Mostrar el CAPTCHA inicial
mostrar_captcha(captcha_correcto)

# Iniciar la ventana
ventana.mainloop()

# Cierra la conexión con el Arduino al salir
if arduino:
    arduino.close()
