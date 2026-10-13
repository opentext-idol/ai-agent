"""{
    "name": "Using FlowFileDocument.modifying()"
}"""

def handler(doc):
    #Begin modifying the FlowFileDocument
    with doc.modifying() as action:

        #Perform any pre-operations using action (DocumentAction)
        myAttr = action.getAttribute("my_attr")

        #Iterate over the parts to perform any modifications
        for part in action.parts():
            if part.isContentPart():
                logInfo("Content part", part.getPartId())
            #elif part.isXXX():

        #Perform any post-operations using action (DocumentAction)
        action.setAttribute("my_attr", myAttr)