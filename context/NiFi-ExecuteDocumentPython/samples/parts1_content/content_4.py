"""{
    "name": "Transforming content text pages"
}"""

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
