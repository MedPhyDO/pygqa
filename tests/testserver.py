# -*- coding: utf-8 -*-
"""
Webserver für api testaufrufe

"""

import sys
import argparse
import site 
import json
import os
from os import path as osp

# Module von hier erreichbar machen 
ABSPATH = osp.dirname( osp.abspath( __file__) )
BASEPATH = osp.abspath(osp.join( ABSPATH , ".."))
FILESPATH = osp.abspath(osp.join( BASEPATH, 'data', 'unittest'))

path = osp.join( ABSPATH , "..")
sys.path.insert(0, path)

site.addsitedir(BASEPATH)

from sqlalchemy import MetaData
from safrs import jsonapi_rpc
from flask import Response 

from testdb import dbtests
from testdummy import dummy

from app.api import gqa

from isp.config import ispConfig
from isp.webapp import ispBaseWebApp
  
from isp.safrs import ispSAFRSDummy

from app import run


if not os.path.exists( FILESPATH ):
    os.mkdir( FILESPATH )

results_path = osp.join( FILESPATH, "results" )
if not os.path.exists( results_path ):
    os.mkdir( results_path )

check_path = os.path.join( FILESPATH, 'check')
if not os.path.exists( check_path ):
    os.mkdir( check_path )
    
dicom_path = osp.abspath(osp.join( FILESPATH, "..", "DICOM" ))
if not os.path.exists( dicom_path ):
    os.mkdir( dicom_path )


config =  {
    "server" : {
        "webserver" : {
            "name" : "app_test",
            "port" : 5001,
            "reloader" : False
        },
        "logging" : { 
            "safrs" :  10,
            "sqlalchemy" :10,
            "webapp" : 10
        },
    },
    "database": {
        "servername" : "VMSCOM",
        "main": "pygqa",
        "pygqa" : {
            "name" : "pygqa_unittest.json"
        }
    },
    "dicom": {
        "servername" : "VMSCOM",
        "VMSCOM" : {
            "local_dir" : dicom_path
        }
    },
    "resultsPath" : results_path,
    "version": "unittest",
    "variables" : {
        "Datenausgabe" : "unittest"
    }

}

class unittest( gqa ):
    """
        description: zusätzliche Zugriffe für den testserver
        ---
        
    """
    __tablename__ = "unittest"
    _database_key = ""
        
    config = None
    
    metadata = MetaData()
    
    
    @jsonapi_rpc( http_methods=['GET'] )
    def api_list(cls, **kwargs):
        """
            summary : alle Angaben
            description: alle Angaben
            parameters:
                - name : _ispcp
                  type: OrderedMap
                  in : query
                  default : {}
                  description : zusätzliche parameter
        ----
        """

        # letzte config laden
        _kwargs = cls.init( kwargs )

        cls.appInfo("kwargs", _kwargs )  

        subfolders = [ f.name for f in os.scandir(cls.config.resultsPath) if f.is_dir() ]
        units = {key: value for (key, value) in cls.config.get( "units", {} ).items() if value }
        
        unittestResults = {}
        with open(osp.join(results_path, "unittestResults.json"), "r" ) as json_file:
            unittestResults = json.load( json_file )

        result = {
            "version" :cls.config.version,
            "resultsPath" :cls.config.resultsPath,
            "units": units,
            "years": subfolders,
            "firstYear" : cls.config.get("firstYear", 2017),
            "calledTests" : unittestResults["calledTests"]
        }

        cls.appInfo("unittest", result, area="config" )  
        
        return cls._int_json_response( {"data": unittestResults["calledTestsResults"] } )   

    @classmethod
    @jsonapi_rpc( http_methods=['GET'] )
    def pdf( cls, **kwargs ):
        '''
        description: test von pdf Funktionen und Parametern
        parameters:
            - name : file
              in : query
              required : false
              description : Anzuzeigendes pdf ab result/
        '''
        _kwargs = cls.init( kwargs )

        cls.appInfo("kwargs", _kwargs )

        mimetype='text/html'
        status = 200 
        if not _kwargs["file"] :
            status=400
            result = "No File parameter"
            cls.appError( "gqa/pdf", result)
            return cls._int_json_response(  )   
        
        result = ""
        _file = osp.join(cls.config.resultsPath, _kwargs["file"])
        if osp.isfile( _file ):
            result = ""
            with open(_file, 'rb') as static_file:
                result = static_file.read()
                mimetype='application/pdf'
            if result == "":
                status=400
                result = "Error Open File {}".format( _file )
                cls.appError( "gqa/pdf", result )
        else:
            status=400
            result = "No File found {}".format( _file )
            cls.appError( "gqa/pdf", result)

        return Response(result, status=status, mimetype=mimetype)
    
    @classmethod
    @jsonapi_rpc( http_methods=['GET'] )
    def image( cls, **kwargs ):
        '''
        description: holt das zum pdf passende image
        parameters:
            - name : file
              in : query
              required : false
              description : Anzuzeigendes image ab result/
        '''
        _kwargs = cls.init( kwargs )
        
        mimetype='text/html'
        status=200
        if not _kwargs["file"] :
            status=400
            result = "No File parameter"
            cls.appError( "gqa/image", result)
            return cls._int_json_response(   )  
        
        result = "" 
        _file = osp.join(cls.config.resultsPath, _kwargs["file"])
        
        if osp.isfile( _file ):
            result = ""
            with open(_file, 'rb') as static_file:
                result = static_file.read()
                mimetype='image/png'
            if result == "":
                status=400
                result = "Error Open File {}".format( _file )
                cls.appError( "gqa/pdf", result )
        else:
            status=400
            result = "No File found {}".format( _file )
            cls.appError( "gqa/pdf", result)
        
        return Response(result, status=status, mimetype=mimetype)


# ----------------------------------------------------------------------------- 
if __name__ == '__main__':
    
    #test()
       
    version_info = (0, 0, 1)
    version = '.'.join(str(c) for c in version_info)

    # Initialisieren des parsers und setzen des Hilfetextes
    parser = argparse.ArgumentParser( description='Neko' )
    
    parser.add_argument('--version', action='version', version='%(prog)s {}'.format(version) )
    
    parser.add_argument( "-w", "--webserver",
        action="store_true",
        default=False,
        help="Startet einen Webserver",
    )
        
    # ohne Angaben immer webserver
    args = None
    if len( sys.argv ) == 1:
        #args = ["--help"]
        args = ["--webserver"]

    # Parse commandline arguments
    # unterbindet exit bei help und version
    try:
        args = parser.parse_args( args )
    except SystemExit:
        args=None
        

    if args:
        if args.webserver:
            models = [
                dbtests,
                dummy,
                unittest
            ]
            run(config, additionalModels=models )
            
       
