# -*- coding: utf-8 -*-

""" Basis Funktionen für alle Tests

"""

__author__ = "R. Bauer"
__copyright__ = "MedPhyDO - Machbarkeitsstudien des Instituts für Medizinische Strahlenphysik und Strahlenschutz am Klinikum Dortmund im Rahmen von Bachelor und Masterarbeiten an der TU-Dortmund / FH-Dortmund"
__credits__ = ["R.Bauer", "K.Loot"]
__license__ = "MIT"
__version__ = "0.1.0"
__status__ = "Prototype"

import sys
import json
import datetime

#from app.core import ispCore

#from app.pdf import appPdf as ispPdf

from isp.mpdf import PdfGenerator as ispPdf

import matplotlib.pyplot as plt

from collections import OrderedDict
import pandas as pd
import numpy as np

import logging
logger = logging.getLogger( "MQTT" )

class ispBase(  ):
    '''Basis Klasse
    
    Attributes
    ----------
    
    _config:
        
    metadata : 
        Metadaten aus config.metadata
    dicomData: dict
        Die übergebenen Dicomdaten
    pdf: class
        Die pdf Klasse
    fileCount: int
        wird für progress verwendet
    icons: dict
        Vorbelegte Icons für die Testergebnisse
        
    '''
        
    def __init__( self, config=None, metadata={}, dicomData={} ):
        """Initialisiert die Klasse und stellt icons und pdf bereit

        Parameters
        ----------
        config:
            Die aktuelle config
        metadata : TYPE, optional
            Metadaten aus config.metadata. The default is {}.
        dicomData : TYPE, optional
            Zu bearbeitende Dicomdaten. The default is {}.

        Returns
        -------
        None.

        """
        #self.pdf: str = None
        self.fileCount = 0
        
        self._config = config
        
        # mit einer Kopie der Metadaten arbeiten
        self.metadata: dict = metadata.copy()
        
        self.dicomData: dict = dicomData
        
        # ispCore initialisieren 
        #ispCore.__init__( self )
        
        # pdf erstellung bereitstellen
        self.pdf = ispPdf( variables=self.metadata, config=self._config )
        
        # print("_variables", self.pdf._variables )
       
        # kleine icons size=x1 für result Tabelle bereitstellen
        self.icons: dict = {
            5: self.pdf.resultIcon( 5, iconOnly=True, size="x1", addClass="tableIcon" ), # ok
            4: self.pdf.resultIcon( 4, iconOnly=True, size="x1", addClass="tableIcon" ), # Good
            3: self.pdf.resultIcon( 3, iconOnly=True, size="x1", addClass="tableIcon" ), # warning
            2: self.pdf.resultIcon( 2, iconOnly=True, size="x1", addClass="tableIcon" ), # Insufficient
            1: self.pdf.resultIcon( 1, iconOnly=True, size="x1", addClass="tableIcon" ), # error
            0: np.nan, # nicht durchgeführt
            "nan": np.nan, # nicht durchgeführt
            999 : np.nan # nicht durchgeführt
        }

    
    def __del__(self):
        """Ausführung beim löschen der Instanz
        Alle vorhandenen figures entfernen
        
        """
        for i in plt.get_fignums():
            figure = plt.figure(i)
            axes = figure.get_axes()
            for ax in axes:
               figure.delaxes(ax) # alle Achsen entfernen
            try:
                figure.clf( ) # figures löschen
                plt.close( i ) # und entfernen
            except: # pragma: no cover
                pass                

    def getFullData(self, field):
        """Holt aus dicomData die zu Field id passenden dicomDaten und gibt beide zurück
        
        
        Parameters
        ----------
        field: dict, OrderedDict, className=Pandas|Series
            muss id enthalten
            
        Returns
        -------   
        result : dict
            * info: field
            * dicom: 
                
        """
       # print("getFullData", field.__class__.__name__ )
        
        # ggf. umwandelungen duchführen
        if isinstance(field, tuple) and field.__class__.__name__ == "Pandas":
            # eine Pandas tuple in ein dict umwandeln 
            field = dict( field._asdict() )
        elif field.__class__.__name__ == 'Series':
            # eine Pandas serie in ein dict umwandeln: df.iloc[3] 
            field = field.to_dict()
        elif isinstance( field, OrderedDict):
            # ein OrderedDict in ein dict umwandeln
            field = dict( field )

        result = {
            "_type" : "fulldata",
            "info" : field,
            "dicom" : {}
            
        }
        # ist eine id angegeben 
        if "id" in field and field["id"] in self.dicomData:
            result["dicom"] = self.dicomData[ field["id"] ]
   
        return result
    
    def getMetaErrorString( self, meta:dict={} ):
        """Erzeugt einen String aus Metadata für Fehler Angaben

        Parameters
        ----------
        meta : dict, optional
            Metadata. The default is {}.

        Returns
        -------
        meta_str : str

        """
        _meta = {
            "testType":"ispBase.checkFields",
            "AcquisitionYear":  "",
            "AcquisitionMonth":  "",
            "unit":"",
            "energy":""
        }
        
        if isinstance( meta, dict ): 
            _meta.update( meta )

        # string zusammenstellen
        meta_str = "{testType} {unit}-{energy} {AcquisitionYear}/{AcquisitionMonth}".format( **_meta )
        
        return meta_str
        
    
    def checkFields(self, meta:dict={}, baseField=None, fields=None, fieldLen:int=-1, warn:bool=True ):
        """prüft ob in den Pandas.dataFrames ein baseField und die fieldLen von fields stimmen 
        
        BaseField muss nicht angegeben werden 
        
        FIXME: später nur noch dict verwenden
            
        Parameters
        ----------
        meta: dict
            metadata des Aufrufs
        baseField : pandas
            das basis Feld
        fields: pandas
            die ermittelten passenden Felder
        fieldLen: int
            die Anzahl der benötigten Felder
        warn:
            Eine Warung auf logger ausgeben
            
        Returns
        -------   
        ok : boolean
            False - bei Fehlern
            True - wenn ok
             
        """
        ok = True
        errors = []
        # base Field
        if isinstance(baseField, pd.DataFrame) and len(baseField) != 1:
            ok = False
            errors.append( "baseField fehlt" )
        
        # fields prüfen
        if fieldLen > -1 and isinstance(fields, pd.DataFrame) and len(fields) != fieldLen:
            
            err_fields = {}
            # base Field ist da
            if isinstance(baseField, pd.DataFrame): 
                err_fields["base"] = baseField[ ["CourseId", "PlanSetupId", "RadiationId", "ImageId", "acquisition", "SliceUID"] ].to_json()
            
            err_fields["fields"] = fields[ ["CourseId", "PlanSetupId", "RadiationId", "ImageId", "acquisition", "SliceUID"] ].to_json()
                
            errors.append( " Feldzahl {} statt {} ".format( len(fields), fieldLen ) )
            errors.append( err_fields )
            ok = False
            
        if not ok:
            meta_str = self.getMetaErrorString( meta )
            self.appError( meta_str, errors )
            if warn:
                logger.error( meta_str + ": " + json.dumps( errors ) )
                    
        return ok           
     
        
    def pdf_error_result(self, md:dict={}, date="", group_len:int=0, msg:str="", pos:dict={},  ):
        """Für das PDF eine fehlermeldung erzeugen.

        Parameters
        ----------
        md : dict, optional
            DESCRIPTION. The default is {}.
        date : TYPE, optional
            DESCRIPTION. The default is "".
        group_len : int, optional
            DESCRIPTION. The default is 0.
        msg : str, optional
            DESCRIPTION. The default is "".
        pos : dict, optional
            DESCRIPTION. The default is {}.

        Returns
        -------
        result : int
            Rückgabe von createResult()

        """
    
        acceptance = 0
        # Gesamt check - na
        self.pdf.resultIcon( acceptance )
        if msg=="":
            msg = '<b>Datenfehler</b>'
        
        self.pdf.html( msg, pos  )
        result = self.createResult( md=md, date=date, 
            group=group_len, acceptance=acceptance
        )

        return result
                
    def check_tolerance(self, value, tolerance=None, name="default" ):
        """ Toleranzangaben für value im Bereich name prüfen 
        und den Wert für acceptance zurückgeben
        
        * 5 - green - very Good (True)
        * 4 - green - Good
        * 3 - yellow - Sufficient
        * 2 - orange - Insufficient
        * 1 - red - Fail (False)
        * 999 - (n.a.) Not applicable
        
        Parameters
        ----------
        value: int|real
            zu prüfender Wert
        tolerance: DotMap
            info des testaufrufs::
                
            { 
                name: {
                    f: formel mit {value} 
                    value: wert
                    range: [min, max]
                    operator: [ eq, ne, lt, gt, le, ge]
                }
            }
            
        Returns
        -------      
        acceptance: int
            Varianten::
                
            5 - green - very Good (True)
            4 - green - Good
            3 - yellow - Sufficient
            2 - orange - Insufficient
            1 - red - Fail (False)
            999 - (n.a.) Not applicable
            
        """
    
        if not isinstance( value, (int, float) ) or np.isnan( value ) or pd.isnull( value ):
            return 999
        
        # erstmal ok 
        acceptance = 5
        if tolerance:
            for t in ["warning", "error"]:
                try:
                    f = tolerance.get( name ).get( t ).get("f", None)
                except : # pragma: no cover
                    f = None
                    
                if f:
                    try:
                        # die formel auswerten und icon ggf überschreiben
                        if eval( f.format( value=value ) ):
                            if t == "warning":
                                acceptance = 3
                            else:
                                acceptance = 1
                    except : # pragma: no cover
                        acceptance = 0
                        
                    #print( f.format( value=row ) )
        #print("check_tolerance",  value, acceptance, tolerance )
        return acceptance
    
    def getIcon(self, acceptance):
        """Gibt das Icon das der acceptance Angabe entspricht
        
        Parameters
        ----------
        acceptance : int
            1-5 oder 999 
            
        Returns
        -------
        icon : str
            htmlcode des Icon
            
        """
                    
        try:
            icon = self.icons[ int(acceptance) ]
            acceptance = int(acceptance)
        except: # pragma: no cover
            icon = self.icons[ 999 ]

        return icon
        
    def check_acceptance_ext( self, df, md={}, check=[], withSoll=False ):
        """Überprüft die angegebenen Felder auf die Erfüllung der Toleranz Angaben
        Erweitert das Dataframe um  <field>_acceptance und <field>_passed (Icon)
        gibt das gesamt Ergebnis zurück 
        
        Parameters
        ----------
        df : DataFrame
            Pandas DataFrame mit den in  'field' angegebenen Feldern
        md : dict
            metadata mit tolerance angaben für die Energie in md["energy"] 
        check : dict
            field: str
                Name des Feldes in md
            tolerance: str
                Bezeichner des toleranz Bereichs in  md.tolerance
                wird tolerance nicht angegeben wird default verwendet
            query: str
                Filter für Felder bei denen der check angewandt wird
                
        withSoll: boolean
            true - zusätzlich value einfügen wenn in toleranz angegeben   
            
        Returns
        -------   
        df : DataFrame
            entweder das übergebene oder das neu erstellte bei angabe von query
        int : acceptance aller Felder
            5-ok, 3-warn, 1-error  0-bei nan
        
        """
        
        # Felder die für einen gesammelten check verwendet werden  
        fullCheck = {}
        
        # dataframes und sammlung von dataframes bei query angabe
        dfs = []
        for ci in check:
            
            tolerance = "default"
            
            if "tolerance" in ci:
                tolerance = ci['tolerance'] 
            
            if withSoll:
                try:
                    sollValue = md.tolerance[ md["energy"] ].get( tolerance ).get("soll").get("value", np.nan)
                except: 
                    sollValue = np.nan
                    
                if sollValue:
                    df[ ci['field'] + "_soll" ] = sollValue

            # bei query Angabe nur passende verwenden
            if "query" in ci:
                query = ci['query'] 
                qdf = df.query( query )
                qdf[ "_query" ] = query
            else:
                qdf = df
            
            # ein zusätzliches Feld <field>_acceptance anlegen und füllen
            qdf[ ci['field'] + "_acceptance" ] = np.nan
            qdf[ ci['field'] + "_acceptance" ] = qdf[ ci['field'] ].apply( 
                self.check_tolerance, 
                args=[ md.tolerance[ md["energy"] ], tolerance ]
            )
            
           
            # und ein zusätzliches feld <field>_passed anlegen     und füllen  
            qdf[ ci['field'] + "_passed" ] = qdf[ ci['field'] + "_acceptance" ].apply(
                self.getIcon 
            ) 
            
            # das feld in fullCheck merken
            fullCheck[ ci['field'] + "_acceptance" ] = ci['field'] + "_acceptance"

            # in der liste der dataframes anfügen
            dfs.append( qdf )

        # alle teil dataframes zusammenfassen
        df = pd.concat( dfs )    
        
        #print( "df", df)
        
        # minimun des fullcheck ermitteln
        minAll = df[ fullCheck ].min(axis=None, skipna=True)
        acceptance = minAll.min()
        
        return df, acceptance

    def check_acceptance( self, df, md={}, check=[], withSoll=False ):
        """Überprüft die angegebenen Felder auf die Erfüllung der Toleranz Angaben
        Erweitert das Dataframe um  <field>_acceptance und <field>_passed (Icon)
        gibt das gesamt Ergebnis zurück 
        
        Parameters
        ----------
        df : DataFrame
            Pandas DataFrame mit den in  'field' angegebenen Feldern
        md : dict
            metadata mit tolerance angaben für die Energie in md["energy"] 
        check : dict
            field: str
                Name des Feldes
            tolerance: str
                Bezeichner des toleranz Bereichs in  md.tolerance
                wird tolerance nicht angegeben wird default verwendet
        withSoll: boolean
            true - zusätzlich value einfügen wenn in toleranz angegeben   
            
        Returns
        -------      
        int : acceptance aller Felder
            Varianten::
                
            5 - green - very Good (True)
            4 - green - Good
            3 - yellow - Sufficient
            2 - orange - Insufficient
            1 - red - Fail (False)
            999 - (n.a.) Not applicable
        
        """
        
        fullCheck = []
        for ci in check:
            tolerance = "default"
            if "tolerance" in ci:
                tolerance = ci['tolerance'] 

            if withSoll:
                try:
                    sollValue = md.tolerance[ md["energy"] ].get( tolerance ).get("soll").get("value", np.nan)
                except:
                    sollValue = np.nan
                    
                if sollValue:
                    df[ ci['field'] + "_soll" ] = sollValue
                    
            df[ ci['field'] + "_acceptance" ] = df[ ci['field'] ].apply( 
                    self.check_tolerance, 
                    args=[md.tolerance[ md["energy"] ], tolerance ]
            )
             
            # und in passed anzeigen      
            #df[ ci['field'] + "_passed" ] = df[ ci['field'] + "_acceptance" ].apply( lambda x: 999 if 888 else self.icons[ x ] ) 
            df[ ci['field'] + "_passed" ] = df[ ci['field'] + "_acceptance" ].apply( self.getIcon ) 
            # das feld in fullCheck einfügen
            fullCheck.append( ci['field'] + "_acceptance")
        minAll = df[ fullCheck ].min(axis=None, skipna=True)
        acceptance = minAll.min()
        
        #print("check_acceptance",df, acceptance )
        return acceptance    
    
        
    def createResult(self, df=None, md={}, check=[], date="", group=0, acceptance=999 ):
        '''
        Erstellt ein result dict
        
        Parameters
        ----------
        df : list|DataFrame
            list oder Pandas DataFrame mit den in 'field' angegebenen Feldern
        md : dict
            metadata mit tolerance angaben für die Energie in md["energy"] 
        check : dict
            field: str
                Name des Feldes
        date : str
            Datum des Tests
        group: 
            ist notwendig falls mehrere Tabellen oder ein Test mehrfach an einem tag gemacht wurde
        acceptance : int, nan oder None
            wird immer nach int gewandelt nan und None werden zu 999

        Returns
        -------
        result : dict
            - test (testTag) 
            - unit
            - energy
            - year
            - month
            - date
            - group
            - acceptance
            - data
                In data immer eine list.

        '''
        
        
        # data : es werden nur die in md["table_fields"] angegebenen Felder verwendet  

        if isinstance(df, type(None)):
            data = []
        elif type( df ) == list:
            # data soll so verwendet werden
            data = df
        else:
            # data stamm aus einem dataframe
            drops = []
            # passed felder ausschließen
            for ci in check:
                drops.append( ci["field"] + "_passed" )
                
            #print(  md.get('table_fields', [] ) )
            fields = []
            for field in md.get('table_fields', [] ):
                #print( fields )
                if not field["field"] in drops:
                    fields.append( field["field"] )
                    
            data = [ json.loads( df[ fields ].to_json(orient='index') ) ]
        
        if not acceptance or np.isnan( acceptance ) or pd.isnull( acceptance ):
            acceptance = 999
       
        # wenn in date ein . ist dann datum umwandeln
        if date.find(".") > 0:
            date_time_obj = datetime.datetime.strptime(date, "%d.%m.%Y")
            date = date_time_obj.strftime("%Y%m%d")
            
        # print("createResult", md)
        
        result = {
            "test" : md['testTag'],
            "unit" : md['unit'],
            "energy" : md['energy'],
            "year" : int( md.get('AcquisitionYear') or 0 ),
            "month" : int( md.get('AcquisitionMonth') or 0 ),
            "date" : date,
            "group" : int( group ),
            "acceptance" : int( np.nan_to_num( acceptance ) ),
            "data" : data
        }
     
        #print(acceptance, result )
        
        return result
    