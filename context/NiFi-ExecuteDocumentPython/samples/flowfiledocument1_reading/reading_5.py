"""{
    "name": "Using FlowFileDocument.reading()"
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
    #Begin reading the FlowFileDocument
    with doc.reading() as action:

        #Perform any read operations using action (DocumentAction)
        myAttr = action.getAttribute("my_attr")

        #Iterate over the parts to read the parts
        for part in action.parts():
            if part.isContentPart():
                logInfo("Content part", part.getPartId())
            #elif part.isXXX():