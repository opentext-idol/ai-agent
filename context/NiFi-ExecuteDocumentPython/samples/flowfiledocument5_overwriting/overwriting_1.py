"""{
    "name": "Using a single callable with DocumentAction"
}"""

from idolnifi import DocumentModifier, DocumentAction

def myDocumentAction(a: DocumentAction):
    #Use DocumentAction to read metadata and write files and metadata to the FlowFileDocument
    pass

def handler(doc):
    #Direct call to myDocumentAction as a postAction
    doc.overwrite(myDocumentAction)

    #Using a DocumentModifier explicitly with a postAction
    #This can be combined with additional DocumentModifier methods for access to existing parts
    doc.overwrite(DocumentModifier()
        .postAction(myDocumentAction))