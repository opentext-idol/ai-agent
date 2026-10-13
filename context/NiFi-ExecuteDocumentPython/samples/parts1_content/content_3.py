"""{
    "name": "Adding content text pages"
}"""

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
