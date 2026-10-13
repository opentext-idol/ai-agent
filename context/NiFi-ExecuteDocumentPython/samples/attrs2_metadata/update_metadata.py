"""{
    "name": "Update document metadata",
    "info": "Update the XML metadata from a FlowFileDocument"
}"""

def handler(doc):
    #Begin updating
    with doc.updatingAttributes() as action:

        #Get the root metadata element
        xml = action.getXmlMetadata()

        #Add a new field with a value
        xml.addChild("NEW_FIELD").setValue("NEW_VALUE")

        #Replace the first existing field or add a new field
        xml.getOrAddChild("MAYBE_EXISTING_FIELD").setValue("NEW_VALUE")