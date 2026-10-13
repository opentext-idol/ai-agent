"""{
    "name": "Using FlowFileDocument.updatingAttributes()"
}"""

from idolnifi import DocMod, DocumentAction

def handler(doc):
    #Begin updating attributes for the FlowFileDocument
    with doc.updatingAttributes() as action:

        #Perform any pre-operations using action (DocumentAction)
        myAttr = action.getAttribute("my_attr")

        #Iterate over the parts to perform any attribute or metadata updates
        for part in action.parts():
            if part.isContentPart():
                logInfo("Content part", part.getPartId())
            #elif part.isXXX():

        #Perform any post-operations using action (DocumentAction)
        action.setAttribute("my_attr", myAttr)