"""{
    "name": "Create PDF from images",
    "info": "Create a PDF containing a page for each image file from a FlowFile"
}"""

# BEGIN COPYRIGHT NOTICE
# Copyright 2026 Open Text.
#
# The only warranties for products and services of Open Text and its affiliates and licensors
# ("Open Text") are as may be set forth in the express warranty statements accompanying such
# products and services. Nothing herein should be construed as constituting an additional warranty.
# Open Text shall not be liable for technical or editorial errors or omissions contained herein.
# The information contained herein is subject to change without notice.
#
# END COPYRIGHT NOTICE

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
