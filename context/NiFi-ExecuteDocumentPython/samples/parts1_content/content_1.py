"""{
    "name": "Reading all content text pages (simplified)"
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

from idolnifi import *

def handler(doc):
    #Begin reading content parts
    for part in filter(DocumentAction.isContentPart, doc.partsRead()):
        
        #Get all content for the current part as a list of page strings
        partContent = part.getContent()