# -*- coding: utf-8 -*-
"""Speicherung und Bereitstellung aller Testergebnisse

Die Ergebnisse werden in einer pandas Tabelle bereitgestellt
und im resultsPath als json Datei abgelegt.


"""

__author__ = "R. Bauer"
__copyright__ = "MedPhyDO - Machbarkeitsstudien des Instituts für Medizinische Strahlenphysik und Strahlenschutz am Klinikum Dortmund im Rahmen von Bachelor und Masterarbeiten an der TU-Dortmund / FH-Dortmund"
__credits__ = ["R.Bauer", "K.Loot"]
__license__ = "MIT"
__version__ = "0.1.10"
__status__ = "Prototype"

import pandas as pd
from sqlalchemy import String, Date, Integer, JSON
import re
import os
import os.path as osp
import datetime

from isp.config import ispConfig
from app.db import gqadb
from isp.safrs import isoDateType

import logging
logger = logging.getLogger( "ISP" )

# spalten und index bereitstellen (type Angabe für sql)
columns = {
    "unit": String(25),
    "energy": String(25),
    "test": String(25),
    "date": isoDateType,
    "group": Integer(),
    "year": Integer(),
    "month": Integer(),
    "acceptance": Integer(),
    "data": JSON()
}
index = [ 'unit', 'energy', 'test', 'date', 'group' ]

class ispResults(  ):
    """Verarbeitet die Testergebnisse

    Verwendet den durch main definierten database Abschnitt
    - name : wenn angegeben wird die json Datei verwendet
    - connection: wenn angegeben wird die Datenbankverbindung verwendet

    Ohne beide Angaben ist name = gqa.json

    """

    config = None

    bind = "gqa"

    filename = None

    useFile = False

    useDB = False
    
    columns = None

    index = None

    errors = []

    """Pandas
    """
    gqa = None

    """Database
    """
    gqadb = None

    def __init__( self, config:None ):
        """ in gqa ein pandas object bereitstellen
        zum laden und speichern den über die Dateiendung bestimmten wrapper verwenden

        Parameters
        ----------
        config: ispConfig object
            Die eingelesene Konfiguration

        """
        self.gqa = None

        self.config = config
        if not config:
            self.config = ispConfig()

        # Konfigurationsabschnitt für Ergebnisse bestimmen
        
        self.bind = self.config.get("database.main", ["gqa"] )
        if type( self.bind ) == list:
            self.bind = self.bind[0]
        self.useDB = self.config.get(["database", self.bind, "connection"], False) != False 
        name = self.config.get(["database", self.bind, "name"], False)
        if self.useDB:
            self.gqadb = gqadb
            self.gqadb._int_init()
        elif not name:
            name = "gqa.json"

        # print( "withDB", self.bind, self.withDB )

        # spalten und index bereitstellen (type Angabe für sql)
        self.columns = columns
        # date und group auch als index damit mehrere pro jahr/monat möglich sind
        # Der Index ist notwendig damit ein update/insert funktioniert
        self.index = index

        # pandas dataframe vorbereiten
        self.gqa = pd.DataFrame( {}, columns=self.columns.keys() )
        self.gqa.set_index( self.index, inplace=True)

        if name:
            self.filename = osp.join( self.config.get("resultsPath", ".."), name )

            # datei noch nicht vorhanden - anlegen
            if not osp.isfile( self.filename ):
                self.useFile = True
                self.write()

            self.useFile = self.read()

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
                #self.gqa["year"] = self.gqa["year"].astype('int')
                #self.gqa["month"] = self.gqa["month"].astype('int')
                #self.gqa["acceptance"] = self.gqa["acceptance"].astype('int')
                ok = True
            except:
                msg = "results.read fehlgeschlagen ({})".format(self.filename)
                self.errors.append( msg )
        else:
            msg = "results.read keine Leserechte ({})".format(self.filename)
            self.errors.append( msg )

        return ok
    
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
        if not self.useFile:
            return False
        
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

    def upsert( self, rows:list=[] ):
        """ Einen update oder insert Befehl in gqa durchführen

        Parameters
        ----------
        rows: list
            Ein Liste von Objekten mit Feldern aus self.columns

        Returns
        -------
        bool
            True wenn das Einfügen möglich war
        """

        if len(rows) == 0:
            return False
        
        if self.useDB:
            for row in rows:
                self.gqadb.upsert( row )

        if self.useFile:
            # print("upsert", rows )
            # Dataframe mit gleichem index vorbereiten
            upsert_df = pd.DataFrame( rows )
            upsert_df.set_index(self.gqa.index.names, inplace=True)

            for idx, row in upsert_df.iterrows():
                # daten überschreiben oder anhängen
                #print( "upsert-idx", idx )
                self.gqa.loc[ idx ] = row

            return True

    def getYearData( self, year):
        """nur die Daten für das angegebene Jahr ohne index

        Parameters
        ----------
        year : int
            das zu filternde Jahr

        Returns
        -------
        DataFrame
            ohne Index
        """
        if self.useDB:
            qs = self.gqadb.getYearQueryString( year )
            conn = self.gqadb._get_connection()
            self.gqa = pd.read_sql_query( qs, con=conn )
            return self.gqa
        else:
            if not self.useFile:
                self.useFile = self.read()

        return self.gqa[ self.gqa['year'] == year ].reset_index()

    def getYears( self ):
        """Holt die verwendeten Jahre
        
        1. aus der Datenbank
        2. aus der geladenen Datei
        3. über scandir in resultsPath
        4. das aktuelle Jahr

        Returns
        -------
        list
            gefundene Jahre

        """
        years = []
        if self.useDB:
            years = self.gqadb.years()
        if self.useFile and len(years) == 0:
            years = self.gqa.year.unique().tolist()
        if len(years) == 0:
            p = self.config.get("resultsPath", "..")
            years = [ int(f.name) for f in os.scandir(p) if f.is_dir() and re.match(r'^[0-9]+$', f.name)]
        if len(years) == 0:
            today = datetime.date.today()
            years = [ today.year ]
        return years

    def exportYear( self, year=None ):
        """exportiert ein angegebenes Jahr in eine seperate json Datei im Jahresordner 

        Parameters
        ----------
        year : _type_, optional
            _description_, by default None

        Returns
        -------
        _type_
            _description_
        """

        result = {  }
        if  year: 
            years=[year]
        else:
            years=self.getYears()
        
        def saveYear( gqaYear ):
            y =  gqaYear.year.unique()[0] 
            resultPath = osp.join( self.config.get("resultsPath", ".."), str(y) )
            if not os.path.exists( resultPath ):
                try:
                    os.makedirs( resultPath )
                except IOError as e:
                    pass
                
            filename = osp.join( resultPath, "{}_{}".format( y, self.config.get("database.gqa.name", "gqa.json") ) )
            if not osp.isfile( filename ) or os.access(filename, os.W_OK) is True:
                try:
                    gqaYear.to_json( filename, orient="table", double_precision=10, indent=2 ) # , indent=2 erst später
                    result[filename] = True
                except:
                    msg = "results.exportYear fehlgeschlagen ({})".format(filename)
                    self.errors.append( msg )
                    result[filename] = False
            else:
                msg = "results.exportYear keine Schreibrechte ({})".format(filename)
                self.errors.append( msg )
        
        for year in years:
            gqaYear = self.getYearData( year )
            saveYear( gqaYear )

        return result
    
    def to_db( self ):
        """
        description: kopiert die aktuellen results in die Datenbank
                
        /api/gqa/import_from_json?
       
        """
        if not self.useDB:
            return None
        
        conn = self.gqadb._get_connection()
 
        self.gqa.to_sql('gqadb', conn, 
            index=True, 
            if_exists='append',
            dtype = self.columns
        )

        return self.filename