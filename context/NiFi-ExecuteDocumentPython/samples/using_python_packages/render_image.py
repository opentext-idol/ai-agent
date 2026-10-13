"""{
    "name": "Render an image",
    "info": "Render an image from calculated image data and add it to a FlowFileDocument"
}"""

from idolnifi import *

#installPackage('matplotlib', 'numpy')

import numpy as np
import matplotlib.pyplot as plt

def mandelbrot(h, w, maxit=20, r=2):
    x = np.linspace(-2.5, 1.5, 4*h+1)
    y = np.linspace(-1.5, 1.5, 3*w+1)
    A, B = np.meshgrid(x, y)
    C = A + B*1j
    z = np.zeros_like(C)
    divtime = maxit + np.zeros(z.shape, dtype=int)
    for i in range(maxit):
        z = z**2 + C
        diverge = abs(z) > r
        div_now = diverge & (divtime == maxit)
        divtime[div_now] = i
        z[diverge] = r
    return divtime

def handler(doc):
    with doc.modifying() as action:
        with action.addFile(displayName='mandelbrot.png', mimeType='image/png') as outImg:
            plt.clf()
            plt.imsave(outImg, mandelbrot(720, 720, 50))