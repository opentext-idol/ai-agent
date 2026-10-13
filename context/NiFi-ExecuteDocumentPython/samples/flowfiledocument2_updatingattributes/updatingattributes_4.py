"""{
    "name": "Using FlowFileDocument.partsUpdateAttributes()"
}"""

def handler(doc):
    #Use partsUpdateAttributes() to access the parts in an implicit updating attributes context
    for part in doc.partsUpdateAttributes():

        #Test the type of the current part
        if part.isContentPart():
            logInfo("Content part", part.getPartId())
        elif part.isFilePart():
            logInfo("File (" + type(part).__name__ + ") part " + part.getPartId())
        # Update attributes or metadata for any of the parts or the document