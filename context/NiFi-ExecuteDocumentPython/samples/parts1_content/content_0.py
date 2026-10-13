"""{
    "name": "Reading all content text pages (verbose)"
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
    #Begin reading
    with doc.reading() as action:

        #Iterate parts
        for part in action.parts():
            
            #Test if part is content text
            if part.isContentPart():

                #Get the content stream for the current part
                with part.readContent() as inputstream:

                    #Read all content as a list of page strings
                    partContent = inputstream.readall().split(PageSeparator)