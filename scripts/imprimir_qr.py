"""
SCRIPT PARA EXTRAER TODOS LOS QR E IMPRIMIRLOS
"""

import sqlite3
from fpdf import FPDF, XPos, YPos
from io import BytesIO

# Conectar a la base de datos
conn = sqlite3.connect('chalecos.db')
cursor = conn.cursor()

# Consultar los datos de los chalecos junto con la imagen QR almacenada
cursor.execute('SELECT numero_serie, fabricante, lote, qr_image FROM chalecos')  # Incluye la columna con el QR
chalecos = cursor.fetchall()

# Crear una clase para generar el PDF
class PDF(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 12)
        self.cell(0, 10, 'Listado de Chalecos con QR', 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}', 0, new_x=XPos.RIGHT, new_y=YPos.TOP, align='C')

pdf = PDF()
pdf.set_auto_page_break(auto=True, margin=15)
pdf.add_page()

# Estilo para el texto
pdf.set_font('Helvetica', '', 10)

# Función para agregar QR a la página PDF
def agregar_qr_a_pdf(numero_serie, fabricante, lote, qr_image_blob, pdf):
    # Convertir el blob de la imagen QR en bytes
    img_bytes = BytesIO(qr_image_blob)

    # Insertar texto antes de cada QR
    pdf.cell(0, 10, f'Lote: {lote}, Fabricante: {fabricante}, N° Serie: {numero_serie}', 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # Insertar la imagen QR desde el blob
    pdf.image(img_bytes, x=10, y=pdf.get_y(), w=30, h=30)
    pdf.ln(35)  # Saltar a la siguiente posición (depende del tamaño del QR)

# Recorrer los resultados de la base de datos y agregar las imágenes QR
for chaleco in chalecos:
    numero_serie, fabricante, lote, qr_image_blob = chaleco
    if qr_image_blob:
        agregar_qr_a_pdf(numero_serie, fabricante, lote, qr_image_blob, pdf)
    else:
        # Manejar el caso en que no haya QR almacenado
        pdf.cell(0, 10, f'Lote: {lote}, Fabricante: {fabricante}, N° Serie: {numero_serie} (Sin QR)', 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(35)

# Guardar el PDF en un archivo
pdf.output('chalecos_qr.pdf')

# Cerrar la conexión a la base de datos
conn.close()

print("PDF generado exitosamente.")
