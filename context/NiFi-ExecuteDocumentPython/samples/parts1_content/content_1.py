"""{
    "name": "Reading all content text pages (simplified)"
}"""

from idolnifi import *

def handler(doc):
    #Begin reading content parts
    for part in filter(DocumentAction.isContentPart, doc.partsRead()):
        
        #Get all content for the current part as a list of page strings
        partContent = part.getContent()