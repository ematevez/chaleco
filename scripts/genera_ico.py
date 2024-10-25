from PIL import Image

# Abrir la imagen en formato .png o .jpg
imagen = Image.open("Logo.png")

# Convertir a .ico y guardar
imagen.save("mi_icono.ico", format="ICO", sizes=[(64, 64)])
