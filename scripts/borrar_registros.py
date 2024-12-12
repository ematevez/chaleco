import sqlite3

def vaciar_tabla(db_path):
    """
    Elimina todos los registros de la tabla chalecos_receptora en la base de datos especificada.
    """
    try:
        # Conectar a la base de datos
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Confirmar acción con el usuario
        confirmacion = input("¿Estás seguro de que deseas vaciar la tabla 'chalecos_receptora'? Esto eliminará todos los registros. (sí/no): ")
        if confirmacion.lower() != 's':
            print("Operación cancelada.")
            return

        # Vaciar la tabla
        cursor.execute("DELETE FROM chalecos_receptora;")
        
        # Guardar los cambios
        conn.commit()
        print("Todos los registros de la tabla 'chalecos_receptora' han sido eliminados.")
    
    except sqlite3.Error as e:
        print(f"Error al intentar vaciar la tabla: {e}")
    finally:
        # Cerrar la conexión
        if conn:
            conn.close()

if __name__ == "__main__":
    # Cambia 'chalecos.db' por el nombre de tu archivo de base de datos si es diferente
    db_path = 'chalecos.db'

    # Vaciar la tabla
    vaciar_tabla(db_path)
