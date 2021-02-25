# -*- coding: utf-8 -*-

import os
from os import path as osp
import requests
from pygments.formatters import get_formatter_by_name

ABSPATH = os.path.dirname( os.path.abspath( __file__) )
resources_path =  osp.join( ABSPATH , "resources")
vendor_path = osp.join( resources_path, "vendor")

vendors = [
	"bootstrap",
	"d3",
	"fonts",
	"jquery",
	"material",
	"paho-mqtt",
	"pygment"
]

resources = [
	{ "from":"https://stackpath.bootstrapcdn.com/bootstrap/4.3.1/css/bootstrap.min.css", "to":"bootstrap/bootstrap-4.3.1.min.css", "typ":"text" },
	{ "from":"https://stackpath.bootstrapcdn.com/bootstrap/4.3.1/js/bootstrap.bundle.min.js", "to":"bootstrap/bootstrap-4.3.1.bundle.min.js", "typ":"text" },
	{ "from":"https://cdnjs.cloudflare.com/ajax/libs/bootstrap3-dialog/1.33.4/css/bootstrap-dialog.min.css", "to":"bootstrap/bootstrap-dialog-1.33.4.min.css", "typ":"text" },
	{ "from":"https://cdnjs.cloudflare.com/ajax/libs/bootstrap3-dialog/1.33.4/js/bootstrap-dialog.min.js", "to":"bootstrap/bootstrap-dialog-1.33.4.min.js", "typ":"text" },
    
    { "from":"https://cdnjs.cloudflare.com/ajax/libs/d3/5.7.0/d3.min.js", "to":"d3/d3-5.7.0.min.js", "typ":"text" },

	{ "from":"https://code.jquery.com/jquery-3.5.1.min.js", "to":"jquery/jquery-3.5.1.min.js", "typ":"text" },
    
	{ "from":"https://cdnjs.cloudflare.com/ajax/libs/paho-mqtt/1.1.0/paho-mqtt.min.js", "to":"paho-mqtt/paho-mqtt-1.1.0.min.js", "typ":"text" },

    { "from":"https://cdnjs.cloudflare.com/ajax/libs/MaterialDesign-Webfont/5.8.55/css/materialdesignicons.min.css", "to":"material/materialdesignicons.min.css", "typ":"text" },
     
    { "from":"https://cdnjs.cloudflare.com/ajax/libs/MaterialDesign-Webfont/5.8.55/fonts/materialdesignicons-webfont.eot", "to":"fonts/materialdesignicons-webfont.eot", "typ":"bin" },
    { "from":"https://cdnjs.cloudflare.com/ajax/libs/MaterialDesign-Webfont/5.8.55/fonts/materialdesignicons-webfont.ttf", "to":"fonts/materialdesignicons-webfont.ttf", "typ":"bin" },
    { "from":"https://cdnjs.cloudflare.com/ajax/libs/MaterialDesign-Webfont/5.8.55/fonts/materialdesignicons-webfont.woff", "to":"fonts/materialdesignicons-webfont.woff", "typ":"bin" },
    { "from":"https://cdnjs.cloudflare.com/ajax/libs/MaterialDesign-Webfont/5.8.55/fonts/materialdesignicons-webfont.woff2", "to":"fonts/materialdesignicons-webfont.woff2", "typ":"bin" },


]

pygments = {"class": "codehilite", "to":"pygment/codehilite.css"}
materialize = {"from":"https://cdnjs.cloudflare.com/ajax/libs/materialize/1.0.0/css/materialize.css", "to":"material/materialize-colors.css", "typ":"text", "before":"/*! normalize.css" }

#
# start copy resources
#

print("create vendor path", vendor_path)

errors = 0
if not os.path.exists( vendor_path ):
    try:
        os.makedirs( vendor_path )
    except IOError as e:
        errors += 1
        print("Unable to create dir.", e)

# create all vendor paths
for vendor in vendors:
	if not os.path.exists( osp.join(vendor_path, vendor) ):
		try:
			os.makedirs( osp.join(vendor_path, vendor) )
		except IOError as e:
			print("Unable to create dir.", e)

for resource in resources:
    print("loading:", resource["from"])
    resource_to =  osp.join( vendor_path, resource["to"] )
    response = requests.get( resource["from"] )
    if resource["typ"] == "text":
        try:
            with open(resource_to, "w") as f:
                f.write(response.text)
        except IOError as e:
            print("Unable to create file.", e)
    elif resource["typ"] == "bin":
        try:
            with open(resource_to, "wb") as f:
                f.write(response.content)
        except IOError as e:
            print("Unable to create file.", e)

#    
# get colors from materialize
#
print("get named-colors from materialize:", materialize["from"])
response = requests.get( materialize["from"] )
# 
pos = response.text.find( materialize["before"] )
# print( response.text[ : pos ] )
try:
    pos = response.text.find( materialize["before"] )
    with open(osp.join(vendor_path, materialize["to"]), "w") as f:
        f.write(response.text[ : pos ] )
except IOError as e:
    print("Unable to create file.", e)

#    
# create pygments css rules for codehilite    
#
print("create pygments/codehilite.css with pygments")
fmter = get_formatter_by_name("html", style="default")
css_content = fmter.get_style_defs( ".{}".format(pygments["class"]) )
try:
    with open( osp.join(vendor_path, pygments["to"]), "w") as f:   
        f.write(css_content)
except IOError as e:
    print("Unable to create file.", e)

#
# print result 
#
if errors > 0:
    print( "Installation error." )
    
else:
    print('''
    Run as sudo to copy materialdesignicons_webfont to your system fonts:
    
> sudo cp ./resources/vendor/fonts/materialdesignicons-webfont.ttf /usr/share/fonts/truetype/materialdesignicons_webfont.ttf
> sudo chmod 644 /usr/share/fonts/truetype/materialdesignicons_webfont.ttf
''')

