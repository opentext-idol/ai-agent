"""{
    "name": "Using FlowFileDocument.partsRead()"
}"""

def handler(doc):
    #Use partsRead() to access the parts in an implicit reading context
    for part in doc.partsRead():

        #Test the type of the current part
        if part.isContentPart():
            logInfo("Content part", part.getPartId())
        elif part.isFilePart():
            logInfo("File (" + type(part).__name__ + ") part " + part.getPartId())
        # Read any of the parts or the document