"""{
    "name": "Basic handler function",
    "info": "Basic example of a handler function with ProcessContext, ProcessSession and FlowFile arguments"
}"""
#@ PythonScriptFunction=handler

from idolnifi import *

def handler(context, session, flowfile):

    #Log processor information
    logInfo(context.getName())

    #Create a new flowfile and set an attribute
    newflowfile = session.create()
    newflowfile = session.putAttribute(newflowfile, "an_attribute", "value")
    
    #Manipulate the new empty flowfile as a FlowFileDocument
    doc = session.asFlowFileDocument(newflowfile)
    with doc.overwriting() as action:
        action.addContent('some text content')

    # Transfer created flowfile explicitly
    session.transfer(newflowfile, "success")
    
    # FlowFiles that are not transferred will be routed based on configured properties
    
    # Return the input flowfile
    return flowfile