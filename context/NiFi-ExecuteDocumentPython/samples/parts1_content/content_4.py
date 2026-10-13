"""{
    "name": "Transforming content text pages"
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
    #Begin writing
    with doc.modifying() as action:

        #Iterate parts
        for part in action.parts():

            #Test if part is content text
            if part.isContentPart():

                #Get the read and write streams for the current part
                with part.transformContent() as (inputstream,outputstream):

                    #Example to reverse the page ordering in the part
                    pages = inputstream.readall().split(PageSeparator)
                    outputstream.write(PageSeparator.join(pages[::-1]))
