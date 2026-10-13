"""{
    "name": "Retrieve document part metadata",
    "info": "Retrieve XML metadata values from a FlowFileDocument part"
}"""

# BEGIN COPYRIGHT NOTICE
# Copyright 2026 Open Text.
#
# The only warranties for products and services of Open Text and its affiliates and licensors
# ("Open Text") are as may be set forth in the express warranty statements accompanying such
# products and services. Nothing herein should be construed as constituting an additional warranty.
# Open Text shall not be liable for technical or editorial errors or omissions contained herein.
# The information contained herein is subject to change without notice.
#
# END COPYRIGHT NOTICE

    
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