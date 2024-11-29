import random
import tkinter as tk
from tkinter import messagebox

# Función para generar un captcha aleatorio
def generar_captcha():
    palabras = ["python", "arduino", "control", "rele", "sensor", "script"]
    return random.choice(palabras)

# Función para verificar el CAPTCHA
def verificar_captcha():
    respuesta = entrada_captcha.get().strip()
    if respuesta == captcha_correcto:
        messagebox.showinfo("Éxito", "✅ CAPTCHA resuelto correctamente.")
        etiqueta_estado.config(text="Relé ACTIVADO", fg="green")
        ventana.after(2000, desactivar_rele)  # Desactiva el relé después de 2 segundos
    else:
        messagebox.showerror("Error", "❌ CAPTCHA incorrecto. Inténtalo de nuevo.")

# Función para desactivar el "relé"
def desactivar_rele():
    etiqueta_estado.config(text="Relé DESACTIVADO", fg="red")
    nuevo_captcha()

# Función para generar un nuevo CAPTCHA
def nuevo_captcha():
    global captcha_correcto
    captcha_correcto = generar_captcha()
    etiqueta_captcha.config(text=f"Resuelve el CAPTCHA: {captcha_correcto}")
    entrada_captcha.delete(0, tk.END)

# Configuración inicial
captcha_correcto = generar_captcha()

# Crear la ventana principal
ventana = tk.Tk()
ventana.title("Simulador de Captcha")
ventana.geometry("400x200")
ventana.resizable(False, False)

# Etiqueta del CAPTCHA
etiqueta_captcha = tk.Label(ventana, text=f"Resuelve el CAPTCHA: {captcha_correcto}", font=("Arial", 14))
etiqueta_captcha.pack(pady=10)

# Campo de entrada para el CAPTCHA
entrada_captcha = tk.Entry(ventana, font=("Arial", 12))
entrada_captcha.pack(pady=5)

# Botón para verificar el CAPTCHA
boton_verificar = tk.Button(ventana, text="Verificar", font=("Arial", 12), command=verificar_captcha)
boton_verificar.pack(pady=10)

# Etiqueta de estado del "relé"
etiqueta_estado = tk.Label(ventana, text="Relé DESACTIVADO", font=("Arial", 12), fg="red")
etiqueta_estado.pack(pady=10)

# Iniciar la ventana
ventana.mainloop()
