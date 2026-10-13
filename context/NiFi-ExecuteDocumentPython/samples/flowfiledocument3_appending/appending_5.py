"""{
    "name": "Using FlowFileDocument.appending()"
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