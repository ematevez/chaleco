"""
Te dice que tiene la base de datos
"""
import sqlite3

# Conectar a la base de datos SQLite
conexion = sqlite3.connect('chalecos.db')
cursor = conexion.cursor()

# Ejecutar la consulta PRAGMA table_info para obtener información de la tabla
tabla = 'chalecos_receptora'
cursor.execute(f"PRAGMA table_info({tabla});")

# Obtener los resultados y mostrar los campos y características
columnas = cursor.fetchall()

print(f"Información de la tabla {tabla}:")
for columna in columnas:
    cid, nombre, tipo, notnull, dflt_value, pk = columna
    print(f"Columna: {nombre}")
    print(f"  Tipo de dato: {tipo}")
    print(f"  No Nulo: {bool(notnull)}")
    print(f"  Valor por defecto: {dflt_value}")
    print(f"  Llave primaria: {bool(pk)}\n")

# Cerrar la conexión
conexion.close()
