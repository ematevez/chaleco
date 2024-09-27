import cv2
import numpy as np
import pyzbar.pyzbar as qr

cap = cv2.VideoCapture(0)
font = cv2.FONT_HERSHEY_PLAIN

while True:
      ret,cuadro = cap.read()
      qrdetectado=qr.decode(cuadro)
     
      for i in qrdetectado:
          print (i.data)
          cv2.rectangle(cuadro,(i.rect.left,i.rect.top),(i.rect.left+i.rect.width,i.rect.top+i.rect.height),(0,255,0),3)
          cv2.putText(cuadro,str((i.data).decode("utf-8")),(30,30),font,1,(0,255,0),2) 
      cv2.imshow("Lector QR", cuadro)
      if cv2.waitKey(1) & 0xFF == ord('q'):
          break