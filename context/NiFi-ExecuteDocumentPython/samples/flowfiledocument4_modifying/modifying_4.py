"""{
    "name": "Using FlowFileDocument.partsModify()"
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
    #Use partsModify() to access the parts in an implicit modifying context
    for part in doc.partsModify():

        #Test the type of the current part
        if part.isContentPart():
            logInfo("Content part", part.getPartId())
        elif part.isFilePart():
            logInfo("File (" + type(part).__name__ + ") part " + part.getPartId())
        # Modify any of the parts or the document