"""{
    "name": "Using FlowFileDocument.partsAppend()"
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
    #Use partsAppend() to access the parts in an implicit appending context
    for part in doc.partsAppend():

        #Test the type of the current part
        if part.isContentPart():
            logInfo("Content part", part.getPartId())
        elif part.isFilePart():
            logInfo("File (" + type(part).__name__ + ") part " + part.getPartId())
        # append new or replacement parts to the document