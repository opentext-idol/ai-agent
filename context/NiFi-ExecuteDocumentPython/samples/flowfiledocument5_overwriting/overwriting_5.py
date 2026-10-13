"""{
    "name": "Using FlowFileDocument.overwriting()"
}"""

from idolnifi import DocMod, DocumentAction

def handler(doc):
    #Begin overwriting the FlowFileDocument
    with doc.overwriting() as action:

        #Perform any pre-operations using action (DocumentAction)
        myAttr = action.getAttribute("my_attr")

        #Iterate over the parts to read before fully overwriting with new parts
        for part in action.parts():
            if part.isContentPart():
                logInfo("Content part", part.getPartId())
            #elif part.isXXX():

        #Perform any post-operations using action (DocumentAction)
        action.setAttribute("my_attr", myAttr)