# -*- coding: utf-8 -*-
"""
Webserver für api testaufrufe

"""

import sys
import argparse
from os import path as osp

# Module von hier erreichbar machen 
ABSPATH = osp.dirname( osp.abspath( __file__) )
path =  osp.join( ABSPATH , "..")
sys.path.insert(0, path)

from isp.config import ispConfig
from isp.webapp import ispBaseWebApp
  
from isp.safrs import system, db

from testdb import dbtests
from testdummy import dummy

# -----------------------------------------------------------------------------
def run( config:dict={} ):
    ''' Startet ispBaseWebApp mit zusätzlichen config Angaben

    Parameters
    ----------
    config : dict, optional
        DESCRIPTION. The default is {}.

    Returns
    -------
    webApp : ispBaseWebApp
        Die gestartete WebApplication

    '''

    # Konfiguration öffnen
    _config = ispConfig(  )
    _config.update( config )

    print( "BASE_DIR", _config.get("BASE_DIR") )
    #print( _config )

    _apiConfig = {
        "models": [ system, dbtests, dummy ],
    }

    # Webserver starten
    webApp = ispBaseWebApp( _config, db, apiconfig=_apiConfig )
    return webApp

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
            run()
            
       