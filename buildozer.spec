[app]

# Nombre que aparecerá en tu aplicación
title = MiAppChalecos

# Nombre del paquete (en formato de dominio inverso)
package.name = miappchalecos
package.domain = org.miempresa

# Versión de la app
version = 0.1

# Ruta donde están tus archivos fuente
source.dir = .

# Extensiones a incluir en la compilación
source.include_exts = py,png,jpg,kv,atlas

# Icono de tu app (debes poner un archivo icon.png en la carpeta de tu proyecto)
icon.filename = %(source.dir)s/icon.png

# Orientación de la pantalla: 'landscape' o 'portrait'
orientation = portrait

# (list) Requisitos de tu app (lo que necesita para funcionar)
requirements = python3,kivy,sqlite3,qrcode,bleak

# (list) Permisos requeridos por tu app
android.permissions = INTERNET, BLUETOOTH, BLUETOOTH_ADMIN, BLUETOOTH_CONNECT, ACCESS_FINE_LOCATION

# Arquitectura de Android. Por defecto suele estar bien.
android.archs = armeabi-v7a, arm64-v8a

# APK que no sea firmada (esto es para debug)
android.debug = 1

# Formato del paquete APK
android.release_artifact = apk

# Archivo principal de tu aplicación (por defecto main.py)

# Firmar la aplicación con claves predeterminadas (si quieres liberar la APK debes usar claves reales)
#android.debug_keystore = %(buildozer_dir)s/android/debug.keystore

# Mostrar consola (útil para ver errores al probar)
log_level = 2
