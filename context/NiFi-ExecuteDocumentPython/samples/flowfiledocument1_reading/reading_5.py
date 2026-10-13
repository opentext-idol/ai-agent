"""{
    "name": "Using FlowFileDocument.reading()"
}"""

def handler(doc):
    #Begin reading the FlowFileDocument
    with doc.reading() as action:

        #Perform any read operations using action (DocumentAction)
        myAttr = action.getAttribute("my_attr")

        #Iterate over the parts to read the parts
        for part in action.parts():
            if part.isContentPart():
                logInfo("Content part", part.getPartId())
            #elif part.isXXX():