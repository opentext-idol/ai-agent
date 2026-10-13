"""{
    "name": "Update document part metadata",
    "info": "Update the XML metadata from a FlowFileDocument part"
}"""

def handler(doc):
    #Begin updating
    with doc.updatingAttributes() as action:

        #Iterate parts
        for part in action.parts():
            
            #Get the part metadata element
            xml = part.getPartXmlMetadata()

            #Add a new field with a value
            xml.addChild("NEW_FIELD").setValue("NEW_VALUE")

            #Replace the first existing field or add a new field
            xml.getOrAddChild("MAYBE_EXISTING_FIELD").setValue("NEW_VALUE")