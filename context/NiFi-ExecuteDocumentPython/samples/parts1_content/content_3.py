"""{
    "name": "Adding content text pages"
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
        
        #Add a part containing two pages
        action.addContent(["First content page", "Second content page"])
        
        #Add a second part containing text from a file
        with open("mycontent.txt", "r") as textContentFromInputStream:
            action.addContent(textContentFromInputStream)
            
        #Add another part containing two pages
        with action.addContent() as outputstream:
            outputstream.write("First content page")
            outputstream.write(PageSeparator)
            outputstream.write("Second content page")
