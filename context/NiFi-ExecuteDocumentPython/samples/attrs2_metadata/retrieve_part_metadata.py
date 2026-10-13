"""{
    "name": "Retrieve document part metadata",
    "info": "Retrieve XML metadata values from a FlowFileDocument part"
}"""
    
def handler(doc):
    #Begin reading
    with doc.reading() as action:

        #Iterate parts
        for part in action.parts():
            
            #Get the part metadata element
            xml = part.getPartXmlMetadata()

            #Retrieve a single existing value
            value = xml.getFirstChild("EXISTING_FIELD").getValue()

            #Retrieve values for elements matching an XPath
            elements = xml.getElementsByXPath("FIELD1/FIELD2")
            for element in elements:
                value = element.getValue()

            #Retrieve value list directly by XPath
            attrValues = xml.getValuesByXPath("FIELD1/FIELD2/@ATTR")