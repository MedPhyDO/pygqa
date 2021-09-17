 # -*- coding: utf-8 -*-

"""

Daten holen
-----------

<server>/api/info/<year>

Test durchführen
----------------
<server>/api/run

PDF Ausgabe
-----------
<server>/api/pdf


"""

__author__ = "R. Bauer"
__copyright__ = "MedPhyDO - Machbarkeitsstudien des Instituts für Medizinische Strahlenphysik und Strahlenschutz am Klinikum Dortmund im Rahmen von Bachelor und Masterarbeiten an der TU-Dortmund / FH-Dortmund"
__credits__ = ["R.Bauer", "K.Loot"]
__license__ = "MIT"
__version__ = "0.1.4"
__status__ = "Prototype"

import json

from isp.config import ispConfig

from app.ariadicom import ariaDicomClass

import logging
logger = logging.getLogger( "MQTT" )

from isp.safrs import ispSAFRSDummy

from safrs import jsonapi_rpc # rpc decorator
from flask import Response

class gqa( ispSAFRSDummy ):
    """
    description: Geräte QA - Test und Durchführung
    ---

    """

    _database_key = ""

    _dicom_key = ""

    config = None

    ariaDicom = None


    @classmethod
    def init(self, kwargs:dict={} ):
        """
        Wird von den @jsonapi_rpc Funktionen aufgerufen

        Parameters
        ----------
        kwargs : dict, optional
            DESCRIPTION. The default is {}.

        Returns
        -------
        kwargs : TYPE
            DESCRIPTION.

        """

        info = {}
        # Konfiguration ggf. für weitere Module jahres/monats basiert bereitstellen
        # dabei kwargs immer als int wenn nicht vorhanden dann aktuelles datum
        if "year" in kwargs or "month" in kwargs or "day" in kwargs:
            year = 9999
            month = 99
            day = 99
            if "year" in kwargs:
                if kwargs["year"] == None:
                    kwargs["year"] = 0
                else:
                    kwargs["year"] = int(kwargs["year"])
                    year = kwargs["year"]
            if "month" in kwargs:
                if kwargs["month"] == None:
                    kwargs["month"] = 0
                else:
                    kwargs["month"] = int(kwargs["month"])
                    month = kwargs["month"]
            if "day" in kwargs:
                if kwargs["day"] == None:
                    kwargs["day"] = 0
                else:
                    kwargs["day"] = int(kwargs["day"])
                    day = kwargs["day"]

            last = int("{year:04d}{month:02d}{day:02d}".format(
                year = year,
                month = month,
                day = day
            ))
            # bis last als Overlay verwenden
            self.config = ispConfig( lastOverlay=last )
            info["gqa.lastOverlay"] = last
        else:
            self.config = ispConfig(  )

        # config mit overlay erweitern
        self.config.update( self._configOverlay )

        info["version"] = self.config.get("version")
        info["configs"] = self.config._configs
        self.appInfo( "gqa.config info", info )

        # name der verwendeten Datenbank und dicom verbindung
        self._database_key = self.config.get( "server.database.servername", "VMSCOM" )
        self._dicom_key = self.config.get( "dicom.servername", "" )

        # ariaDicom bereitstellen
        self.ariaDicom = ariaDicomClass(
            database = self._database_key,
            server = self._dicom_key,
            config = self.config
        )

        # unit pid über config Angaben holen
        if not "pid" in kwargs or kwargs["pid"] == None:
            kwargs["pid"] = list( self.config.units.keys() )

        if type( kwargs["pid"] ) == str:
            kwargs["pid"] = kwargs["pid"].split(",")

        # passende pid ( PatientenID ) zu einer unit über config bestimmen
        if "unit" in kwargs:
            for pid, unit in self.config.units.items():
                if unit == kwargs["unit"]:
                    kwargs["pid"] = [ pid ]

        self.appInfo( "gqa.init", kwargs )

        return kwargs

    @jsonapi_rpc( http_methods=['GET'] )
    def api_list(cls, **kwargs):
        """
        .. restdoc::
        summary : alle Jahre in denen Test gemacht wurden
        description: alle Jahre in denen Test gemacht wurden
        parameters:
            - name : _ispcp
              type : OrderedMap
              in : query
              default : {}
              description : zusätzliche parameter

        ----

        """
        result = []
        return  cls._int_json_response( { "data": result } )

    @jsonapi_rpc( http_methods=['GET'] )
    def api_get(cls, **kwargs):
        """
        .. restdoc::

        summary : Tests und Fortschritte für ein Jahr
        description: alle Test und deren Fortschritte für ein Jahr
        parameters:
            - name : gqaId
              in : path
              type: integer
              required : true
              description : gqaId - Das Jahr für das die Informationen geholt werden sollen
            - name : pid
              in : query
              required : false
              description : Id des Tests im Aria [_xxxQA TB, _xxxQA VB]
            - name : unit
              in : query
              required : false
              description : Name eines Geräts wird nach pid umgewandelt und auch dort gesetzt
            - name : _ispcp
              type: OrderedMap
              in : query
              default : {}
              description : zusätzliche parameter

        ----

        """

        # gibt es _s_object_id in den parametern dann als year verwenden
        if cls._s_object_id in kwargs:
            kwargs["year"] = int( kwargs[ cls._s_object_id ] )

            # config laden und alle anderen parameter prüfen
            _kwargs = cls.init( kwargs )

            # Aufruf Paramter in App-Info ablegen
            cls.appInfo( "do_get", _kwargs )

            # Abfrage durchführen
            result = cls.ariaDicom.getAllGQA(
                pids = _kwargs["pid"],
                year = _kwargs["year"],
                withInfo=False,     # alle ImageInfos mit hinzufügen
                withResult=True     # Testergebnisse mit ausgeben
            )

        else:
            result = []
            cls.appError( "keine daten", _kwargs )

        return cls._int_json_response( { "data": result } )

    @classmethod
    @jsonapi_rpc( http_methods=['GET'] )
    def tagging( cls, **kwargs ):
        """
        .. restdoc::

        description: alle verwendeten Tags holen
        summary : Tags als HTML ausgeben
        parameters:
            - name : pid
              in : query
              required : false
              description : Id des Tests im Aria [_xxxQA TB, _xxxQA VB]
            - name : unit
              in : query
              required : false
              description : Name eines Geräts wird in pid umgewandelt und dort gesetzt
            - name: art
              in : query
              description : Art der tags [full, sum, test, tags]
              default : full
            - name : format
              in : query
              required : false
              default : json
              description : Format der Ausgabe [ json, html ]

        ----

        alle verwendeten Tags holen

        Parameters
        ----------
        **kwargs : TYPE
            art : full, sum, test, tags
            pid : []


        """

        _kwargs = {
            "art" : "full"
        }
        # config laden und alle anderen parameter prüfen
        _kwargs.update( cls.init( kwargs ) )

        # Tagging html|dict holen
        data = cls.ariaDicom.getTagging( art=_kwargs["art"], pid=_kwargs["pid"], output_format=_kwargs[ 'format' ]  )

        if kwargs[ 'format' ] == "json":
            return cls._int_json_response( {"data" : data } )

        return Response(data, mimetype='text/html')


    @classmethod
    @jsonapi_rpc( http_methods=['GET'] )
    def matrix( cls, **kwargs ):
        """
        .. restdoc::

        description: alle verwendeten Tags holen
        summary : alle verwendeten Tags holen
        parameters:
            - name : _ispcp
              in : query
              type: OrderedMap
              default : {}
              description : zusätzliche parameter
            - name : year
              in : query
              type: integer
              required : false
              description : Das Jahr für das die Ausgabe erfolgen soll
            - name : month
              in : query
              type: integer
              required : false
              description : Der Monat für den die Ausgabe erfolgen soll
            - name : format
              in : query
              required : false
              default : json
              description : Format der Ausgabe [ json, html ]
        ----


        """
        # config laden und alle anderen parameter prüfen
        _kwargs = cls.init( kwargs )

        cls.appInfo("matrix", _kwargs )

        # print("getMatrix", kwargs)

        # Matrix HTML holen
        data = cls.ariaDicom.getMatrix( output_format=_kwargs[ 'format' ], params=_kwargs )
        if kwargs[ 'format' ] == "json":
            return cls._int_json_response( {"data" : data } )

        return Response(data, mimetype='text/html')

    @classmethod
    @jsonapi_rpc( http_methods=['GET'] )
    def configs( cls, **kwargs ):
        """
        .. restdoc::

        description: GQA Konfigurationen holen
        summary : Holt alle GQA Konfigurationen aus allen configs als json oder stellt sie in einer Tabelle dar
        parameters:
            - name : _ispcp
              in : query
              type: OrderedMap
              default : {}
              description : zusätzliche parameter
            - name : format
              in : query
              required : false
              default : json
              description : Format der Ausgabe [ json, html ]
        ----


        """
        import numpy as np
        from app.config import gqa_config

        gqa_df = gqa_config().read().matrix()

        # print( kwargs )
        if kwargs[ 'format' ] == "json":
            return cls._int_json_response( {"data" : gqa_df.replace({np.nan:None}).to_dict() } )

        style = """
        <style>
        .gqa-config {
            color: #333;
            min-width: 100px;
            border-collapse: collapse;
            border-spacing: 0;
            font-size: 12px;
        }
        .gqa-config td, .gqa-config th {
            border: 1px solid gray;
            text-align: center;
            vertical-align: middle;
        }
        .gqa-config th {
            font-weight: bold;
        }
        .gqa-config thead th, .gqa-config tbody th {
            background: #FCFCFC;
        }

        .gqa-config th,
        .gqa-config td,
        .gqa-config caption {
            padding: 2px 2px 2px 2px;
        }

        /*
          You can zebra-stripe your tables in outdated browsers by adding
          the class "even" to every other table row.
         */
        .gqa-config tbody tr:nth-child(even) td,
        .gqa-config tbody tr.even td  {
          background: #FAFAFA;
        }
        .gqa-config tfoot       { font-style: italic; }
        .gqa-config caption     { background: #eee; }

        /* Angaben auch für pivot
        */
        .gqa-config {
            empty-cells: show;
        }

        .gqa-config .index_name{

        }
        .gqa-config .blank{

        }
        .gqa-config .data{
            text-align: left;
            vertical-align: top;
        }
        .gqa-config .data code{
            word-wrap: break-word;
            white-space: pre-wrap;
            max-width: 35em;
            display: inline-block;
        }

        """
        def json_pretty( value ):
            #value = "<pre>" + value + "</pre>"

            return value

        html = '<div class="gqa-config flex-1">'
        html += (gqa_df.replace({np.nan:''}).style
            .set_table_attributes('class="gqa-config"')
            .format("<pre><code>{}</code></pre>")
            .render()
        )
        html += '</div>'
        return Response(style + html, mimetype='text/html')

    @classmethod
    @jsonapi_rpc( http_methods=['GET'] )
    def info( cls, **kwargs ):
        """
        .. restdoc::

        description: Informationen zu allen Tests eines Jahres holen
        summary : Informationen holen
        parameters:
            - name : year
              in : query
              type: integer
              required : true
              description : Das Jahr für das der Test durchgeführt werden soll
            - name : pid
              in : query
              required : false
              description : Id des Tests im Aria [_xxxQA TB, _xxxQA VB]
        """

        # config laden und alle anderen parameter prüfen
        _kwargs = cls.init( kwargs )

        # Aufruf Paramter in App-Info ablegen
        cls.appInfo( "do_get", _kwargs )

        where = "LEN([Radiation].[Comment]) > 0  "

        pids = _kwargs["pid"]
        if type(pids) == str:
            pids = pids.split(",")

        if not type(pids) == list:
            pids = [pids]

        if not pids or len(pids) == 0:
            _result = { "error": "no pid (Aria Patient ID) found in config or params" }
        else:
            subSql = []
            for pid in pids:
                subSql.append( "[Patient].[PatientId]='{}'".format( pid.strip() ) )
            if len( subSql ) > 0:
                where += " AND (" + " OR ".join( subSql ) + ")"

            images, sql = cls.ariaDicom.getImages(
                addWhere=where,
                AcquisitionYear=_kwargs["year"]
            #    AcquisitionMonth=month,
            #    AcquisitionDay=day,
            #    testTags=testTags
            )

            _result = {"sql": sql, "data":images }

        return cls._int_json_response( { "data": _result } )


    @classmethod
    @jsonapi_rpc( http_methods=['GET'] )
    def run( cls, **kwargs ):
        """
        .. restdoc::

        description: Einen angegebenen Test durchführen
        summary : Einen angegebenen Test durchführen
        parameters:
            - name : _ispcp
              type: OrderedMap
              in : query
              default : {}
              description : zusätzliche parameter
            - name : testid
              in : query
              required : true
              description : Der durchzuführende Test
            - name : pid
              in : query
              required : false
              description : Id des Tests im Aria [_QA Linac1, _QA Linac2]
            - name : unit
              in : query
              required : false
              description : Name eines Geräts wird in pid umgewandelt und auch dort gesetzt
            - name : year
              in : query
              type: integer
              required : true
              description : Das Jahr für das der Test durchgeführt werden soll
            - name : month
              in : query
              type: integer
              required : false
              description : Der Monat für das der Test durchgeführt werden soll
            - name : day
              in : query
              type: integer
              required : false
              description : Der Tag für den der Test durchgeführt werden soll
            - name : getall
              in : query
              type: boolean
              required : false
              default : false
              description : Bei true wird nicht nur das Ergebnis sondern alle Infos zurückgegeben
            - name : unittest
              in : query
              type: boolean
              required : false
              default : false
              description : bei unittest wird das Ergebnis und nicht die Info zurückgegeben
            - name : reloadDicom
              in : query
              type: boolean
              required : false
              default : false
              description : Gespeicherte DicomDaten verwenden oder neu laden
        ----

        """

        _kwargs = {
            "month": 0,
            "day": 0,
            "reloadDicom": False,
            "unittest": False,
            "getall": False
        }
        _kwargs.update( cls.init( kwargs ) )

        cls.appInfo("run", _kwargs )

        _result = []

        # nur wenn mind. pid, year, testid angegeben wurde
        if "pid" in _kwargs and "year" in _kwargs and "testid" in _kwargs:
            # für jede Patienten Id
            for pid in _kwargs["pid"]:
                _result = cls.ariaDicom.runTests(
                    pid =           pid,
                    year =          int( _kwargs["year"] ),
                    month =         int( _kwargs["month"] ),
                    day =           int( _kwargs["day"] ),
                    testId =      _kwargs["testid"],
                    reloadDicom =  _kwargs["reloadDicom"],
                    unittest =     _kwargs["unittest"]
                )

        if _kwargs["getall"] == True: # pragma: no cover
            # nach einem run kann die info des testjahres aller units zurückgegeben werden
            # config nur für dieses jahr einlesen und verwenden
            cls.init( {"year": _kwargs["year"] } )

            _result = cls.ariaDicom.getAllGQA(
                pids = list(cls.config.units.toDict().keys()),
                year = int( _kwargs["year"] ),
                withInfo=False,
                withResult=True
            )
        elif not _kwargs["unittest"] == True:
            # bei einem normalem Aufruf nur result verwenden
            runTests = {}

             # <AcquisitionYear>-<AcquisitionMonth>-<unit>-<testId>-<energy>
            for key, value in _result.items():
                pdfName = value["pdfData"]["pdf_filename"]
                runTests[pdfName] = value["result"]

            _result = { "runTests": runTests }


        return cls._int_json_response( { "data": _result } )

    @classmethod
    @jsonapi_rpc( http_methods=['GET'] )
    def pdf( cls, **kwargs ):
        """
        .. restdoc::

        description: PDF eines Tests zurückgeben
        summary : PDF eines Tests zurückgeben
        parameters:
            - name : _ispcp
              in : query
              default : {}
              description : zusätzliche parameter
            - name : testid
              in : query
              required : true
              description : Der anzuzeigende Test
            - name : unit
              in : query
              required : false
              description : Id des Geräts wird nach pid umgewandelt und auch dort gesetzt
            - name : energy
              in : query
              required : true
              default : ""
              description : Energie für die das PDF angezeigt werden soll
            - name : year
              in : query
              type: integer
              required : true
              description : Das Jahr für die Anzeige
            - name : month
              in : query
              type: integer
              required : false
              default : 0
              description : Der Monat für die Anzeige
        """

        import os.path as osp
        from jinja2 import Environment
        # jinja enviroment
        env = Environment()

        _kwargs = {
            "testid" : "nn",
            "unit" : "",
            "energy" : "",
            "year" : 0,
            "month" : 0
        }
        # config laden und alle anderen parameter prüfen
        _kwargs.update( cls.init( kwargs ) )

        # metadaten zum ersetzen zusammenstellen
        meta = {
            "AcquisitionYear": int( _kwargs["year"] ),
            "unit": _kwargs["unit"],
            "energy": _kwargs["energy"],
            "testId": _kwargs["testid"]
        }

        # bei Angabe eines Monats AcquisitionMonth hinzufügen
        if int( _kwargs["month"] ) > 0:
            meta["AcquisitionMonth"] = int( _kwargs["month"] )

        # Art des tests MT|JT
        infoTypeArt = _kwargs["testid"][0:2]

        # sicherstellen, das in path auch das Jahr angehängt wurde
        path = cls.ariaDicom.initResultsPath( AcquisitionYear=meta["AcquisitionYear"] )

        # Dateiname zusammenstellen
        pdfFile = osp.join( path, cls.config.templates.get( "PDF-" + infoTypeArt + "-filename", "" ) )
        # Dateiname und Pfad vorbereiten
        pdfFile = env.from_string( pdfFile ).render(
            **meta
        )

        mimetype='text/html'
        status = 200
        result = ""
        #
        if osp.isfile( pdfFile ):

            result = ""
            with open(pdfFile, 'rb') as static_file:
                result = static_file.read()
                mimetype='application/pdf'
                #result = send_file(static_file, attachment_filename='file.pdf')
                # self.response_headers['Content-Type'] = 'application/pdf'

            if result == "":
                status=400
                result = "Error Open File {}".format( pdfFile )
                cls.appError( "gqa/pdf", result )

        else:
            status=400
            result = "No File {}".format( pdfFile )
            cls.appError( "gqa/pdf", result)


        return Response(result, status=status, mimetype=mimetype)
