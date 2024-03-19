# -*- coding: utf-8 -*-

__author__ = "R. Bauer"
__copyright__ = "MedPhyDO - Machbarkeitsstudien des Instituts für Medizinische Strahlenphysik und Strahlenschutz am Klinikum Dortmund im Rahmen von Bachelor und Masterarbeiten an der TU-Dortmund / FH-Dortmund"
__credits__ = ["R.Bauer", "K.Loot"]
__license__ = "MIT"
__version__ = "0.2.1"
__status__ = "Prototype"

from dotmap import DotMap
import os.path as osp
from pathlib import Path
import pandas as pd
import numpy as np
import json
from datetime import date

from isp.dicom import ispDicom
from isp.config import dict_merge

from app.config import infoFields

from app.aria import ariaClass
from app.results import ispResults

from app.qa.mlc import checkMlc
from app.qa.field import checkField
from app.qa.wl import checkWL
from app.qa.vmat import checkVMAT

import logging
logger = logging.getLogger( "MQTT" )

class ariaDicomClass( ariaClass, ispDicom ):
    '''Zentrale Klasse

    Attributes
    ----------

    config : Dot
        konfigurations Daten
    variables :
        Metadaten aus config.variables
    infoFields:
        Infofelder aus config
    dicomfiles: dict
        geladene Dicom dateien
    pd_results: pd
        testergebnisse als Pandas tabelle
    resultfile
        Datei mit Ergebnissen als panda File
    lastSQL: str
        die letzte durchgeführte sql Abfrage
    '''

    def __init__( self, database=None, server="VMSDBD", config=None  ):
        """Klasse sowie ariaClass und dicomClass initialisieren

        """

        # Klassen defaults setzen und übergaben
        self.config = config
        self.variables = self.config.variables
        self.infoFields = infoFields

        self.dicomfiles: dict = {}
        self.pd_results = None
        self.resultfile = None
        self.lastSQL = ""


        # ariaClass initialisieren
        ariaClass.__init__( self, database )

        # dicomClass initialisieren. Der Erfolg kann über dicomClass.initialized abgefragt werden
        ispDicom.__init__( self, server, self.config )

        # Datei mit Ergebnissen als pandas laden
        self.resultfile = osp.join( self.config.get("resultsPath", ".."), self.config.get("database.gqa.name", "gqa.json") )
        self.pd_results = ispResults( self.config, self.resultfile )

    def initResultsPath(self, AcquisitionYear=None ):
        '''Den Ablegeort zu den PDF Dateien bestimmen
        in variables.path befindet sich jetzt der resultsPath ggf. mit angehängten AcquisitionYear

        Parameters
        ----------
        AcquisitionYear : TYPE, optional
            DESCRIPTION. default: None.

        Returns
        -------
        dirname : str
            der aktuelle PDF Pfad (auch in self.variables["path"] )

        '''
        paths = [ ]

        # ist der Pfad relativ angegeben ab base path verwenden
        if self.config["resultsPath"][0] == ".":
            paths.append( self.config["BASE_DIR"] )
            paths.append( self.config["resultsPath"] )
        else:
            paths.append( self.config["resultsPath"] )

        # zusätzlich noch das AcquisitionYear anfügen
        if AcquisitionYear:
            paths.append( str(AcquisitionYear) )

        # den Pfad in  variables["path"] ablegen
        dirname = osp.abspath( osp.join( *paths ) )
        self.variables["path"] = dirname

        return dirname

    def getAllGQA(self, pids=None, testTags:list=None, year:int=None, month:int=None, day:int=None, withResult=False ):
        '''Holt für die angegebenen PatientenIds aus allen Courses
        die Felder mit Angaben in [Radiation].[Comment] und wertet sie entsprechend aus

        Parameters
        ----------
        pids : list, optional
            PatientIds to be searched for. default: None.
        testTags : list, optional
            tags to be searched for. default: None.
        AcquisitionYear : str, optional
            Year to search in AcquisitionDateTime Field, default: None
        AcquisitionMonth : str, optional
           Mounth to search in AcquisitionDateTime Field, default: None
        AcquisitionDay : str, optional
            Day to search in AcquisitionDateTime Field, default: None
        withResult : boolean, optional
            Testergebnisse mit ausgeben. default: False.

        Returns
        -------
        gqa : dict
           Aufbau::

           units: dict
             <unit>: dict
                <infoType>: dict
                    ready: dict
                        all: int
                        <energy> : int
                    gqa: dict
                        fields: int
                        energyFields: int
                    counts: dict
                        all: int
                        <energy> : int
                    pdf: dict,

                    items: dict
                        <energy>: dict
                            <SliceUID>: {info} -> dies wird bei run in ein DataFrame umgewandelt
                    series: [],

        '''

        if not pids:
            return {}

        if type(pids) == str:
            pids = pids.split(",")

        if not type(pids) == list:
            pids = [pids]

        if not pids or len(pids) == 0:
            return {}

        # filter zusammenstellen
        where = "LEN([Radiation].[Comment]) > 0  "

        subSql = []
        for pid in pids:
            subSql.append( "[Patient].[PatientId]='{}'".format( pid.strip() ) )
        if len( subSql ) > 0:
            where += " AND (" + " OR ".join( subSql ) + ")"

        images, sql = self.getImages(
            addWhere=where,
            AcquisitionYear=year,
            AcquisitionMonth=month,
            AcquisitionDay=day,
            testTags=testTags
        )

        self.lastSQL = sql

        # Pfad für die PDF Dateien
        self.initResultsPath( year )

        return self.prepareGQA( images, year=year, withResult=withResult )

    def prepareGQA(self, imagedatas=[], year:int=0, withResult=False, withDicomData:bool=False ):
        """Auswertung für GQA vorbereiten zusätzlich noch Ergebnisse aus der Datenbank einfügen

        Benötig config.GQA und config.units

        - units: ["Linac-1", "Linac-2"],
        - gqa : dict
            <testId>: dict
                <unit>: dict
                    fields: int
                    energyFields: int

        Parameters
        ----------
        imagedatas : list, optional
            Auflistungen von Bildinformationen aus der Aria Datenbank. default: is [].
        year : int, optional
            Das zu verwendende Jahr. default: is 0.
        withResult : boolean, optional
            Testergebnisse mit ausgeben. default: is False.
        withDicomData : boolean, optional
           Info pro Gerät in dicomfiles ablegen. default: is False.

        Returns
        -------
        gqa : dict
            # alles aus config.gqa dabei die Unites mit Daten füllen
            <testname>
                info:
                    inaktiv
                    tip
                    anleitung
                    options:
                    TODO:
                    tolerance:
                        <energy>

                <unit-n>
                    fields: int
                    energyFields: int
                    energy: list

        """

        # dicom gerät , name , infos
        self.dicomfiles = {}
        units = {key: value for (key, value) in self.config.get( "units", {} ).items() if value }
        
        # Dateien im Pfad
        pdfFiles = []
        if osp.exists( self.variables["path"] ):
            p = Path( self.variables["path"] )
            pdfFiles = [i.name for i in p.glob( '*.pdf' )]

        # files = os.listdir( self.variables["path"] )
        data = {
            "GQA" : self.config.get("GQA").toDict(),
            "units" : units,
            "testTags" : {},
            "testIds": {}
        }

        # nur das gesuchte Jahr, ohne index
        df_results = self.pd_results.gqa[ self.pd_results.gqa['year'] == year ].reset_index()

        result_fields = [ "acceptance", "group" ]
        if withResult:
            result_fields.append("data")

        # neuen index setzen
        # Das geht nur bei daten in df_results
        if len(df_results.index) > 0:
            df_results.set_index( df_results.apply(lambda x: f"{x['year']}|{x['unit']}|{x['test']}|{x['energy']}|{x['month']}", axis=1), inplace=True )

            data["results"] = df_results[ result_fields ].to_dict( orient="split" )
        else:
            data["results"] = {
                "columns":result_fields,
                "data":[],
                "index":[]
            }

        # tags und gqa ids bestimmen
        for testid, item in self.config.GQA.items():
            if "tag" in item:
                data["testTags"][ item["tag"] ] = testid
                data["testIds"][ testid ] = item["tag"]

        tagNotFound = {}

        inactiv = []
        testNotFound = []

        for imagedata in imagedatas:

            # bereitetet die Datenbank Informationen auf
            info = self.getImageInfos( imagedata )

            unit = info["unit"]
            energy =  info["energy"]

            #
            # zusätzlich die Daten in self.dicomfiles ablegen
            #
            if withDicomData:
                if not unit in self.dicomfiles:
                    self.dicomfiles[ unit ] = {}
                # zusätzlich in dicomfiles ablegen
                self.dicomfiles[ unit ][ info["id"] ] = info

            # Felder zuordnen, eine Aufnahme kann für mehrere tests verwendet werden
            # tag für die Datenbank, testid für das PDF
            for testTag in info["testTags"]:
                # nur wenn es auch einen test gibt
                if not testTag in data["testTags"]:
                    tagNotFound[ testTag ] = testTag
                    continue

                testId = data["testTags"][testTag]

                # ist der test in gqa nicht erlaubt überspringen
                # inaktive kann auch einen Text enthalten der beschreibt warum
                # FIXME: inaktive
                t = "GQA.{}.info.inaktiv".format( testId )
                if not self.config.get(t, False) == False:
                    inactiv.append( self.config.get(t) )
                    continue

                # gibt es in GQA passend zum Test dem Gerät und der Energie einen Eintrag
                t = "GQA.{}.{}.energyFields.{}".format( testId, unit, energy )
                energyFields = self.config.get(t, False)
                if energyFields == False:
                    testNotFound.append( t )
                    continue

                # Art des tests MT|JT
                tagArt = testId[0:2]
                if tagArt == "JT":
                    dateFlag = "0"
                else:
                    dateFlag = str( info["AcquisitionMonth"] )

                #
                test_unit = data["GQA"][testId][unit]

                if not dateFlag in test_unit:
                    test_unit[ dateFlag ] = {}

                if not energy in test_unit[ dateFlag ]:
                    test_unit[ dateFlag ][energy] = {
                        "counts": 0,
                        "ready": False,
                        "pdfName" : "",
                        "pdf": False,
                        "acceptance" : {}
                    }

                # Anzahl der Felder für das Datumsflag der jeweiligen Energie erhöhen (counts)
                test_unit[ dateFlag ][ energy ][ "counts" ] += 1

                # auf mid Anzahl prüfen
                if test_unit[ dateFlag ][ energy ][ "counts" ]  >= energyFields:
                    test_unit[ dateFlag ][ energy ][ "ready" ] = True

                # PDF Dateiname zusammenstellen
                pdfName = self.config.render_template(
                    self.config["templates"][ "PDF-" + tagArt + "-filename"],
                    {
                        "AcquisitionYear": info["AcquisitionYear"],
                        "AcquisitionMonth": info["AcquisitionMonth"],
                        "unit": unit,
                        "energy": energy,
                        "testId": testId
                    }
                )

                if pdfName in pdfFiles:
                    test_unit[ dateFlag ][ energy ][ "pdfName" ] = pdfName
                    test_unit[ dateFlag ][ energy ][ "pdf" ] = True

        # nicht gefundene Tags
        data["inactiv"] = inactiv
        data["tagNotFound"] = tagNotFound
        data["testNotFound"] = testNotFound

        return data

    # ---------------------- einfache Ausgaben
    def getTagging(self, art:str="full", pid:list=[], output_format="json"  ):
        """alle Tags in Comment Feldern als html Tabelle zurückgeben

        Parameters
        ----------
        art : str, optional
            Art der Tagging Tabellen (). default: full
            * full
            * sum
            * test
            * tags

        pid : list, optional
            Angabe von PatientsIds für die Tags bestimmt werden sollen. default: []

        output_format: str
            Format der Ausgabe [ json, html ]

        Returns
        -------
        str|dict
            html Tags code oder dict.
        """

        style = """
        <style>
        .gqa-tagging {

        }
        .gqa-tagging table {
            color: #333;
            font-family: Helvetica, Arial, sans-serif;
            min-width: 100px;
            border-collapse: collapse;
            border-spacing: 0;
            font-size: 10px;
        }
        .gqa-tagging table td, .gqa-tagging table th {
            border: 1px solid gray;
            text-align: center;
            vertical-align: middle;
        }
        .gqa-tagging table th {
            font-weight: bold;
        }
        .gqa-tagging table thead th, .gqa-tagging table tbody th {
            background-color: #F7F7F7;
        }
        .gqa-tagging table td {
            background-color: white;
        }
        .gqa-tagging table th, .gqa-tagging table td, .gqa-tagging table caption {
            padding: 2px 2px 2px 2px;
        }
        </style>
        """

        split = True
        if art == "tags":
            # bei tags conmment nicht splitten
            split = False

        tags = self.getTags( pid, split )

        if output_format == "json":
            return tags

        if not tags or len(tags) == 0:
            return "getTagging: keine Daten gefunden"

        html = '<div class="gqa-tagging flex-1">'
        html += '<h1 class="m-0 p-1 text-white bg-secondary">Art: ' + art + '</h2>'
        # Pandas erzeugen
        df = pd.DataFrame( tags )

        if art == "full":
            table = pd.pivot_table( df,
                    index=['Comment', 'CourseId', 'PlanSetupId', 'Energy', 'DoseRate', 'RadiationId'],
                    columns='PatientId',
                    values= "nummer",
                    fill_value=0
                )
        elif art == "sum":
            table = pd.pivot_table( df,
                    index=['Comment', 'CourseId', 'PlanSetupId','Energy', 'DoseRate'],
                    columns=['PatientId'],
                    values= 'nummer',
                    aggfunc=[np.sum],
                    fill_value=0
                )
        elif art == "test":
            table = pd.pivot_table( df,
                    index=['Comment', 'CourseId', 'Energy', 'DoseRate'],
                    columns=[ 'PlanSetupId', 'PatientId'],
                    values= 'nummer',
                    aggfunc=[np.sum],
                    fill_value=0
                )
        elif art == "tags":
            table = pd.pivot_table( df,
                    index=['Comment'],
                    columns=['PatientId'],
                    values= 'nummer',
                    fill_value=0
                )
          

        def highlight_fifty( val ):
           color = 'black' if val > 0 else 'white'
           return 'color: %s' % color

        html += (table.style
            .applymap( highlight_fifty )
            .set_table_attributes('class="gqa-tagging-table"')
            #.float_format()
            .to_html( sparse_index=False )
        )

        html += '</div>'

        return style + html


    def getMatrix( self, output_format="json", params:dict={} ):
        """Gibt eine Liste alle Testbeschreibungen (config) mit Anleitungen

        Parameters
        ----------
        output_format: str
            Format der Ausgabe [ json, html ]
        params: dict
            Aufrufparameter mit year und month

        Returns
        -------
        str|dict
            html matrix code oder dict.

        """

        # jahr und Monat bei 0 mit dem aktuellen belegen
        today = date.today()
        if params["year"] == 0:
            params["year"] = today.year
        if params["month"] == 0:
            params["month"] = today.month

        # pdf wird zum laden der Texte verwendet
        from isp.mpdf import PdfGenerator as ispPdf
        pdf = ispPdf()

        html_jt = ""
        html_mt = ""
        html_nn = ""
        data_dict = {}
        for key, content in self.config.GQA.items():

            data = {
                "key" : key,
                "tip" : "",
                "need" : "",
                "anleitung" : "",
                "chips" : ""
            }
            chips = []

            # units und energy
            for unit_key, unit in self.config.units.items():
                if unit in content:
                    for energy in content[ unit ].energy:
                        chips.append( { "class": "badge badge-pill badge-info mr-1", "content": "{} - {}".format( unit_key, energy )  } )

            # info bestimmen
            info = content.info
            data["tip"] = info.get("tip", "")
            need = info.get("need", "")

            if type(need) == str and need != "":
                chips.append( { "class": "badge badge-pill badge-success", "content": 'benötigt: ' + need  } )

            # Anleitung
            anleitung_filename = info.get("anleitung", "")
            data["anleitung"] = '<p class="badge badge-pill badge-primary">Anleitung fehlt!</p>'
            if anleitung_filename != "":
                anleitung = pdf.textFile(anleitung_filename, render = False)
                if anleitung:
                    data["anleitung"] = anleitung

            # Toleranz
            tolerance = content.info.get("tolerance", False)
            if tolerance:
                data["anleitung"] += "<h6>Toleranz</h6>"
                # ggf formel erstellen
                for e, item in tolerance.items():
                    self.prepare_tolerance(key, e)
                    pass

                # toleranz einfügen
                data["anleitung"] += '<pre class="toleranz bg-light text-monospace ">' + json.dumps( tolerance, indent=2 ) + '</pre>'

            # ist der test als inaktiv Hinweis  ausgeben
            inaktiv = content.info.get('inaktiv', False)
            if inaktiv != False:
                chips.append( { "class": "inaktiv", "content": 'Inaktiv: ' + inaktiv } )

            # gibt es optional Angaben
            optional = content.info.get('optional', [])
            if len(optional) > 0:
                for item in optional:
                    chips.append( { "class": "badge badge-pill badge-primary", "content": 'Optional wenn: ' + item + ' OK' } )

            # TODO
            todo = content.info.get("TODO", False)
            if todo and len(todo) > 0:
                data["anleitung"] += "TODO"
                data["anleitung"] += '<pre class="p-1 bg-warning">'
                for t in todo:
                    data["anleitung"] += "* " + t + "\n"
                data["anleitung"] += '</pre>'

            # markierungen zusammenstellen
            for chip in chips:
                data["chips"] += '<div class="{class}">{content}</div>'.format(**chip)


            data_dict[ key ] = content.toDict()
            data_dict[ key ][ "anleitung" ] = anleitung

            card = """
            <div class="card m-3" >
                <div class="card-header">
                    <span class="font-weight-bolder">{key}</span>
                    <span class="pl-3">{tip}</span>
                    <div class="float-right">{chips}</div>
                </div>
                <div class="card-body p-1">
                    {anleitung}
                </div>
            </div>
            """.format( **data )
            if key[0:2] == "JT":
                html_jt += card

            elif key[0:2] == "MT":
                html_mt += card
            else:
                html_nn += card

        if output_format == "json":
            return data_dict

        style = """
        <style>
        /* Anpassung pdf text */
        .gqa_matrix h2 {
            font-size: 1.1667em;
            font-weight: bold;
            line-height: 1.286em;
            margin-top: 0.5em;
            margin-bottom: 0.5em;
        }
        .gqa_matrix .card-body p::first-of-type {
             background-color: #FFFFFFAA;
        }
        </style>
        """
        html = '''
        <div class="gqa_matrix">
        <h1 class="m-0 p-1 text-white bg-secondary" >Angaben für: {month}/{year}</h1>
        <content class="p-1 d-flex flex-row" >
        <div class="w-50">{jt}</div>
        <div class="w-50">{mt}</div>
        <div class="">{nn}</div>
        </content>
        </div>
        '''.format( jt=html_jt, mt=html_mt, nn=html_nn, **params )

        return style + html

    def prepare_tolerance(self, testid:str="", energy=None):
        """Prüft ob es in conig eine tolerance Angabe für die testid und die Energie gibt

        Stellt wenn f nicht angegeben wurde eine Formel in f zusammen

        Gibt es eine GQA.<testid>.info.tolerance.default Angabe, so wird diese als Grundlage für alle Energien verwendet

        Zweig in config::

            GQA.<testid>.info.tolerance.<energy>

            {
                name: {
                    f: formel mit {value}
                    value: wert
                    range: [min, max]
                    operator: [ eq, ne, lt, gt, le, ge]
                }
            }

        Parameters
        ----------
        testid : str, optional
            id des zu verarbeitenden tolerance Bereichs

        energy : str, optional
            Augabe der Energie für die Info. default: None.
            Ohne Angabe wird nur der Parameter info zurückgegeben

        Returns
        -------
        info : dict
            Parameter info mit zusätzlichen Angaben für die Energie.

            Beispiel::

            "default": {
                "warning" : { "f":"abs({value}) > 1.0", "unit": "%" },
                "error" : { "f":"abs({value}) > 2.0", "unit": "%" },
                "check" : { "field": "diff", "query":"ME == 100" }
            },
            "MU_20": {
                "warning" : { "f":"abs({value}) > 1.0", "unit": "%" },
                "error" : { "f":"abs({value}) > 2.5", "unit": "%" },
                "check" : { "field": "diff", "query":"ME == 20" }
            },

        """
        info = self.config.get( ["GQA", testid, "info" ] )

        default = info.tolerance.get( "default", False )
        tolerance = info.tolerance.get( energy, False )
        if not tolerance and not default:
            return DotMap()

        if not default:
            default = DotMap()

        if tolerance:
            tolerance = dict_merge( default, tolerance)
        else:
            tolerance = default

        import functools
        # alle Angaben durchgehen
        for name in tolerance:
            if not isinstance( tolerance.get(name), dict ):
                continue
            for artName, art in tolerance.get(name).items():
                # überspringen wenn art ein string ist oder f schon vorhanden
                if type(art) is str or art.get("f", None):
                    continue
                # gibt es keine formel dann erstellen
                # wurde ein wert angegeben
                _value = art.get("value", None)
                _range = art.get("range", None)
                if _value:
                    #zuerst den operator festlegen
                    operator = art.get("operator", "gt")
                    # [ eq, ne, lt, gt, le, ge]
                    operator = functools.reduce(lambda a, b: a.replace(*b)
                        , [('eq','=='),('ne','!='),('lt', '<'),( 'gt', '>'),( 'le','<='),( 'ge', '>=')] #iterable of pairs: (oldval, newval)
                        , operator #The string from which to replace values
                        )
                    tolerance[name][artName]["f"] = "abs({}) {} {}".format( "{value}", operator, _value )
                # wurde ein Bereich angegeben
                elif art.get("range", None) and len(_range) >= 2:
                    tolerance[name][artName]["f"] = "{} <= {} >= {}".format( _range[0], "{value}", _range[1] )
        return tolerance


    # ---------------------- Test durchführung
    def runTests(self, pid=None,
                 year:int=None, month:int=None, day:int=None,
                 testId:str=None, reloadDicom:bool=False, unittest:bool=False ):
        """Einen angegebenen Test vorbereiten und durchführen

        Parameters
        ----------
        pid : str, optional
            die zu verwendende PatientId, default: None
        year : int, optional
            das zu verwendende Jahr, default: None
        month : int, optional
            der zu verwendende Monat, default: None
        day : int, optional
            der zu verwendende Tag, default: None
        testId : str, optional
            die id des durchzuführenden Test, default: None
        reloadDicom : bool, optional
            Dicomdaten neu laden oder vorhandene verwenden, default: False
        unittest : bool, optional
            spezieller modus für unittest, default: False

        Returns
        -------
        dict
            Testergebnisse
        """        
        # die results der jeweiligen pdf Datei
        test_results = {}

        # units und test bereitstellen
        # units = self.config.units
        unit = self.config.get( ["units", pid], False)
        test = self.config.get( ["GQA", testId], False)

        if test == False or unit == False:
            return test_results

        # tags und gqa ids bestimmen
        tags = {}
        for key, item in self.config.GQA.items():
            if "tag" in item:
                tags[ item["tag"] ] = key

        testTag = test.tag
        
        # getTestData sucht in der datenbank nach dem tag des tests
        data = self.getTestData(
            PatientId=pid,
            AcquisitionYear=year,
            AcquisitionMonth=month,
            AcquisitionDay=day,
            testTags=[ testTag ]
        )

        energyFields = self.config.get( ["GQA", testId, unit, 'energyFields'], {} )

        for energy, info in data.items():

            # nur die Energien die angegeben wurden
            if not energy in energyFields:
                continue

            # payload erweitert in doTestType variables und wird für MQTT verwendet
            payload = {
                "testId" : testId,
                "testTag" : testTag,
                "AcquisitionYear" : year,
                "AcquisitionMonth" : month,
                "unit" : unit,
                "energy" : energy,
                "reloadDicom" : reloadDicom,
                "unittest": unittest
            }

            # den test durchführen
            pdfFilename, results = self.doTestType(
                testId =  testId,
                data =      info,
                payload =   payload
            )

            # results in pandas ablegen
            if len(results) > 0:
                self.pd_results.upsert( results["result"] )

            # nur ablegen wenn ein pdf da ist
            if not pdfFilename == "":
                # results pro dateiname merken
                test_results[ pdfFilename ] = results

        # Pandas Ergebnisse speichern
        self.pd_results.write()

        # pdf Dateien zurückgeben
        return test_results


    def doTestType(self, testId:str, data=None, payload:dict={} ):
        """Den angegebene Test durchführen. Dabei die passende Klasse verwenden

        Parameters
        ----------
        testId : str
            die id des durchzuführenden Test, default: None
        data : dict, optional
            Imageinfos per SliceUID, default: None
        payload : dict, optional
            erweitert self.variables für den Test, default: {}

        Returns
        -------
        str
            pdf_filepath des erzeugten pdf
        dict
            Ergebnis der Testauswertung
            - result
            - pdfData

        """        

        imageCount = len( data )
        # ohne Daten nichts machen
        if imageCount == 0:
            # Anzeigen des problems?
            return False

        # metadaten als kopie bereitstellen und um payload erweitern
        # damit gerät und energie für das pdf vorhanden ist
        variables=self.variables.copy()

        # variables um payload erweitern
        variables.update( payload )

        # metadaten um die test Variante erweitern
        variables["variante"] = payload["testTag"]

        # variables um configdaten des Tests erweitern diese werden in der test Klasse als metadata verwendet
        variables["testConfig"] = self.config.get( ["GQA", testId ], DotMap() );
        current = self.config.get( ["GQA", testId, "current" ], DotMap() )
        variables["testConfig"]["current"] = dict_merge( current, DotMap({
            "testTag":  variables["variante"],
            "testId": variables["testId"],
            "unit": variables["unit"],
            "energy": variables["energy"],
            "year": variables["AcquisitionYear"],
            "month": variables["AcquisitionMonth"],
            "fields": self.config.get( ["GQA", testId, variables["unit"], "energyFields", variables["energy"] ], current.get( "fields" ,0) ),
            "tolerance": self.prepare_tolerance( variables['testId'], variables['energy'] )
        }) )
        variables["testConfig"]["AcquisitionYear"] = variables["AcquisitionYear"]
        variables["testConfig"]["AcquisitionMonth"] = variables["AcquisitionMonth"]

        # die benötigten Daten vom server oder aus dem DICOM dir holen
        # in self.dicomfiles liegen dann pro gerät die Infos als dict
        # in self.data liegen dann pro SOPInstanceUID die eingelesenen DICOM daten
        if not "index" in payload:
            payload["index"] = 0

        if "AcquisitionYear" in payload:
            AcquisitionYear = payload["AcquisitionYear"]
        else:
            AcquisitionYear = ""

        # Pfad für die Ergebnisse vorbereiten
        self.initResultsPath( AcquisitionYear )

        # Dicom Daten einlesen
        i = 0
        read_count = 0
        dicomData = {}
        df = pd.DataFrame( data.values() )
        '''
        ['id', 'PatientId', 'RadiationId', 'RadiationSer', 'CourseId',
       'PlanSetupId', 'SliceRTType', 'ImageId', 'SeriesId', 'SeriesNumber',
       'CreationDate', 'studyID', 'filepath', 'filename', 'Kennung',
       'SOPClassUID', 'acquisition', 'AcquisitionYear', 'AcquisitionMonth',
       'day', 'Tag', 'unit', 'energy', 'doserate', 'MetersetExposure', 'ME',
       'Technique', 'gantry', 'GantryRtnExt', 'GantryRtnDirection',
       'StopAngle', 'collimator', 'CollMode', 'table', 'SID', 'MLCPlanType',
       'IndexParameterType', 'X1', 'X2', 'Y1', 'Y2', 'SliceUID', 'SeriesUID',
       'StudyUID', 'FrameOfReferenceUID', 'gating', 'testTags', 'subTags',
       'varianten', 'AcquisitionDateTime', 'dicom', 'check_variante',
       'check_subtag'],
        '''

        # progress starten
        if hasattr( logger, "progressStart"):
            logger.progressStart( testId, payload )

        # Dicomdaten mit retrieve() holen entweder lokal oder vom server
        for SOPInstanceUID in data:
            i += 1
            # 40% für die dicom daten 40% für die Auswertung 20 % für das pdf
            if hasattr( logger, "progress"):
                logger.progress( testId, 40 / imageCount * i )

            # Dicomdaten holen, diese werden in self.dicomData ergänzt um AcquisitionYear abgelegt
            result, signals = self.retrieve( {
                "PatientID" : data[SOPInstanceUID]["PatientId"],
                "SOPInstanceUID" : SOPInstanceUID,
                "override" : variables["reloadDicom"],
                "subPath" : str(AcquisitionYear)
            })
            for dcm in result:
                data[ dcm.SOPInstanceUID ]["dicom"] = dcm
                # FIXME: in allen testModulen zugriff auf dicom daten über data und nicht mehr über dicomData
                # getFullData() sollte dann nicht mehr benötigt werden
                dicomData[ dcm.SOPInstanceUID ] = dcm
                read_count += 1

            # dicom Verbindung falls sie geöffnet wurde schließen
            self.closeAE()

        if i > read_count: # pragma: no cover
            # das einlesen der Dicomdaten war nicht möglich
            if hasattr( logger, "progress"):
                logger.progress( testId, 100  )
            logger.warning( "doTestType: dicom retrieve Fehler: {} - {} - {} - {}".format(
                SOPInstanceUID,
                data[SOPInstanceUID]["testTags"],
                data[SOPInstanceUID]["PatientId"],
                data[SOPInstanceUID]["ImageId"]
            ) )
            return "", { "result":"", "content":"" }

        # ab hier immer 40%
        if hasattr( logger, "progress"):
            logger.progress( testId, 40  )

        # DataFrame erzeugen
        df = pd.DataFrame( data.values() )
        # die aktuelle variante und den subtag aus varianten in check_variante und check_subtag erzeugen
        df["check_variante"] = variables["testTag"]
        df["check_subtag"] = df["varianten"].apply(lambda x: x.get( variables["testTag"] ))

        logger.debug( "doTestTag: {}".format( variables["testTag"] ) )

        #
        # variables aufbereiten
        #

        # Art des tests MT|JT
        infoTypeArt = testId[0:2]

        # Dateiname aus config templates
        variables["filename"] = self.config.get( ["templates", "PDF-{}-filename".format(infoTypeArt)], "noname.pdf" )

        #  wenn nicht angegeben Titel und Betreff aus config templates
        for t in ["Titel", "Betreff"]:
            if variables.get(t, "") == "":
                variables[t] = self.config.get( ["templates", "PDF-{}-{}".format(infoTypeArt, t)], "" )

        pdfData = {
            "pdf_filepath" : ""
        }
        result = []

        if testId=="JT-4_2_2_1-A":
            check = checkMlc( self.config, variables, dicomData=dicomData )
            pdfData, result = check.doJT_4_2_2_1_A( df )
        elif testId=="JT-4_2_2_1-B":
            check = checkMlc( self.config, variables, dicomData=dicomData )
            pdfData, result = check.doJT_4_2_2_1_B( df )
        elif testId=="JT-4_2_2_1-C":
            check = checkMlc( self.config, variables, dicomData=dicomData )
            pdfData, result = check.doJT_4_2_2_1_C( df )
        elif testId=="JT-LeafSpeed":
            check = checkMlc( self.config, variables, dicomData=dicomData )
            pdfData, result = check.doJT_LeafSpeed( df )
        elif testId=="JT-10_3_1":
            check = checkMlc( self.config, variables, dicomData=dicomData )
            pdfData, result = check.doJT_10_3_1( df )
        elif testId=="JT-7_2":
            check = checkField( self.config, variables, dicomData=dicomData )
            pdfData, result = check.doJT_7_2( df )
        elif testId=="JT-7_3":
            check = checkField( self.config, variables, dicomData=dicomData )
            pdfData, result = check.doJT_7_3( df )
        elif testId=="JT-7_4":
            check = checkField( self.config, variables, dicomData=dicomData )
            pdfData, result = check.doJT_7_4( df )
        elif testId=="JT-7_5":
            check = checkField( self.config, variables, dicomData=dicomData )
            pdfData, result = check.doJT_7_5( df )
        elif testId=="JT-9_1_2":
            check = checkField( self.config, variables, dicomData=dicomData )
            pdfData, result = check.doJT_9_1_2( df )
        elif testId=="JT-10_3":
            check = checkField( self.config, variables, dicomData=dicomData )
            pdfData, result = check.doJT_10_3( df )
        elif testId=="MT-4_1_2":
            check = checkField( self.config, variables, dicomData=dicomData )
            pdfData, result = check.doMT_4_1_2( df )
        elif testId=="MT-WL":
            check = checkWL( self.config, variables, dicomData=dicomData )
            pdfData, result = check.doMT_WL( df )
        elif testId=="MT-8_02-1-2":
            check = checkMlc( self.config, variables, dicomData=dicomData )
            pdfData, result = check.doMT_8_02_1_2( df )
        elif testId=="MT-8_02-3":
            check = checkMlc( self.config, variables, dicomData=dicomData )
            pdfData, result = check.doMT_8_02_3( df )
        elif testId=="MT-8_02-4":
            check = checkMlc( self.config, variables, dicomData=dicomData )
            pdfData, result = check.doMT_8_02_4( df )
        elif testId=="MT-8_02-5":
            check = checkField( self.config, variables, dicomData=dicomData )
            pdfData, result = check.doMT_8_02_5( df )
        elif testId=="MT-LeafSpeed":
            check = checkMlc( self.config, variables, dicomData=dicomData )
            pdfData, result = check.doMT_LeafSpeed( df )
        elif testId=="MT-VMAT-0_1":
            check = checkField( self.config, variables, dicomData=dicomData )
            pdfData, result = check.doMT_VMAT_0_1( df )
        elif testId=="MT-VMAT-0_2":
            check = checkMlc( self.config, variables, dicomData=dicomData )
            pdfData, result = check.doMT_VMAT_0_2( df )
        elif testId=="MT-VMAT-1_1":
            check = checkMlc( self.config, variables, dicomData=dicomData )
            pdfData, result = check.doMT_VMAT_1_1( df )
        elif testId=="MT-VMAT-1_2":
            check = checkMlc( self.config, variables, dicomData=dicomData )
            pdfData, result = check.doMT_VMAT_1_2( df )
        elif testId=="MT-VMAT-2":
            check = checkVMAT( self.config, variables, dicomData=dicomData )
            pdfData, result = check.doMT_VMAT_2( df )
        elif testId=="MT-VMAT-3":
            check = checkVMAT( self.config, variables, dicomData=dicomData )
            pdfData, result = check.doMT_VMAT_3( df )

        # ab hier ist progress immer 100%
        if hasattr( logger, "progress"):
            logger.progress( testId, 100 )

        # progress beenden
        if hasattr( logger, "progress"):
            logger.progressReady( testId )

        return pdfData["pdf_filepath"], { "result":result, "pdfData": pdfData }
