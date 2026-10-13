"""{
    "name": "Reading all content text pages (without part iteration)"
}"""

from idolnifi import *

def handler(doc):
    #Get all content pages across all parts
    for content in doc.getContentPages():

        # Use content string
        pass