"""{
    "name": "Using FlowFileDocument.partsAppend()"
}"""

def handler(doc):
    #Use partsAppend() to access the parts in an implicit appending context
    for part in doc.partsAppend():

        #Test the type of the current part
        if part.isContentPart():
            logInfo("Content part", part.getPartId())
        elif part.isFilePart():
            logInfo("File (" + type(part).__name__ + ") part " + part.getPartId())
        # append new or replacement parts to the document