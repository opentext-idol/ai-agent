"""{
    "name": "Create PDF from images",
    "info": "Create a PDF containing a page for each image file from a FlowFile"
}"""

from idolnifi import *

#installPackage('pillow', 'fpdf2')

from PIL import Image
from fpdf import FPDF
from io import BytesIO

def addToPdf(part, pdf):
    with (
        part.readFile() as imgIn,
        Image.open(BytesIO(imgIn.readall())) as image
    ):
        pdf.add_page(format=image.size)
        pdf.image(image, 0, 0, image.size[0])

def handler(doc):
    pdf = FPDF(unit="pt")
    pdf.set_margin(0)
    pdf.set_text_color(255)
    with doc.modifying() as action:
        for part in action.parts():
            if part.isFilePart():
                addToPdf(part, pdf)
                part.deletePart()
        pdffile = getTempFile(extn=".pdf")
        pdf.output(pdffile)
        action.addFilename(pdffile, True, mimeType='application/pdf')
