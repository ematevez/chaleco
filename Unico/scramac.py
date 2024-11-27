import sqlite3
import hashlib
from datetime import datetime
import uuid

def obtener_mac():
    """Obtiene la dirección MAC de la máquina."""
    mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) for elements in range(0, 8 * 6, 8)][::-1])
    return mac

def encriptar(valor):
    """Encripta un valor usando SHA-256."""
    return hashlib.sha256(valor.encode()).hexdigest()

def borrar_configuracion():
    """Elimina la configuración actual de la base de datos."""
    conn = sqlite3.connect('chalecos.db')
    cursor = conn.cursor()

    # Eliminar la configuración existente si existe
    cursor.execute("DELETE FROM configuracion WHERE id = 1")
    conn.commit()
    conn.close()
    print("Configuración eliminada correctamente.")

def inicializar_configuracion():
    """Inicializa o actualiza la configuración con la MAC y la fecha."""
    conn = sqlite3.connect('chalecos.db')
    cursor = conn.cursor()

    # Crear la tabla si no existe
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS configuracion (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mac_autorizada TEXT,
            fecha_creacion TEXT,
            codigo TEXT
        )
    ''')

    # Obtener la MAC y la fecha actual
    mac_actual = obtener_mac()
    fecha_actual = datetime.now()
    fecha_actual_str = fecha_actual.strftime('%Y-%m-%d')  # Fecha en texto plano

    # Encriptar la MAC
    mac_encriptada = encriptar(mac_actual)

    # Generar un nuevo código basado en la MAC y la nueva fecha
    codigo = encriptar(mac_actual + fecha_actual_str)

    # Insertar la nueva configuración
    cursor.execute('''
        INSERT OR REPLACE INTO configuracion (id, mac_autorizada, fecha_creacion, codigo)
        VALUES (1, ?, ?, ?)
    ''', (mac_encriptada, fecha_actual_str, codigo))

    conn.commit()
    conn.close()
    print("Configuración inicializada correctamente. Fecha extendida 15 días más.")

if __name__ == '__main__':
    borrar_configuracion()  # Eliminar configuración existente
    inicializar_configuracion()  # Crear nueva configuración

