import cv2
import numpy as np
import pyzbar.pyzbar as qr

# Conexión a la cámara DVR mediante RTSP
cap = cv2.VideoCapture('rtsp://admin:Cotn2024@192.168.10.108:554/Streaming/Channels/801')
font = cv2.FONT_HERSHEY_PLAIN

# Preprocesar la imagen para mejorar la detección
def preprocesar_imagen(cuadro):
    # Convertir a escala de grises
    gris = cv2.cvtColor(cuadro, cv2.COLOR_BGR2GRAY)

    # Aplicar un filtro de suavizado (más fuerte para reducir el ruido)
    gris = cv2.GaussianBlur(gris, (7, 7), 0)

    # Mejorar el contraste y brillo
    alpha = 3.0  # Contraste (ajustable)
    beta = 50    # Brillo (ajustable)
    gris = cv2.convertScaleAbs(gris, alpha=alpha, beta=beta)

    # Aplicar un filtro de enfoque (sharpening) para mejorar los bordes
    kernel = np.array([[0, -1, 0], 
                       [-1, 5, -1],
                       [0, -1, 0]])
    gris = cv2.filter2D(gris, -1, kernel)

    # Aplicar binarización adaptativa para mejorar la visibilidad del QR
    gris = cv2.adaptiveThreshold(gris, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)

    return gris

# Ajustar el tamaño de la imagen para mejorar el rendimiento
def redimensionar_imagen(imagen, width=640):
    # Mantener la proporción al redimensionar
    height = int(imagen.shape[0] * (width / imagen.shape[1]))
    return cv2.resize(imagen, (width, height), interpolation=cv2.INTER_AREA)

while True:
    ret, cuadro = cap.read()

    if not ret:
        print("No se pudo obtener el cuadro. Verifica la conexión RTSP.")
        break

    # Redimensionar la imagen para mejorar el rendimiento
    cuadro = redimensionar_imagen(cuadro)

    # Preprocesar la imagen
    cuadro_procesado = preprocesar_imagen(cuadro)

    # Intentar detectar códigos QR en la imagen preprocesada
    qrdetectado = qr.decode(cuadro_procesado)

    # Filtrar solo códigos QR (ignorar otros formatos como PDF417)
    for i in qrdetectado:
        if i.type == 'QRCODE':
            print(i.data)  # Imprimir los datos del QR detectado

            # Dibujar un rectángulo alrededor del QR detectado
            cv2.rectangle(cuadro, (i.rect.left, i.rect.top), (i.rect.left + i.rect.width, i.rect.top + i.rect.height), (0, 255, 0), 3)
            
            # Mostrar el contenido del QR en el cuadro original
            cv2.putText(cuadro, str(i.data.decode("utf-8")), (i.rect.left, i.rect.top - 10), font, 1, (0, 255, 0), 2)

    # Mostrar el cuadro original con los códigos QR detectados
    cv2.imshow("Lector QR", cuadro)

    # Salir del bucle si se presiona la tecla 'q'
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Liberar recursos
cap.release()
cv2.destroyAllWindows()

