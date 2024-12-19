import cv2

def find_usb_cameras(max_devices=10):
    """
    Encuentra las cámaras conectadas al USB probando índices de dispositivos.
    
    Args:
        max_devices (int): Número máximo de dispositivos a comprobar.
        
    Returns:
        list: Lista de índices de cámaras disponibles.
    """
    available_cameras = []
    
    for device_index in range(max_devices):
        cap = cv2.VideoCapture(device_index, cv2.CAP_DSHOW)  # Intenta abrir el dispositivo
        if cap.isOpened():
            available_cameras.append(device_index)
            cap.release()  # Libera el dispositivo después de probar
        else:
            cap.release()
    
    return available_cameras

if __name__ == "__main__":
    cameras = find_usb_cameras()
    if cameras:
        print(f"Cámaras detectadas en los índices: {cameras}")
    else:
        print("No se detectaron cámaras.")
