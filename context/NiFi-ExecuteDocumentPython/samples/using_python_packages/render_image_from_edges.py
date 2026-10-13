"""{
    "name": "Detect edges from images in a FlowFileDocument",
    "info": "Detect the edges in images attached to a FlowFileDocument and add new images showing the edges"
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

#installPackage('matplotlib', 'numpy', 'opencv-python')

import numpy as np
import cv2 as cv
from matplotlib import pyplot as plt

def processFile(part):
    edges = None
    with part.readFile(readMode = ReadMode.READ_AND_KEEP) as imgIn:
        filebytes = np.asarray(bytearray(imgIn.readall()), dtype=np.uint8)
        edges = cv.Canny(cv.imdecode(filebytes, cv.IMREAD_GRAYSCALE), 100, 200)
    with part.addFile(displayName='edges.png', mimeType='image/png') as imgOut:
        plt.clf()
        plt.imsave(imgOut, edges, cmap='gray')
    
def handler(doc):
    for part in doc.partsModify():
        if part.isFilePart():
            processFile(part)
