# Chaleco V1-V2-V3 - Master & Slave Apps
Este proyecto incluye varias versiones de aplicaciones (Master y Slave) para la gestión de chalecos, que utilizan la lectura de códigos QR y el almacenamiento de información en una base de datos local.
---
## Master
El servidor Master está diseñado para gestionar la transmisión de datos y recibir información de chalecos (incluyendo QR) a través de conexiones de red.
### Funcionalidades Implementadas:
#### Master V3
- **Funcionalidad del servidor completa**.
- **Pendiente**: Implementación de la transmisión por Wi-Fi (cuenta de ema).
  
### TODO:
- Acomodar la visualización de los datos.
- Acomodar la impresión de códigos QR.
- Implementar un **Date Picker** para las fechas.
#### Master V4 (Funcional)
- **Transmisión funcional**.
- **Pendiente**: Transmisión por Wi-Fi (cuenta de ema).
  
### TODO:
- Visualización de datos funcional.
- Acomodar la impresión de códigos QR (Funcional).
- Implementar un **Date Picker** para las fechas (Funcional).
- Opción para copiar la base de datos o incluir la opción de verificación mediante "check".
- Acomodar la gestión de lotes.
#### Master V5 (Funcional)
### TODO:
- Arreglar la confirmación de envío, que actualmente no permite cerrar el diálogo.
---
## Slave
El cliente Slave está diseñado para ser ejecutado en un PC portátil, y su propósito es recibir y procesar los datos enviados desde el servidor Master.
### Funcionalidades Implementadas:
#### Slave (Funcional)
- **Recibe datos pero no se conecta automáticamente, solo escucha**.
  
### TODO:
- Acomodar la visualización de datos.
- Verificar los datos en la base de datos y seleccionar qué chaleco destruir.
- Habilitar el uso de la cámara para escanear los códigos QR.
#### Slave_12 (Última versión 25/09 - Funcional)
- **Recibe datos y los guarda en la base de datos, incluyendo los códigos QR**.
- **Visualización de datos**: No implementado aún.
  
### TODO:
- Escanear un código QR y verificar si coincide con un registro existente.
#### cam / cam1 funcional del codigo qr_test con problemas del pyzbar
---

#### Slave_21 ->  
- Se estabilizo con pyzbar -> version de yolo mas funcional falta integrar  slave_21 con slave_12 solo funcion detectar
-# IMPORTANTE! Mejorar la impresion de los datos del qr - utilizar id para armarlo sino duplicidad de lota


### Ejemplo de Activación del Entorno Virtual

Para activar el entorno virtual del proyecto:
```bash
source ~/Desktop/new_env/Scripts/activate
source ~/Desktop/chaleco/.venv/scripts/activate

A revisar ->
https://github.com/yushulx/python-barcode-qrcode-sdk/tree/main/examples/official/9.x/yolo_qr
https://github.com/yushulx/python-barcode-qrcode-sdk/tree/main/examples/official/9.x/webcam


https://github.com/Eric-Canas/QReader
https://github.com/ErenKaymakci/Real-Time-QR-Detection-and-Decoding


https://www.dynamsoft.com/customer/license/trialLicenseList (Hasta el 3 de noviembre)

