# -*- coding: utf-8 -*-

"""

* https://cdnjs.com/libraries
* https://unpkg.com/#/
"""

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
	"pygment",
	"ace",
    "moment",
    "w2ui",
    "jquery.fancytree",
    "jquery.fancytree/skin-lion",
    "jquery.fancytree/skin-themeroller",
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

	# ace
	{ "from":"https://cdnjs.cloudflare.com/ajax/libs/ace/1.4.12/ace.min.js", "to":"ace/ace-1.4.12.min.js", "typ":"text" },
	{ "from":"https://cdnjs.cloudflare.com/ajax/libs/ace/1.4.12/mode-text.min.js", "to":"ace/mode-text.js", "typ":"text" },
	{ "from":"https://cdnjs.cloudflare.com/ajax/libs/ace/1.4.12/mode-json.min.js", "to":"ace/mode-json.js", "typ":"text" },
	{ "from":"https://cdnjs.cloudflare.com/ajax/libs/ace/1.4.12/worker-json.min.js", "to":"ace/worker-json.js", "typ":"text" },
	{ "from":"https://cdnjs.cloudflare.com/ajax/libs/ace/1.4.12/mode-markdown.min.js", "to":"ace/mode-markdown.js", "typ":"text" },
	{ "from":"https://cdnjs.cloudflare.com/ajax/libs/ace/1.4.12/theme-twilight.min.js", "to":"ace/theme-twilight.js", "typ":"text" },
	{ "from":"https://cdnjs.cloudflare.com/ajax/libs/ace/1.4.12/ext-beautify.min.js", "to":"ace/ext-beautify.min.js", "typ":"text" },
	   
    # moment
    { "from":"https://cdnjs.cloudflare.com/ajax/libs/moment.js/2.29.1/moment-with-locales.min.js", "to":"moment/moment-2.29.1.min.js", "typ":"text" },

    # w2ui - 777ac78c6a49593ac93c37ca72336b19bfad70f2
    
    { "from":"https://raw.githubusercontent.com/vitmalina/w2ui/777ac78c6a49593ac93c37ca72336b19bfad70f2/dist/w2ui.min.js", "to":"w2ui/w2ui-777ac78.min.js", "typ":"text" },
    { "from":"https://raw.githubusercontent.com/vitmalina/w2ui/777ac78c6a49593ac93c37ca72336b19bfad70f2/dist/w2ui.min.css", "to":"w2ui/w2ui-777ac78.min.css", "typ":"text" },

    # w2ui 2.0
    { "from":"https://raw.githubusercontent.com/vitmalina/w2ui/master/dist/w2ui.js", "to":"w2ui/w2ui-2.0.js", "typ":"text" },
    { "from":"https://raw.githubusercontent.com/vitmalina/w2ui/master/dist/w2ui.css", "to":"w2ui/w2ui-2.0.css", "typ":"text" },    
    
    
    # fancytree
    { "from":"https://cdnjs.cloudflare.com/ajax/libs/jquery.fancytree/2.38.0/jquery.fancytree-all-deps.min.js", "to":"jquery.fancytree/fancytree-all-deps-2.38.0.min.js", "typ":"text" },  
    # fancytree - themeroller
    { "from":"https://cdnjs.cloudflare.com/ajax/libs/jquery.fancytree/2.38.0/skin-themeroller/ui.fancytree.min.css", "to":"jquery.fancytree/skin-themeroller/ui.fancytree-2.38.0.min.css", "typ":"text" },   
    { "from":"https://cdnjs.cloudflare.com/ajax/libs/jquery.fancytree/2.38.0/skin-themeroller/icons.gif", "to":"jquery.fancytree/skin-themeroller/icons.gif", "typ":"bin" }, 
    { "from":"https://cdnjs.cloudflare.com/ajax/libs/jquery.fancytree/2.38.0/skin-themeroller/vline.gif", "to":"jquery.fancytree/skin-themeroller/vline.gif", "typ":"bin" }, 
    { "from":"https://cdnjs.cloudflare.com/ajax/libs/jquery.fancytree/2.38.0/skin-themeroller/loading.gif", "to":"jquery.fancytree/skin-themeroller/loading.gif", "typ":"bin" }, 
    # fancytree - skin-lion
    { "from":"https://cdnjs.cloudflare.com/ajax/libs/jquery.fancytree/2.38.0/skin-lion/ui.fancytree.min.css", "to":"jquery.fancytree/skin-lion/ui.fancytree-2.38.0.min.css", "typ":"text" }, 
    { "from":"https://cdnjs.cloudflare.com/ajax/libs/jquery.fancytree/2.38.0/skin-lion/icons.gif", "to":"jquery.fancytree/skin-lion/icons.gif", "typ":"bin" }, 
    { "from":"https://cdnjs.cloudflare.com/ajax/libs/jquery.fancytree/2.38.0/skin-lion/vline.gif", "to":"jquery.fancytree/skin-lion/vline.gif", "typ":"bin" }, 
    { "from":"https://cdnjs.cloudflare.com/ajax/libs/jquery.fancytree/2.38.0/skin-lion/loading.gif", "to":"jquery.fancytree/skin-lion/loading.gif", "typ":"bin" }, 

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

''' 
..TODO:: material-color to vendor/material/
 
    https://github.com/mrmlnc/material-color
'''
 
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

