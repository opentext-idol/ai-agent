"""{
    "name": "Using the DocMod class with dict"
}"""

from idolnifi import DocMod, DocumentAction

class MyDocModWithDict(DocMod):
    #Additional state is initialized via the super class dict initializer

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
    #Use a DocMod class instance with dictionary state
    doc.modify(MyDocModWithDict({"handlerState": "handlerstatedata"}))