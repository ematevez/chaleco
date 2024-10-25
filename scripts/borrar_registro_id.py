import sqlite3

def mostrar_registros(db_path):
    # Conectar a la base de datos
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Obtener todos los registros
    cursor.execute("SELECT * FROM chalecos;")
    registros = cursor.fetchall()
    
    # Mostrar los registros en la consola
    print("Registros en la base de datos:")
    for registro in registros:
        print(registro)
    
    # Cerrar la conexión
    conn.close()

def borrar_registro(db_path, id_registro):
    # Conectar a la base de datos
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Eliminar el registro con el ID especificado
    cursor.execute("DELETE FROM chalecos_receptora WHERE id = ?;", (id_registro,))
    
    # Guardar los cambios
    conn.commit()
    
    # Cerrar la conexión
    conn.close()
    print(f"Registro con ID {id_registro} ha sido eliminado.")

if __name__ == "__main__":
    # Cambia 'tu_base_de_datos.db' por el nombre de tu archivo de base de datos
    db_path = 'chalecos.db'
    
    # Mostrar todos los registros
    mostrar_registros(db_path)
    
    # Pedir al usuario el ID del registro a borrar
    id_registro = input("Introduce el ID del registro que deseas borrar: ")
    
    # Borrar el registro seleccionado
    borrar_registro(db_path, id_registro)
