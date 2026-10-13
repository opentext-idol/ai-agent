"""{
    "name": "Using the DocMod class with init"
}"""

from idolnifi import DocMod, DocumentAction

class MyDocModWithInit(DocMod):
    #Initialize any state for the class instance with an explicit initializer
    def __init__(self, state = None):
        super().__init__()
        self.handlerState = state

    #Pre action to perform
    def preAction(self, a: DocumentAction):
        #Assign additional state resulting from actions
        self.state = "statedata"

    #Other similarly named methods to those in DocumentModifier can be defined

    #Post action to perform
    def postAction(self, a: DocumentAction):
        #use self.handlerState
        #use self.state
        pass

def handler(doc):
    #Use a DocMod class instance to store temporary state 
    doc.updateAttributes(MyDocModWithInit("handlerstatedata"))