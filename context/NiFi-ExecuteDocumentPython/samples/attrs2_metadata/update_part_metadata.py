"""{
    "name": "Update document part metadata",
    "info": "Update the XML metadata from a FlowFileDocument part"
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