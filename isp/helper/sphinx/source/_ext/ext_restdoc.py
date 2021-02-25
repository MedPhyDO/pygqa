# -*- coding: utf-8 -*-

'''
ext_restdoc
===========

Erweiterung um mit .. restdoc:: markierte Swagger API Bereiche seperat zu rendern 

'''

__author__ = "R. Bauer"
__copyright__ = "MedPhyDO - Machbarkeitsstudien im Rahmen von Bachelor und Masterarbeiten an der TU-Dortmund / FH-Dortmund und Klinikum Dortmund"
__credits__ = ["R. Bauer", "K.Loot"]
__license__ = "MIT"
__version__ = "0.0.1"
__status__ = "Prototype"

# https://sphinxext-survey.readthedocs.io

from sphinx.application import Sphinx
from typing import Any, Dict

from sphinx.ext.autodoc import MethodDocumenter, ClassDocumenter
  
def setup(app: Sphinx) -> Dict[str, Any]:
    
    app.add_autodocumenter( RestDocMethodDocumenter )
    app.add_autodocumenter( RestDocClassDocumenter )
    
    return {
        'version': '0.1',
        'parallel_read_safe': True
    }


class restdocConverter():
    
    def results_convert(self, results:list=[]): 
        for result in results:
            if isinstance(result, list) and ".. restdoc::" in result[0]:
                restconvert = []
                restconvert.append( self.restdoc_convert( result[1:] ) )
                results = restconvert
        return results
    
    def restdoc_convert(self, data):
        result = []
        restdoc = ["", "Swagger API::", ""]   
        # der erste ist .. restdoc::
        end_marker = False
        for line in data:
            if line == "----":
                end_marker = True
            else:
                # alles nach dem Endmarker ist normaler Inhalt
                if end_marker:
                    result.append( "{}".format(line) )
                    
                else:
                    restdoc.append( "    {}".format(line) )
        # als letztes restdoc hinzufügen
        result.extend( restdoc )
        return result
    
class RestDocClassDocumenter(ClassDocumenter, restdocConverter):
  
    def get_doc(self, *args, **kwargs):
        results = super().get_doc(*args, **kwargs) 
        if results:
            results = self.results_convert( results )
        return results
        

class RestDocMethodDocumenter(MethodDocumenter, restdocConverter):
    
   def get_doc(self, *args, **kwargs):
        results = super().get_doc(*args, **kwargs)
        if results:
            results = self.results_convert( results )
        return results
        