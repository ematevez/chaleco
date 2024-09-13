import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
from tkcalendar import DateEntry
from PIL import Image, ImageTk
import cv2
import qrcode
import datetime
import os

# Ruta RTSP de la cámara (modifica esto con la URL de tu cámara)
RTSP_URL = "rtsp://admin:admin@192.168.10.103:554"

# Variable para controlar si el streaming está activo
streaming_activo = False
datos = {}

# Función para habilitar o deshabilitar los campos de texto
def habilitar_campos(estado):
    state = tk.NORMAL if estado else tk.DISABLED
    entry_numero_serie.config(state=state)
    entry_numero_lote.config(state=state)
    entry_fabricante.config(state=state)
    entry_fecha_fabricacion.config(state=state)
    entry_fecha_vencimiento.config(state=state)
    entry_tipo_modelo.config(state=state)
    entry_peso.config(state=state)
    entry_talla.config(state=state)
    entry_proveniente.config(state=state)

# Función para borrar los campos de texto
def limpiar_campos():
    entry_numero_serie.delete(0, tk.END)
    entry_numero_lote.delete(0, tk.END)
    entry_fabricante.delete(0, tk.END)
    entry_fecha_fabricacion.set_date(datetime.datetime.now())
    entry_fecha_vencimiento.set_date(datetime.datetime.now())
    entry_tipo_modelo.delete(0, tk.END)
    entry_peso.delete(0, tk.END)
    entry_talla.delete(0, tk.END)
    entry_proveniente.delete(0, tk.END)

# Validación de los campos de entrada
def validar_campos():
    mensaje_error = ""

    # Verifica que todos los campos estén llenos
    if not (entry_numero_serie.get() and entry_numero_lote.get() and entry_fabricante.get() and
            entry_fecha_fabricacion.get() and entry_fecha_vencimiento.get() and entry_tipo_modelo.get() and
            entry_peso.get() and entry_talla.get() and entry_proveniente.get()):
        mensaje_error = "Todos los campos son obligatorios.\n"

    # Valida que la fecha de fabricación sea menor que la de vencimiento
    fecha_fabricacion = entry_fecha_fabricacion.get_date()
    fecha_vencimiento = entry_fecha_vencimiento.get_date()
    if fecha_fabricacion >= fecha_vencimiento:
        mensaje_error += "La fecha de fabricación debe ser menor que la fecha de vencimiento.\n"

    # Valida que el peso sea un número
    try:
        float(entry_peso.get())
    except ValueError:
        mensaje_error += "El peso debe ser un número válido.\n"

    # Si hay errores, muestra el mensaje y retorna False
    if mensaje_error:
        messagebox.showwarning("Validación", mensaje_error)
        return False
    else:
        return True

# Función para tomar una foto desde la cámara RTSP
def capturar_foto():
    cap = cv2.VideoCapture(RTSP_URL)
    ret, frame = cap.read()
    if not ret:
        messagebox.showerror("Error", "No se pudo capturar la imagen de la cámara.")
        return None

    # Guarda la imagen capturada
    file_path = "captura.png"
    cv2.imwrite(file_path, frame)
    cap.release()

    # Muestra la imagen en la interfaz
    img = Image.open(file_path)
    img.thumbnail((150, 150))
    img_tk = ImageTk.PhotoImage(img)
    label_imagen.config(image=img_tk)
    label_imagen.image = img_tk  # Guardar referencia para evitar que la imagen se recolecte

    return file_path

# Función para generar el código QR y guardar los datos
def generar_qr_y_guardar():
    global datos
    # Validar los campos antes de proceder
    if not validar_campos():
        return

    # Recoge los datos de los campos de entrada
    datos = {
        "fecha_hora": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "numero_serie": entry_numero_serie.get(),
        "numero_lote": entry_numero_lote.get(),
        "fabricante": entry_fabricante.get(),
        "fecha_fabricacion": entry_fecha_fabricacion.get(),
        "fecha_vencimiento": entry_fecha_vencimiento.get(),
        "tipo_modelo": entry_tipo_modelo.get(),
        "peso": entry_peso.get(),
        "talla": entry_talla.get(),
        "proveniente": entry_proveniente.get(),
        "orden_id": f"{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}",  # ID de orden único
    }

    # Captura la foto
    foto_path = capturar_foto()
    if foto_path is None:
        return

    # Genera el código QR
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(datos)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    qr_file_path = f"{datos['orden_id']}_qr.png"
    qr_img.save(qr_file_path)

    # Guarda los datos en un archivo de texto (o en una base de datos)
    with open(f"{datos['orden_id']}_datos.txt", "w") as file:
        for key, value in datos.items():
            file.write(f"{key}: {value}\n")
        file.write(f"Foto: {foto_path}\n")
        file.write(f"QR: {qr_file_path}\n")

    # Muestra el QR en la interfaz
    qr_img = Image.open(qr_file_path)
    qr_img.thumbnail((150, 150))
    qr_img_tk = ImageTk.PhotoImage(qr_img)
    label_qr.config(image=qr_img_tk)
    label_qr.image = qr_img_tk  # Guardar referencia para evitar que la imagen se recolecte

    # Abre el archivo QR para impresión
    os.system(f"start {qr_file_path}")

    messagebox.showinfo("Éxito", f"Datos y QR guardados exitosamente con Orden ID: {datos['orden_id']}")

# Función para iniciar el streaming de la cámara y la grabación
def iniciar_streaming():
    global streaming_activo
    global datos
    streaming_activo = True  # Activa el streaming
    habilitar_campos(False)  # Deshabilitar los campos
    cap = cv2.VideoCapture(RTSP_URL)
    if not cap.isOpened():
        messagebox.showerror("Error", "No se pudo acceder a la cámara.")
        return

    # Crear objeto VideoWriter para guardar el video
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter(f"{datos['orden_id']}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.avi", fourcc, 20.0, (640, 480))

    # Texto que será mostrado en el video (orden_id)
    id_text = datos["orden_id"]

    while streaming_activo:  # Mientras el streaming esté activo
        ret, frame = cap.read()
        if not ret:
            break

        # Superponer el ID y el código QR en el video
        cv2.putText(frame, id_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)

        # Cargar el código QR generado
        qr_img = cv2.imread(f"{datos['orden_id']}_qr.png")
        if qr_img is not None:
            qr_img = cv2.resize(qr_img, (100, 100))
            frame[10:110, 10:110] = qr_img  # Superpone el QR en la esquina superior izquierda

        out.write(frame)
        cv2.imshow('Streaming de la Cámara', frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):  # También permitir salir con 'q'
            break

    cap.release()
    out.release()
    cv2.destroyAllWindows()

# Función para detener el streaming
def detener_grabacion():
    global streaming_activo
    streaming_activo = False  # Detiene el streaming
    cv2.destroyAllWindows()  # Cierra cualquier ventana de OpenCV abierta
    limpiar_campos()  # Limpia los campos
    habilitar_campos(True)  # Vuelve a habilitar los campos
    messagebox.showinfo("Grabación", "El streaming y la grabación han sido detenidos.")

# Configuración de la ventana principal
ventana = tk.Tk()
ventana.title("Sistema de Destrucción")
ventana.geometry("600x800")
ventana.config(bg="#f0f0f0")

# Frame para organizar los campos de entrada
frame_campos = tk.Frame(ventana, bg="#f0f0f0")
frame_campos.pack(pady=20)

def crear_campo(texto, row, frame, widget_class=tk.Entry):
    label = tk.Label(frame, text=texto, bg="#f0f0f0")
    label.grid(row=row, column=0, padx=10, pady=5, sticky="e")
    entry = widget_class(frame)
    entry.grid(row=row, column=1, padx=10, pady=5)
    return entry

# Creación de los campos de entrada
entry_numero_serie = crear_campo("Número de Serie:", 0, frame_campos)
entry_numero_lote = crear_campo("Número de Lote:", 1, frame_campos)
entry_fabricante = crear_campo("Fabricante:", 2, frame_campos)
entry_fecha_fabricacion = crear_campo("Fecha de Fabricación:", 3, frame_campos, widget_class=DateEntry)
entry_fecha_vencimiento = crear_campo("Fecha de Vencimiento:", 4, frame_campos, widget_class=DateEntry)
entry_tipo_modelo = crear_campo("Tipo/Modelo:", 5, frame_campos)
entry_peso = crear_campo("Peso (kg):", 6, frame_campos)
entry_talla = crear_campo("Talla:", 7, frame_campos)
entry_proveniente = crear_campo("Proveniente:", 8, frame_campos)

# Frame para las imágenes
frame_imagenes = tk.Frame(ventana, bg="#f0f0f0")
frame_imagenes.pack(pady=20)

label_imagen = tk.Label(frame_imagenes, bg="#f0f0f0", text="Imagen")
label_imagen.grid(row=0, column=0, padx=20)

label_qr = tk.Label(frame_imagenes, bg="#f0f0f0", text="QR")
label_qr.grid(row=0, column=1, padx=20)

# Botones para generar QR, iniciar y detener streaming
btn_generar_qr = tk.Button(ventana, text="Generar QR y Guardar", command=generar_qr_y_guardar, bg="green", fg="white", padx=20, pady=10)
btn_generar_qr.pack(pady=10)

btn_iniciar_streaming = tk.Button(ventana, text="Iniciar Streaming", command=iniciar_streaming, bg="blue", fg="white", padx=20, pady=10)
btn_iniciar_streaming.pack(pady=10)

btn_detener_grabacion = tk.Button(ventana, text="Detener Grabación", command=detener_grabacion, bg="red", fg="white", padx=20, pady=10)
btn_detener_grabacion.pack(pady=10)

ventana.mainloop()
