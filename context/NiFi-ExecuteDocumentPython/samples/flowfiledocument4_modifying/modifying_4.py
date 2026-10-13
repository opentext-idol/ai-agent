"""{
    "name": "Using FlowFileDocument.partsModify()"
}"""

def handler(doc):
    #Use partsModify() to access the parts in an implicit modifying context
    for part in doc.partsModify():

        #Test the type of the current part
        if part.isContentPart():
            logInfo("Content part", part.getPartId())
        elif part.isFilePart():
            logInfo("File (" + type(part).__name__ + ") part " + part.getPartId())
        # Modify any of the parts or the document