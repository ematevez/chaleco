import sqlite3
import os

# Ruta de la base de datos
db_path = 'chalecos.db'  # Ajusta la ruta si es diferente

def reiniciar_tabla_chalecos(db_path):
    if not os.path.isfile(db_path):
        print("La base de datos no existe.")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Vaciar la tabla chalecos_receptora
        cursor.execute("DELETE FROM chalecos_receptora")

        # Reiniciar los IDs automáticos para la tabla chalecos_receptora
        cursor.execute("DELETE FROM sqlite_sequence WHERE name = 'chalecos_receptora'")

        conn.commit()
        conn.close()

        print("La tabla 'chalecos_receptora' ha sido reiniciada correctamente.")
    except sqlite3.Error as e:
        print(f"Error al reiniciar la tabla: {e}")

# Ejecutar la función
reiniciar_tabla_chalecos(db_path)
