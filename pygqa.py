# -*- coding: utf-8 -*-

"""
Das Hauptmodul der GeräteQA (GQA) 

Startet den Webserver

"""

import sys
import argparse

from app import run

# ----------------------------------------------------------------------------- 
if __name__ == '__main__':
       
    version_info = (1, 2, 0)
    version = '.'.join(str(c) for c in version_info)

    # Initialisieren des parsers und setzen des Hilfetextes
    parser = argparse.ArgumentParser( description='pygqa' )
    
    parser.add_argument('--version', action='version', version='%(prog)s {}'.format(version) )
    
    parser.add_argument( "-w", "--webserver",
        action="store_true",
        default=False,
        help="Startet den Webserver",
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