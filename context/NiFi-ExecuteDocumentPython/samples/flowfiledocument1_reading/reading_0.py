"""{
    "name": "Using the DocumentModifier class"
}"""

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
    doc.read(DocumentModifier()
        .preAction(myPreAction)
        .onContent(myContentAction)
        .defaultFileAction(myDefaultFileAction)
        .postAction(myPostAction))