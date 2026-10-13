"""{
    "name": "Highlight regions in an image",
    "info": "Highlight regions in images using rectangle data specified in the file part metadata"
}"""

from idolnifi import *

#installPackage('pillow')

from PIL import Image, ImageDraw
from io import BytesIO

def updateImage(imgIn, regions, imgOut):
    with (
        Image.open(BytesIO(imgIn.readall())).convert("RGBA") as image,
        Image.new('RGBA', image.size) as rectsImage
    ):
        draw = ImageDraw.Draw(rectsImage)
        for region in regions:
            rect = list(map(int, region.split(",")))
            draw.rectangle(rect, "#ffff004b", "#ffff004b", 3)
        Image.alpha_composite(image, rectsImage).save(imgOut, "PNG")

def handler(doc):
    for part in doc.partsModify():
        if part.isFilePart():
            #region field format "left,top,right,bottom" (e.g. "100,100,200,200" square at (100,100))
            regions = part.getPartXmlMetadata().getValuesByXPath(".//regions/region")
            with part.transformFile() as (imgIn, imgOut):
                updateImage(imgIn, regions, imgOut)