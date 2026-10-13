"""{
    "name": "Using a single callable with DocumentAction"
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

from idolnifi import DocumentModifier, DocumentAction

def myDocumentAction(a: DocumentAction):
    #Use DocumentAction to read metadata and write files and metadata to the FlowFileDocument
    pass

def handler(doc):
    #Direct call to myDocumentAction as a postAction
    doc.read(myDocumentAction)

    #Using a DocumentModifier explicitly with a postAction
    #This can be combined with additional DocumentModifier methods for access to existing parts
    doc.read(DocumentModifier()
        .postAction(myDocumentAction))