# -*- coding: utf-8 -*-

'''
Das eigentliche starten der app wird über run erledigt

'''

import logging

from isp.config import ispConfig

from app.db import gqadb

from app.api import gqa

from isp.webapp import ispBaseWebApp
from isp.safrs import db, system

# -----------------------------------------------------------------------------      
def run( overlay:dict={} ):
    ''' Startet ispBaseWebApp mit zusätzlichen config Angaben
    
    Parameters
    ----------
    overlay : dict, optional
        Overlay Angaben für config. The default is {}.

    Returns
    -------
    webApp : ispBaseWebApp
        Die gestartete WebApplication

    '''
   
    # Konfiguration öffnen
    _config = ispConfig( mqttlevel=logging.WARNING )
    
    _apiConfig = {
        "models": [ gqa, gqadb, system ],
    }
    
    # Webserver starten
    webApp = ispBaseWebApp( _config, db, apiconfig=_apiConfig, overlay=overlay )
    
    #  mqtt in config schließen
    _config.mqttCleanup( )
    return webApp
