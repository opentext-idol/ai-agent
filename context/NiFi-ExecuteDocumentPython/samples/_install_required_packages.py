"""{
    "name": "Install required packages",
    "info": "Install packages required by the script when the processor is scheduled to run"
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