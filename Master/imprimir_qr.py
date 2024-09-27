"""
SCRIPT PARA EXTRAER TODOS LOS QR E IMPRIMIRLOS
"""

import sqlite3
import qrcode
from fpdf import FPDF, XPos, YPos
from io import BytesIO

# Conectar a la base de datos
conn = sqlite3.connect('tu_base_de_datos.db')
cursor = conn.cursor()

# Consultar los datos de los chalecos
cursor.execute('SELECT numero_serie, fabricante, lote FROM chalecos')
chalecos = cursor.fetchall()

# Crear una clase para generar el PDF
class PDF(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 12)  # Cambiar 'Arial' por 'Helvetica'
        self.cell(0, 10, 'Listado de Chalecos con QR', 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)  # Cambiar 'Arial' por 'Helvetica'
        self.cell(0, 10, f'Página {self.page_no()}', 0, new_x=XPos.RIGHT, new_y=YPos.TOP, align='C')

pdf = PDF()
pdf.set_auto_page_break(auto=True, margin=15)
pdf.add_page()

# Estilo para el texto
pdf.set_font('Helvetica', '', 10)  # Cambiar 'Arial' por 'Helvetica'

# Función para agregar QR a la página PDF
def agregar_qr_a_pdf(numero_serie, fabricante, lote, pdf):
    # Generar código QR
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
    qr.add_data(numero_serie)
    qr.make(fit=True)

    img = qr.make_image(fill='black', back_color='white')

    # Convertir la imagen QR a bytes
    img_bytes = BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)

    # Insertar texto antes de cada QR
    pdf.cell(0, 10, f'Lote: {lote}, Fabricante: {fabricante}, N° Serie: {numero_serie}', 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # Insertar la imagen del QR
    pdf.image(img_bytes, x=10, y=pdf.get_y(), w=30, h=30)
    pdf.ln(35)  # Saltar a la siguiente posición (depende del tamaño del QR)

# Recorrer los resultados de la base de datos y generar los QR
for chaleco in chalecos:
    numero_serie, fabricante, lote = chaleco
    agregar_qr_a_pdf(numero_serie, fabricante, lote, pdf)

# Guardar el PDF en un archivo
pdf.output('chalecos_qr.pdf')

# Cerrar la conexión a la base de datos
conn.close()

print("PDF generado exitosamente.")
