"""{
    "name": "Reading all content text pages (verbose)"
}"""

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