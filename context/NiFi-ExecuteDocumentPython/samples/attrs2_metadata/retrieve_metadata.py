"""{
    "name": "Retrieve document metadata",
    "info": "Retrieve XML metadata values from a FlowFileDocument"
}"""
    
def handler(doc):
    #Begin reading
    with doc.reading() as action:

        #Get the root metadata element
        xml = action.getXmlMetadata()

        #Retrieve a single existing value
        value = xml.getFirstChild("EXISTING_FIELD").getValue()

        #Retrieve values for elements matching an XPath
        elements = xml.getElementsByXPath("FIELD1/FIELD2")
        for element in elements:
            value = element.getValue()

        #Retrieve value list directly by XPath
        attrValues = xml.getValuesByXPath("FIELD1/FIELD2/@ATTR")