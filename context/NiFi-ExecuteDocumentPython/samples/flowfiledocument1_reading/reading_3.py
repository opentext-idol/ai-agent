"""{
    "name": "Using the DocMod class with dict"
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
    doc.read(MyDocModWithDict({"handlerState": "handlerstatedata"}))