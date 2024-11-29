import math
import secrets
import hashlib
import time

# Función para generar un número seguro
def generar_numero_seguro(intentos):
    # Usar cifras combinadas de π y e
    pi_str = str(math.pi).replace(".", "")[:1000]  # Primeros 1000 dígitos de π
    e_str = str(math.e).replace(".", "")[:1000]    # Primeros 1000 dígitos de e
    base = pi_str + e_str  # Combinamos ambos números

    # Seleccionar 5 cifras aleatorias no consecutivas
    seleccion = "".join(secrets.choice(base) for _ in range(5))

    # Transformación adicional: aplicar salt y operaciones matemáticas
    salt = secrets.token_hex(8)  # Salt aleatorio de 8 caracteres
    transformado = "".join(chr((int(cifra) * 3 ^ 7) % 94 + 33) for cifra in seleccion)

    # Adjuntar marca de tiempo
    timestamp = int(time.time())
    resultado = f"{transformado}:{salt}:{timestamp}"

    # Cifrado con SHA-256
    hash_resultado = hashlib.sha256(resultado.encode()).hexdigest()

    # Verificar si ya se ha generado el mismo resultado en intentos previos
    if hash_resultado in intentos:
        intentos[hash_resultado] += 1
    else:
        intentos[hash_resultado] = 1

    # Retornar el número cifrado y el número de repeticiones
    return hash_resultado

# Función principal para simular los intentos hasta encontrar repetidos
def ejecutar_simulador(intentos_max=100):
    intentos = {}  # Diccionario para guardar los números generados
    intentos_totales = 0
    repetido = False
    numero_repetido = ""

    while not repetido and intentos_totales < intentos_max:
        numero_seguro = generar_numero_seguro(intentos)
        intentos_totales += 1

        # Comprobar si el número se repite
        if intentos[numero_seguro] > 1:
            repetido = True
            numero_repetido = numero_seguro

    # Mostrar el resultado
    if repetido:
        print(f"El número repetido es: {numero_repetido}")
        print(f"Se repitió después de {intentos_totales} intentos.")
    else:
        print(f"No se encontró repetición en {intentos_max} intentos.")

# Ejecutar el simulador con 100 intentos
ejecutar_simulador(intentos_max=1000000000000000000)
