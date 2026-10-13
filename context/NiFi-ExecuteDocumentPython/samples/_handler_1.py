"""{
    "name": "Basic handler function",
    "info": "Basic example of a handler function with ProcessContext, ProcessSession and FlowFile arguments"
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