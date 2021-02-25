# -*- coding: utf-8 -*-
"""Speicherung und Bereitstellung aller Testergebnisse 

Die Ergebnisse werden in einer pandas Tabelle bereitgestellt
und im resultsPath als json Datei abgelegt.

 
"""

__author__ = "R. Bauer"
__copyright__ = "MedPhyDO - Machbarkeitsstudien des Instituts für Medizinische Strahlenphysik und Strahlenschutz am Klinikum Dortmund im Rahmen von Bachelor und Masterarbeiten an der TU-Dortmund / FH-Dortmund"
__credits__ = ["R.Bauer", "K.Loot"]
__license__ = "MIT"
__version__ = "0.1.0"
__status__ = "Prototype"

import pandas as pd

import os
import os.path as osp

import logging
logger = logging.getLogger( "MQTT" )
        
class ispResults(  ):
    """Verarbeitet die Testergebnisse
    Speichert per default in <resultsPath>/gqa.json
    
    unterstützte Datenformate (wrapper):
        
        * json (.json)
        
    """
    
    config = None
        
    filename = None
    
    columns = None
    
    index = None
    
    errors = []
    
    """Pandas
    """
    gqa = None
     
    def __init__( self, config:None, filename=None ):
        """ in gqa ein pandas object bereitstellen 
        zum laden und speichern den über die Dateiendung bestimmten wrapper verwenden
        
        Parameters
        ----------
        config: ispConfig object
            Die eingelesene Konfiguration
        
        filename: str, optional
            Der zu verwendene Dateiname ohne Angabe aus config bestimmen
            
        """
        self.gqa = None
        
        self.config = config
        
        if filename:
            self.filename = filename
        else:
            self.filename = osp.join( config.get("resultsPath", ".."), config.get("database.gqa.name", "gqa.json") )    
        
        # spalten und index bereitstellen(type nur für sql)
        self.columns = {
            "unit" : "string",
            "energy" : "string",
            "test" : "string",
            "date" : "string",
            "group": "int32",
            "year" : "int32",
            "month" : "int32",
            "acceptance" : "int32",
            "data" : "string"
        }
        
        # date und group auch als index damit mehrere pro jahr/monat möglich sind
        # Der Index ist notwendig damit ein update/insert funktioniert 
        self.index = [ 'unit', 'energy', 'test', 'date', 'group' ]
                
        # pandas dataframe vorbereiten
        self.gqa = pd.DataFrame( {}, columns=self.columns.keys() )
        self.gqa.set_index( self.index, inplace=True)
        
        # datei noch nicht vorhanden - anlegen
        if not osp.isfile( self.filename ):
            self.write()
            
        self.isOnline = self.read()
          
        #print( self.errors )
        # immer noch nichts angelegt offline Daten verwenden (keine speicherung)   
        #if not self.isOnline: 
        #    self.gqa = pd.DataFrame( {}, columns=self.columns.keys() )
        #    self.gqa.set_index( self.index, inplace=True)
       
        
    def write( self ):
        """Pandas Object als json im table format speichern
        
        default Genauigkeit: double = 10 nachkommastellen
        
        table:
        {"schema": {"fields":[{"name":"test","type":"string"},{"name":"unit","type":"string"},{"name":"date","type":"string"},{"name":"acceptance","type":"string"}],"primaryKey":["test","unit","date"],"pandas_version":"0.20.0"}, "data": [{"test":"MT_WL","unit":"VitalBeamSN2674","date":"20191110","acceptance":3},{"test":"MT_WL","unit":"VitalBeamSN2674","date":"20191111","acceptance":4}]}
        
        Returns
        -------
        bool
            True bei erfolgreichen Speichern der Daten
        
        """ 
        ok = False
        if not osp.isfile( self.filename ) or os.access(self.filename, os.W_OK) is True:
            try:
                self.gqa.to_json( self.filename, orient="table", double_precision=10, indent=2 ) # , indent=2 erst später
                ok = True
            except:
                msg = "results.write fehlgeschlagen ({})".format(self.filename) 
                self.errors.append( msg )
        else:
            msg = "results.write keine Schreibrechte ({})".format(self.filename) 
            self.errors.append( msg )      
            
        return ok

    def read( self ):
        """Pandas Object als json im table format laden
        
        Returns
        -------
        bool
            True bei erfolgreichen Laden der Daten
        """

        ok = False
        if os.access(self.filename, os.R_OK) is True:
            try:
                self.gqa = pd.read_json( self.filename, orient="table", precise_float=10 )
                ok = True
            except:
                msg = "results.read fehlgeschlagen ({})".format(self.filename) 
                self.errors.append( msg )
        else:
            msg = "results.read keine Leserechte ({})".format(self.filename) 
            self.errors.append( msg )
            
        return ok
        
    def upsert( self, rows:list=[] ):
        """ Einen update oder insert Befehl in gqa durchführen
        
        Parameters
        ----------
        rows: list
            Ein Liste von Objecten mit Feldern aus self.columns
        
        Returns
        -------
        bool
            True wenn das Einfügen möglich war     
        """     
        
        if len(rows) == 0:
            return False
        
        # print("upsert", rows ) 
        # Dataframe mit gleichem index vorbereiten
        upsert_df = pd.DataFrame( rows )
        upsert_df.set_index(self.gqa.index.names, inplace=True)
        
        for idx, row in upsert_df.iterrows():
            # daten überschreiben oder anhängen
            #print( "upsert-idx", idx )
            self.gqa.loc[ idx ] = row 
            
        return True
    
