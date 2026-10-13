"""{
    "name": "Install required packages",
    "info": "Install packages required by the script when the processor is scheduled to run"
}"""

from idolnifi import installPackage,PersistentPackageDirectory

#Executed when the processor is scheduled to run
#Install to the pre-defined PersistentPackageDirectory instead of the default package directory
installPackage('numpy', packageDirectory=PersistentPackageDirectory)

#Installation can also be performed using the Packages tab in the Advanced processor configuration
#This can install to the PersistentPackageDirectory making manual installation as above unnecessary

import numpy

def handler():
    #Do something using the packages
    pass