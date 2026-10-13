"""{
    "name": "Using FlowFileDocument.appending()"
}"""

from idolnifi import DocMod, DocumentAction

def handler(doc):
    #Begin appending to the FlowFileDocument
    with doc.appending() as action:

        #Perform any pre-operations using action (DocumentAction)
        myAttr = action.getAttribute("my_attr")

        #Iterate over the parts to append any replacement or new parts
        for part in action.parts():
            if part.isContentPart():
                logInfo("Content part", part.getPartId())
            #elif part.isXXX():

        #Perform any post-operations using action (DocumentAction)
        action.setAttribute("my_attr", myAttr)