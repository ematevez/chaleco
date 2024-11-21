import sqlite3
from datetime import datetime

# Conexión a la base de datos
conn = sqlite3.connect('chalecos.db')
cursor = conn.cursor()

# Agregar el campo 'creado' si no existe
cursor.execute("ALTER TABLE chalecos_receptora ADD COLUMN fecha_destruido TEXT")
conn.commit()

print("Campo 'creado' agregado exitosamente a la tabla 'chalecos_receptora'.")
