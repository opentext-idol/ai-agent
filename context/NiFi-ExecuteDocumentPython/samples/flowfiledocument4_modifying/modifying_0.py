"""{
    "name": "Using the DocumentModifier class"
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

from idolnifi import DocumentModifier, DocumentAction, ContentAction, FileAction

#Actions to perform first
def myPreAction(a: DocumentAction):
    pass

#Actions to perform for each text content page in the FlowFileDocument
def myContentAction(a: ContentAction):
    pass

#This is the default action called for all file part types in the FlowFileDocument
#The behaviour can be overridden for each by assigning the other methods on the DocumentModifier
#Each method takes an appropriate action argument type based on the method name
def myDefaultFileAction(a: FileAction):
    pass

#Actions to perform last
def myPostAction(a: DocumentAction):
    pass

def handler(doc):
    doc.modify(DocumentModifier()
        .preAction(myPreAction)
        .onContent(myContentAction)
        .defaultFileAction(myDefaultFileAction)
        .postAction(myPostAction))