# -*- coding: utf-8 -*-

"""
Das Hauptmodul der GeräteQA (GQA) 

Startet den Webserver

"""

import sys
import argparse

from version import __version__
from app import run, importPandas, exportPandas

# ----------------------------------------------------------------------------- 
if __name__ == '__main__':

    # Initialisieren des parsers und setzen des Hilfetextes
    parser = argparse.ArgumentParser( description='pygqa' )
    subparsers = parser.add_subparsers()

    parser.add_argument('--version', action='version', version='%(prog)s {}'.format(__version__) )
    
    parser.add_argument( "-w", "--webserver",
        action="store_true",
        default=False,
        help="Startet den Webserver",
    )

    parser_import = subparsers.add_parser( "import",
        help="Importiert die angegebene Pandas Datendatei in die Datenbank"
    )
    parser_import.add_argument( "import_filename",
        default=None,
        help="Dateiname der Pandas Datendatei",
    )
    parser_import.add_argument( "-c", "--connection",
        default=None,
        help="Datenbank connection Angabe (ohne Angabe die aus config verwenden)",
    )
   
    parser_export = subparsers.add_parser( "export",
        help="Exportiert die Datenbank in die angegebene Pandas Datendatei"
    )
    parser_export.add_argument( "export_filename",
        default=None,
        help="Dateiname der Pandas Datendatei",
    )
    parser_export.add_argument( "-c", "--connection",
        default=None,
        help="Datenbank connection Angabe (ohne Angabe die aus config verwenden)",
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
            run(  )
        elif "import_filename" in args:
            importPandas( args.import_filename, args.connection )
        elif "export_filename" in args:
            exportPandas( args.export_filename, args.connection )
