import sqlite3

def update_transmitidos(db_path):
    # Conectar a la base de datos
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Actualizar el campo 'transmitido' a 0 para todos los registros
    cursor.execute("UPDATE chalecos SET transmitido = 0;")
    
    # Guardar los cambios
    conn.commit()
    
    # Cerrar la conexión
    conn.close()
    print("Se han actualizado los campos 'transmitido' a 0.")

if __name__ == "__main__":
    # Cambia 'tu_base_de_datos.db' por el nombre de tu archivo de base de datos
    update_transmitidos('chalecos.db')
