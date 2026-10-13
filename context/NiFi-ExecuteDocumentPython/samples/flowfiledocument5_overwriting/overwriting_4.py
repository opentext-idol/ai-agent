"""{
    "name": "Using FlowFileDocument.partsOverwrite()"
}"""

def handler(doc):
    #Use partsOverwrite() to access the parts in an implicit overwriting context
    for part in doc.partsOverwrite():

        #Test the type of the current part
        if part.isContentPart():
            logInfo("Content part", part.getPartId())
        elif part.isFilePart():
            logInfo("File (" + type(part).__name__ + ") part " + part.getPartId())
        # Write all the new parts to the document