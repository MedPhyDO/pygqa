# -*- coding: utf-8 -*-

""" Basis Funktionen für alle Tests

"""

__author__ = "R. Bauer"
__copyright__ = "MedPhyDO - Machbarkeitsstudien des Instituts für Medizinische Strahlenphysik und Strahlenschutz am Klinikum Dortmund im Rahmen von Bachelor und Masterarbeiten an der TU-Dortmund / FH-Dortmund"
__credits__ = ["R.Bauer", "K.Loot"]
__license__ = "MIT"
__version__ = "0.1.2"
__status__ = "Prototype"

import sys
import json
import datetime

#from app.core import ispCore

#from app.pdf import appPdf as ispPdf

from isp.mpdf import PdfGenerator as ispPdf
from isp.config import dict_merge

import matplotlib.pyplot as plt

from collections import OrderedDict
from dotmap import DotMap

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
        Metadaten aus variables.testConfig
    dicomData: dict
        Die übergebenen Dicomdaten
    pdf: class
        Die pdf Klasse
    fileCount: int
        wird für progress verwendet
    icons: dict
        Vorbelegte Icons für die Testergebnisse
        
    '''
        
    def __init__( self, config=None, variables={}, dicomData={} ):
        """Initialisiert die Klasse und stellt icons und pdf bereit

        Parameters
        ----------
        config:
            Die aktuelle config
        variables : TYPE, optional
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
        
        # mit einer Kopie der Metadaten als DotMap arbeiten
        self.metadata = dict_merge( DotMap( {
            "manual": {
                "filename": variables.testConfig.info["anleitung"],
                "attrs": {"class":"layout-fill-width"},
            },
            "plotImage": {
                
            },
            "plotImage_pdf": {},
            "evaluation_table_pdf": {},
            "tolerance_pdf": {}
        }), variables.testConfig.copy() )
               
        self.dicomData: dict = dicomData
        
        # ispCore initialisieren 
        #ispCore.__init__( self )
        
        # pdf erstellung bereitstellen
        self.pdf = ispPdf( variables=variables, config=self._config )
        
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

        #print("getFullData", field )
        result = {
            "_type" : "fulldata",
            "info" : field,
            "dicom" : {}
            
        }
        # 
        if "dicom" in field:
            result["dicom"] = field["dicom"] 
        else:
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
        result: empty dict or dict with
            - msg: Message string for PDF output
            - data: list of fields
           
             
        """
        err_columns = ["CourseId", "PlanSetupId", "RadiationId", "ImageId", "acquisition", "gantry", "SliceUID"]

        # err_columns = ["FeldArt", "CourseId", "PlanSetupId", "RadiationId", "ImageId", "acquisition", "SliceUID"]
        result = {}
        
        errors = []
        err_fields = pd.DataFrame(columns=err_columns)
        err_fields['FeldArt'] = ''
        # base Field
        if isinstance(baseField, pd.DataFrame) and len(baseField.index) != 1:
   
            if len(baseField.index) > 1:
                errors.append( "- baseField ist nicht 1" )
                dfb = baseField[ err_columns ]
                dfb['FeldArt'] = 'base'

                err_fields = err_fields.append(dfb)
            else:
                errors.append( "- baseField fehlt" )
        
        # fields prüfen
        if fieldLen > -1 and isinstance(fields, pd.DataFrame) and len(fields.index) != fieldLen:
            
            dff = fields[ err_columns ]
            dff['FeldArt'] = 'field'
            
            err_fields = err_fields.append(dff)
            
            errors.append( "- Feldzahl ist {} statt {}".format( len(fields.index), fieldLen ) )
            
            #errors.append( err_fields )
            
        if len(err_fields) > 0:
            meta_str = self.getMetaErrorString( meta )
            # self.appError( meta_str, errors )
            if warn:
                logger.error( meta_str + ": " + json.dumps( errors ) )
            
            result = {"msg": "\n\n".join(errors), "data": err_fields}
        #print( result )
        return result   
     
        
    def pdf_error_result(self, md:dict={}, date="", group_len:int=0, errors:dict={}, msg:str="", pos:dict={},  ):
        """Für das PDF eine fehlermeldung erzeugen.

        Parameters
        ----------
        md : dict, optional
            DESCRIPTION. The default is {}.
        date : TYPE, optional
            DESCRIPTION. The default is "".
        group_len : int, optional
            DESCRIPTION. The default is 0.
        errors: dict
            immer mit
            - msg: str
            - data: DataFrame
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
        
        if "msg" in errors:
            msg += "\n\n" + errors["msg"]
            
        self.pdf.markdown( msg )
        
        if "data" in errors:
            self.pdf.pandas( errors["data"], pos )
            
        
        result = self.createResult( md=md, date=date, 
            group=group_len, acceptance=acceptance
        )

        return result
                
    def check_tolerance(self, value, tolerance=None, name="default", row=None ):
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

    def check_tolerance_ext(self, row, ci, tolerance=None, name="default" ):
        """Check tolerance specifications for value in the name tolerance. 
        
        Returns value for acceptance ::
        
        * 5 - green - very Good (True)
        * 4 - green - Good
        * 3 - yellow - Sufficient
        * 2 - orange - Insufficient
        * 1 - red - Fail (False)
        * 999 - (n.a.) Not applicable
        * 0 - eval error of f
        
        Parameters
        ----------
        row: pandas.row
            one row in DataFrame
        ci: dict 
            - field: str
                name of field in row
            - tolerance: str
                Identifier of tolerance range in  md.current.tolerance
                if tolerance is not specified, default is used 
            - query: str
                Filter for fields where the check is applied 
        tolerance: DotMap
            <name>: {
                f: formula with {value} 
                value: wert
                range: [min, max]
                operator: [ eq, ne, lt, gt, le, ge]
            }
            
        name: str
            name of tolerance entry
            
        Returns
        -------      
        acceptance: int
            
        """
        value = row[ ci['field'] ]
        
        if not isinstance( value, (int, float) ) or np.isnan( value ) or pd.isnull( value ):
            row[ ci['field'] + "_acceptance" ] = 999
            return row
        
        # use first ok 
        acceptance = 5
        if tolerance:
            for t in ["warning", "error"]:
                try:
                    f = tolerance.get( name ).get( t ).get("f", None)
                except : # pragma: no cover
                    f = None
                    
                if f:
                    if not "value" in row:
                        f = f.format( value=value, **row ) 
                    else:
                        f = f.format( **row ) 
                    
                    try:
                        # die formel auswerten und icon ggf überschreiben 
                        if eval( f ):
                            if t == "warning":
                                acceptance = 3
                            else:
                                acceptance = 1
                    except : # pragma: no cover   
                        print( "check_tolerance_ext eval error", f, value, row )
                        acceptance = 0

        row[ ci['field'] + "_acceptance" ] = acceptance
        return row

        
    def check_acceptance_ext( self, df, md={}, check:list=[], withSoll=False ):
        """Überprüft die angegebenen Felder auf die Erfüllung der Toleranz Angaben
        Erweitert das Dataframe um  <field>_acceptance und <field>_passed (Icon)
        gibt das gesamt Ergebnis zurück 
        
        Parameters
        ----------
        df : DataFrame
            Pandas DataFrame mit den in  'field' angegebenen Feldern
        md : dict
            metadata mit tolerance angaben für die Energie in md["energy"] 
        check : list with dict 
            field: str
                Name des Feldes in md
            tolerance: str
                Bezeichner des toleranz Bereichs in  md.current.tolerance
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

            # bei query Angabe nur passende verwenden
            if "query" in ci:
                query = ci['query'] 
                qdf = df.query( query )
                qdf[ "_query" ] = query
            else:
                qdf = df
                
            if not "field" in ci:
                # in der liste der dataframes anfügen
                dfs.append( qdf )
                continue
            
            tolerance = "default"
            if "tolerance" in ci:
                tolerance = ci['tolerance'] 
            
            if withSoll:
                try:
                    sollValue = md.current.tolerance.get( tolerance ).get("soll").get("value", np.nan)
                except: 
                    sollValue = np.nan
                    
                if sollValue:
                    df[ ci['field'] + "_soll" ] = sollValue

            # ein zusätzliches Feld <field>_acceptance anlegen und füllen
            # apply calls check_tolerance with args on each row (axis=1)
            
            qdf[ ci['field'] + "_acceptance" ] = np.nan
            qdf = qdf.apply( 
                lambda r: self.check_tolerance_ext( r, ci, md.current.tolerance, tolerance ),
                axis=1,
                result_type='expand'
            )
            
            # und ein zusätzliches feld <field>_passed anlegen     und füllen  
            qdf[ ci['field'] + "_passed" ] = qdf[ ci['field'] + "_acceptance" ].apply(
                self.getIcon 
            ) 
            
            # das feld in fullCheck merken
            fullCheck[ ci['field'] + "_acceptance" ] = ci['field'] + "_acceptance"

            #print( "# check_acceptance_ext-qdf", qdf )
            # in der liste der dataframes anfügen
            dfs.append( qdf )
             
        
        # alle teile des dataframes zusammenfassen
        df = pd.concat( dfs )
        
        # print( "check_acceptance_ext df", df)
        
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
                Bezeichner des toleranz Bereichs in  md.current.tolerance
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
        #print( "check_acceptance", df, md.current, check )
        
        fullCheck = []
        for ci in check:

            tolerance = "default"
            if "tolerance" in ci:
                tolerance = ci['tolerance'] 

            if withSoll:
                try:
                    sollValue = md.current.tolerance.get("soll").get("value", np.nan)
                except:
                    sollValue = np.nan
                    
                if sollValue:
                    df[ ci['field'] + "_soll" ] = sollValue
                    
            df[ ci['field'] + "_acceptance" ] = df[ ci['field'] ].apply( 
                    self.check_tolerance, 
                    args=[md.current.get( "tolerance", None ), tolerance ]
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

    def evaluationPrepare( self, df, md={}, result:list=[], printManual:bool=True, pre:str="" ):
        """Get base and fields, check number of df.
        
        printout manual (anleitung) and error Messages

        Parameters
        ----------
        df : pandas.DataFrame
            DataFrame with Testfields.
        md : DotMap, optional
            needs::
            - manual
                - filename
                - area
                - attrs
            - current
                - fields
                - <pre>fields
            - querys
                - base
                - fields
                - <pre>base
                - <pre>fields
                - engine
                
        result : list, optional
            List for results and error Messages.
        printManual: bool, optional
            Print manual. Default is True.
        pre: str, optional
            used for sub querys
        
        Returns
        -------
        ok : boolean
            true if checkFields without errors
        df_base : TYPE
            result of data query with querys.<pre>base
        df_fields : TYPE
            result of data query with querys.<pre>fields

        """
        # use date from first record
        md.current.check_date = df['AcquisitionDateTime'].iloc[0].strftime("%d.%m.%Y") 
        self.pdf.setContentName( md.current.check_date )

        #               
        # Manual
        #
        if printManual:
            self.pdf.textFile( **md.manual )
        
        field_count = int( md.current.get( pre + "fields", 0) )
        # get base field
        if md.querys.get(pre + "base", None) == None: 
            df_base = None
        else:
            df_base = df.query( md.querys[pre + "base"], engine=md.querys.get('engine', None) )
            field_count = field_count - 1
           
        # get all other fields
        if md.querys.get(pre + "fields", None) == None: 
            df_fields = df
        else:
            df_fields = df.query( md.querys[pre + "fields"], engine=md.querys.get('engine', None) )

        # check number of data
        ok = True
        errors = self.checkFields( md, df_base, df_fields, field_count )
        
        if len(errors) > 0:
            result.append( self.pdf_error_result( 
                md, date=md.current.check_date, group_len=len( result ),
                errors=errors
            ) )
            ok = False
                
        return ok, df_base, df_fields
    
    def evaluationResult(self, df, md={}, result:list=[], field:str=None, printResultIcon:bool=True):
        """Printout tolerance and result icon.
        
        Parameters
        ----------
        df : pandas.DataFrame
            DataFrame with Testfields.
        md : DotMap, optional
            needs::
                - evaluations: list - additional calculated fields for the table 
                - evaluation_text: str - Display this text instead of autom. generated text from evaluations
                - current: dict - current evaluation parameters 
                - table_sort_values_by
                - table_sort_values_ascending
                - evaluation_table_pdf: dict
                    - fields
                    - area
                    - attr
                - tolerance_pdf: dict
                    - area
                    - attr
                    - mode
                - evaluation_replaces: dict - text replaces with format 
                
        field: str, optional
            simple evaluation of field
        result : list, optional
            List for results and error Messages.
        printResultIcon: bool
            print Result Icon at end of page
            
        Returns
        -------
        acceptance: int
            total acceptance of evaluation
            
        """
        _md = dict_merge( DotMap( {
            "table_sort_values_by" : [],
            "table_sort_values_ascending": [],
            "evaluation_table_pdf": { },
            "tolerance_pdf": {
               # "mode":"markdown"
            },
            "evaluation_replaces": { "value": "Delta" }
        }), md )

        text = ""
        # zusätzliche berechungen einfügen
        if type( _md["evaluations"] ) == list:  
            eval_str = "\n".join( _md["evaluations"] )
            if type( _md["evaluation_text"] ) == str:
                text += _md["evaluation_text"]
            else:
                text += "**Berechnungen:**\n```javascript\n{}\n```\n".format( eval_str )
            try:
                df.eval( eval_str, inplace=True)
            except:
                pass

        #
        # create text for tolerance
        #
        if type(field) == str:
            tolerance_name = "default" 
            check = [ { "field":field, "tolerance": tolerance_name } ]
            
            text_values = {
                "f_warning": _md.current.tolerance[ tolerance_name ].warning.get("f",""),
                "f_error": _md.current.tolerance[ tolerance_name ].error.get("f","")
            }
            text += """<br>
                Warnung bei: <b style="position:absolute;left:25mm;">{f_warning}</b><br>
                Fehler bei: <b style="position:absolute;left:25mm;">{f_error}</b>
            """.format( **text_values ) 
        else:
            check = []
            tolerance_format = '<b>{}</b> <span style="position:absolute;left:25mm;">{}</span> <span style="position:absolute;left:75mm;">{}</span> <br>'
            text += tolerance_format.format("<br>", "<b>Warnung [%]</b>", "<b>Fehler [%]</b>")
            for tolerance_name, tolerance in _md.current.tolerance.items():         
                tolerance_check = tolerance.check
                
                tolerance_check["tolerance"] = tolerance_name
                check.append( tolerance_check )
                text += tolerance_format.format( tolerance_name, tolerance.warning.f, tolerance.error.f )

        #
        # Abweichung ausrechnen und Passed setzen
        #
        evaluation_df, acceptance = self.check_acceptance_ext( df, _md, check )
        
        if isinstance( _md["table_sort_values_by"], list ) or isinstance( _md["table_sort_values_by"], str ):
            try:
                evaluation_df.sort_values( 
                    by=_md["table_sort_values_by"], 
                    ascending=_md["table_sort_values_ascending"],
                    inplace=True
                )
            except:
                pass

        #
        # Ergebnis in result merken
        #
        result.append( self.createResult( evaluation_df, _md, check, 
            _md.current.check_date, 
            len( result ), # bisherige Ergebnisse in result
            acceptance
        ) )
            
        self.pdf.pandas( evaluation_df, **_md.evaluation_table_pdf )
                    
        # print text and replace all {<name>} for printout
        try:
            text = text.format( **_md["evaluation_replaces"] )
        except:
            pass
        self.pdf.text( text, **_md.tolerance_pdf )
        
        # Gesamt check - das schlechteste aus der tabelle
        if printResultIcon:
            self.pdf.resultIcon( acceptance )  
        
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
            - testId (testId) 
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

            # FIXME: nach umstellung aller auf evaluationResult nur noch md.evaluation_table_pdf.fields verwenden
            fields = []
            for field in md.evaluation_table_pdf.get("fields", md.get('table_fields', [] ) ):
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

        result = {
            "test" : md.current['testTag'],
            "testId" : md.current['testId'],
            "unit" : md.current['unit'],
            "energy" : md.current['energy'],
            "year" : int( md.get('AcquisitionYear') or 0 ),
            "month" : int( md.get('AcquisitionMonth') or 0 ),
            "date" : date,
            "group" : int( group ),
            "acceptance" : int( np.nan_to_num( acceptance ) ),
            "data" : data
        }
     
        return result
    