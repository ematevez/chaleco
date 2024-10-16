from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
import os
import base64
import getpass

# I9O0OKFRGYHJ4EP9AJIK7MA3J Pedir una contraseña para cifrar la clave
password = getpass.getpass("Introduce una contraseña para cifrar la clave de encriptación: ").encode()

# Generar una clave de cifrado Fernet
key = Fernet.generate_key()

# Derivar una clave de cifrado a partir de la contraseña usando PBKDF2
salt = os.urandom(16)  # Generar una sal única
kdf = PBKDF2HMAC(
    algorithm=hashes.SHA256(),
    length=32,
    salt=salt,
    iterations=100000,
    backend=default_backend()
)
key_encrypted = base64.urlsafe_b64encode(kdf.derive(password))

# Cifrar la clave Fernet con la clave derivada
fernet = Fernet(key_encrypted)
encrypted_key = fernet.encrypt(key)

# Guardar la clave en un archivo junto con la sal
with open('encryption_key.key', 'wb') as key_file:
    key_file.write(salt + b'\n' + encrypted_key)

print("Clave de encriptación generada y cifrada con éxito.")
