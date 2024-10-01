import cv2 as cv
import numpy as np
import time
from threading import Thread
import queue
from pyzbar.pyzbar import decode  # Asegúrate de tener instalada la librería pyzbar

winName = 'QR Detection'
threshold = 0.6

# Cargar nombres de clase y modelo YOLOv3-tiny
classes = open('qrcode.names').read().strip().split('\n')
net = cv.dnn.readNetFromDarknet('qrcode-yolov3-tiny.cfg', 'qrcode-yolov3-tiny.weights')
net.setPreferableBackend(cv.dnn.DNN_BACKEND_OPENCV)

def postprocess(frame, outs):
    frameHeight, frameWidth = frame.shape[:2]
    classIds = []
    confidences = []
    boxes = []

    for out in outs:
        for detection in out:
            scores = detection[5:]
            classId = np.argmax(scores)
            confidence = scores[classId]
            if confidence > threshold:
                x, y, width, height = detection[:4] * np.array([frameWidth, frameHeight, frameWidth, frameHeight])
                left = int(x - width / 2)
                top = int(y - height / 2)
                classIds.append(classId)
                confidences.append(float(confidence))
                boxes.append([left, top, int(width), int(height)])

    indices = cv.dnn.NMSBoxes(boxes, confidences, threshold, threshold - 0.1)
    if not isinstance(indices, tuple):
        for i in indices.flatten():
            box = boxes[i]
            left = box[0]
            top = box[1]
            width = box[2]
            height = box[3]

            # Extraer la región de interés (ROI) para decodificación
            roi = frame[top:top + height, left:left + width]
            
            # Verificar que la ROI no esté vacía
            if roi.size == 0:
                print("Error: ROI está vacía.")
                continue

            # Decodificar el QR
            decoded_objects = decode(roi)
            for obj in decoded_objects:
                print("Contenido QR:", obj.data.decode('utf-8'))  # Muestra el contenido del QR

            # Dibujar bounding box para objetos
            cv.rectangle(frame, (left, top), (left + width, top + height), (0, 0, 255))

            # Dibujar nombre de clase y confianza
            label = '%s:%.2f' % (classes[classIds[i]], confidences[i])
            cv.putText(frame, label, (left, top), cv.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255))

# Determinar la capa de salida
ln = net.getLayerNames()
ln = [ln[i - 1] for i in net.getUnconnectedOutLayers().flatten()]

# Conectar a la cámara RTSP
cap = cv.VideoCapture('rtsp://admin:Cotn2024@192.168.10.108:554/Streaming/Channels/801')

class QueueFPS(queue.Queue):
    def __init__(self):
        queue.Queue.__init__(self)
        self.startTime = 0
        self.counter = 0

    def put(self, v):
        queue.Queue.put(self, v)
        self.counter += 1
        if self.counter == 1:
            self.startTime = time.time()

    def getFPS(self):
        return self.counter / (time.time() - self.startTime)

process = True

# Hilo de captura de frames
framesQueue = QueueFPS()

def framesThreadBody():
    global framesQueue, process

    while process:
        hasFrame, frame = cap.read()
        if not hasFrame:
            print("Error: No se pudo capturar un marco. Verifica la conexión de la cámara.")
            break
        framesQueue.put(frame)

# Hilo de procesamiento de frames
processedFramesQueue = queue.Queue()
predictionsQueue = QueueFPS()

def processingThreadBody():
    global processedFramesQueue, predictionsQueue, process

    while process:
        frame = None
        try:
            frame = framesQueue.get_nowait()
            framesQueue.queue.clear()  # Limpiar la cola de frames
        except queue.Empty:
            continue

        if frame is not None:
            blob = cv.dnn.blobFromImage(frame, 1/255, (416, 416), swapRB=True, crop=False)
            processedFramesQueue.put(frame)

            # Ejecutar el modelo
            net.setInput(blob)
            outs = net.forward(ln)
            predictionsQueue.put(outs)

framesThread = Thread(target=framesThreadBody)
framesThread.start()

processingThread = Thread(target=processingThreadBody)
processingThread.start()

# Bucle de postprocesamiento y renderización
while cv.waitKey(1) < 0:
    try:
        # Solicitar predicción primero porque ponen después de los frames
        outs = predictionsQueue.get_nowait()
        frame = processedFramesQueue.get_nowait()

        postprocess(frame, outs)

        # Poner información de eficiencia
        if predictionsQueue.counter > 1:
            label = 'Camera: %.2f FPS' % (framesQueue.getFPS())
            cv.putText(frame, label, (0, 15), cv.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0))

            label = 'Network: %.2f FPS' % (predictionsQueue.getFPS())
            cv.putText(frame, label, (0, 30), cv.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0))

            label = 'Skipped frames: %d' % (framesQueue.counter - predictionsQueue.counter)
            cv.putText(frame, label, (0, 45), cv.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0))

        cv.imshow(winName, frame)
    except queue.Empty:
        print("Esperando frames procesados...")

process = False
framesThread.join()
processingThread.join()
cap.release()
cv.destroyAllWindows()
