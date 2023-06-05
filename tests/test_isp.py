# -*- coding: utf-8 -*-
"""

Alle in isp befindlichen Klassen und Funktionen prüfen.

Alle Laufzeit Fehlermeldungen sind bei der Testausführung gewollt 

Nach der Ausführung steht am Ende OK wenn alle Tests durchgefürt wurden.

Bei Fehlern in den Überprüfungen steht am Ende::
 
    ======================================================================  
    FAIL:
        .......
    
    FAILED (failures=x)

"""

import os
from os import path as osp

import site

# alle Module auch von der Konsole erreichbar machen 
ABSPATH = osp.dirname( osp.abspath( __file__) )
base_path =  osp.join( ABSPATH , "..")
site.addsitedir(base_path)

import shutil

import unittest
import json

import time
from datetime import datetime

import warnings
warnings.filterwarnings("ignore") 

from dotmap import DotMap

import threading

from isp.config import ispConfig, dict_merge
from isp.webapp import ispBaseWebApp
from isp.safrs import db, system


from testbase import testCaseBase

import testdb as testdb
from testdummy import dummy


import logging
logger = logging.getLogger()

# ordner test/files
files_path = os.path.join( ABSPATH, 'files') 
if not os.path.exists( files_path ):
    try:
        os.makedirs( files_path )
    except IOError as e:
         print("Unable to create dir.", e)
    
# weasyprint logging
wp_log_file = os.path.join(files_path, 'weasyprint.log') 
if os.path.exists( wp_log_file ):
    os.remove( wp_log_file )

wp_logger = logging.getLogger('weasyprint')

wp_logger.addHandler( logging.FileHandler( wp_log_file ) )
wp_logger.setLevel( logging.CRITICAL ) # WARNING, CRITICAL

         
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
    _config = ispConfig( config=config )
        
    _apiConfig = {
        "models": [ system, dummy, testdb.dbtests, testdb.dbtestsrel ],
    }
    
    _webconfig = {
        # nur um update von webconfig zu testen
        "name" : "test_isp",
    }

    # Webserver starten
    webApp = ispBaseWebApp( _config, db, webconfig=_webconfig, apiconfig=_apiConfig )
    return webApp

class testBase(testCaseBase):
    '''
    setUp(), tearDown(), and __init__() will be called once per test.
    
    app: Flask
        initialisierte Flask app

    api: SAFRSAPI
        initialisierte SAFRSAPI
        
    '''
    
    @classmethod
    def setUpClass(cls):
        ''' Wird beim initialisieren der Testklasse aufgerufen
        
        - Api bereitstellen
        - test Ergebnisse zum Vergleich laden
        '''  
        # This attribute controls the maximum length of diffs output by assert methods that report diffs on failure. 
        # It defaults to 80*8 characters
        cls.maxDiff = None    
        
        files_path = os.path.join( ABSPATH, 'files')
        pdf_path = os.path.join( ABSPATH, 'files', 'pdf')
       
        if not os.path.exists( files_path ):
            os.mkdir( files_path )
            
        resources_path = os.path.join( ABSPATH , "resources" ) 
        
        check_path = os.path.join( resources_path, 'check')
        if not os.path.exists( check_path ):
            os.mkdir( check_path )
            
        # alte Datenbank löschen: über Pfad Angaben falls in der config nicht die testdatei steht 
        db_file = os.path.join( files_path, "test_isp.db" ) 
        if os.path.exists( db_file ):
            os.remove( db_file )
            pass
        
        
        dbtests_file = os.path.join( resources_path, "dbtests.json" )
        dbtests = []
        with open(dbtests_file, 'r') as fp: 
            dbtests = json.load(fp)
            
        dbtestsrel_file = os.path.join( resources_path, "dbtestsrel.json" )
        dbtestsrel = []
        with open(dbtestsrel_file, 'r') as fp: 
            dbtestsrel = json.load(fp)
        
       
        # alle erzeugten pdf und den Pfad pdf löschen
        if os.path.exists( pdf_path ):
            shutil.rmtree( pdf_path )
        

        swagger_file = os.path.join( check_path, "swagger_test.json" )
        if not os.path.exists( swagger_file ):   
            with open(swagger_file, 'w') as fp: 
                obj = {
                    "info": {
                        "title": "test_isp"
                    }
                }
                json.dump(obj, fp, indent=2)
                     
        # webapp mit unitest config
        cls.webapp = run( {
            "loglevel" :{
                "safrs" : logging.DEBUG, # 10
                "sqlalchemy" : logging.DEBUG, # 10
                "webapp" : logging.DEBUG,
            },
            "server" : {
                "webserver" : {
                    "name" : "swagger_test",
                    "port" : 5001,
                    "TESTING": True,
                    "reloader" : False
                },
                "api": {
                    "DBADMIN": True,
                    "custom_swagger_config": os.path.join( check_path, "swagger_test.json" )
                }
            },
            "templates":{
                 "PDF-HEADER": None
            },
            "database": {
                "main": "tests",
                "tests" : {
                    "connection": "sqlite:///{{BASE_DIR}}/tests/files/test_isp.db"
                }
            }
        } )
        cls.app = cls.webapp.app
        cls.api = cls.webapp.api
        
        # import sqlalchemy, weasyprint
        
        #print( "sqlalchemy.__version__",  sqlalchemy.__version__ )
    
        #print( "weasyprint.__version__",  weasyprint.__version__ )
        
        # print("###### setUpClass", dbtests( ) )
        # n = dbtests( string="test" )
        
        # Grunddaten in die Datenbank laden 
        for d in dbtests:
            cls.app.post( "api/dbtests/", headers={'Content-Type': 'application/json'}, data=json.dumps({ 
                "data": {
                    "attributes": d,
                    "type":"dbtests"
                }
            }))
            
        for d in dbtestsrel:
            cls.app.post( "api/dbtestsrel/", headers={'Content-Type': 'application/json'}, data=json.dumps({ 
                "data": {
                    "attributes": d,
                    "type":"dbtestsrel"
                }
            }))
        
        
    @classmethod
    def tearDownClass(cls):
        """
        config unittest file löschen
        """
        #os.remove( cls.unitest_file )
        pass
        
    def setUp(self):
        ''' wird vor jedem test aufgerufen
        '''
        pass
    
    def tearDown(self):
        ''' wird nach jeden test aufgerufen
        

        Returns
        -------
        None.

        '''
        
        #self.app.
        # close the browser window
        #self.driver.quit()
        pass
    
    
class ispTest( testBase ):
    
 
    def test_config_mqtt(self):    
        '''isp.config ispConfig mit MQTTHandler (isp.mqtt) prüfen immer mit neuen kernel für mqttInitLogging
        
        '''
       
        # zuerst ohne parameter aufrufen
        config = ispConfig( )  
                
        # __repr__ testen soll nicht die Klasse sondern die config selbst (dotmap) geben
        self.assertEqual(
            repr(config)[:7], 'DotMap(' , "Fehler beim laden __repr__")
        
        # Magic Methods prüfen
        
        self.assertEqual(
            config.__dict__["_loadErrors"], [], "Fehler beim laden von _loadErrors")
        
        self.assertEqual(
            config._loadErrors, [], "__getitem__ Fehler bei vorhandenen _loadErrors im Object")
        
        self.assertEqual(
            type(config.test), DotMap, "__getitem__ Fehler bei nicht vorhandenen in der config")
        
        # __getattr__ wird bei nicht vorhandenen aufgerufen
        self.assertEqual(
            config._test, None, "__getitem__ Fehler bei nicht vorhandenen im Object")
        
        # __getitem__
        self.assertEqual(
            config["_loadErrors"], [], "__getitem__ Fehler")
        
        # __getitem__
        self.assertEqual(
            type(config["versions"]), DotMap, "__getitem__ mit dotmap Fehler")
        
        # __getattr__ mit dotmap (config Values) 
        self.assertEqual(
            type(config.versions), DotMap, "__getattr__ mit dotmap Fehler")
        
        # __setitem__
        config["_version"] = '2.unittest' # __setitem__
        self.assertEqual(
            config.__dict__["_version"], '2.unittest', "__setitem__ Fehler")
        
        # __setitem__ mit dotmap (config Values) 
        config["unittest"] = '3.unittest' # __setitem__
        self.assertEqual(
            config.unittest, '3.unittest', "__setitem__ mit dotmap Fehler")
                
        # __setattr__
        config._version = '3.unittest' # __setattr__
        self.assertEqual(
            config.__dict__["_version"], '3.unittest', "__setattr__ Fehler")
        
        # Zugiffe auf die config selbst
        #
        
        # komplette config als dict
        self.assertEqual(
            type( config.get() ), dict, "komplette config als dict")
        
        # config get mit default
        self.assertEqual(
           config.get("gibtsnicht", "defaultValue"), 'defaultValue', "config get mit default")
        
        # dotmap set oberste ebene
        config._config["unittest"] =  '4.unittest'
        self.assertEqual(
            config.get("unittest") , '4.unittest', "dotmap get auf erster ebene")
        
        # dotmap set/get auf einer ebene
        config._config.A.unittest =  '4A.unittest'
        self.assertEqual(
            config.get("A.unittest") , '4A.unittest', "dotmap get auf zweiter ebene")
        
        config._config.A.B.unittest =  '4AB.unittest'
        self.assertEqual(
            config.get( ["A", "B", "unittest"] ) , '4AB.unittest', "dotmap get auf dritter ebene")
        
        # dotmap set oberste ebene
        config.set("5unittest", '5-unittest')
        # dotmap get
        self.assertEqual(
            config.get("5unittest"), '5-unittest', "dotmap set auf erster ebene anlegen")
        # dotmap set oberste ebene überschreiben
        config.set("5unittest", '5a-unittest')
        # dotmap get
        self.assertEqual(
            config.get("5unittest"), '5a-unittest', "dotmap set auf erster ebene ändern")   
        
        # dotmap set zweite ebene
        config.set("B5.unittest", '5B-unittest')
        
         # dotmap get
        self.assertEqual(
            config.get("B5.unittest"), '5B-unittest', "dotmap set auf zweiter ebene") 
         
        # dotmap set zweite ebene als list
        config.set(["C5","unittest"], '5C-unittest')
        
        # dotmap get
        self.assertEqual(
            config.get(["C5","unittest"]), '5C-unittest', "dotmap set/get auf zweiter ebene  als list") 
         
        # dotmap set zweite ebene neues Element
        config.set("B5.unittestA", '5B-unittest')
        self.assertEqual(
            config.get("B5").toDict(), {'unittest': '5B-unittest', 'unittestA': '5B-unittest'}, "dotmap set zweite ebene neues Element") 
      
        
        # hilfsfunktion dict_merge testen
        a = {"A":1}
        b = {"B":2}
        c = dict_merge(a, b)
        self.assertEqual(
            c, {'A': 1, 'B': 2}, "dict_merge auch neue keys") 

        c = dict_merge(a, b, False)
        self.assertEqual(
            c, {'A': 1}, "dict_merge nur vorhandene keys")
 

        # test in config setzen update prüfen
        #
        localtime = time.strftime("%Y%m%d %H:%M:%S.%f", time.localtime(time.time()) )
        config.test = {"a":1, "time": localtime }
        
        # a verändern
        config.update( { 
            "test": {"a":2}
        })
        self.assertEqual(
            config.test,  {"a":2, "time": localtime }, "Fehler bei config update")
                    
        # ohne mqtt findet default logging statt (konsole)
        # .. todo:: Konsole logger funktionen noch überprüfen
        logger = logging.getLogger( "MQTT" )
        logger.debug('logger.debug')
        logger.info("logger.info")
        logger.warning("logger.warning")
        logger.error("logger.error")
        
 
        # mqtt logging prüfen
        #
        
        if config.get("server.mqtt.host", "") == "":
            print( "(MQTT) keine Angaben in config vorhanden. MQTT wird nicht getestet!")
            return;
        
                
        # config mit anderem mqttLevel
        config = ispConfig( mqttlevel=30 )
        
        mqtt = config.mqttGetHandler()
       
        self.assertIsNotNone(
            mqtt, "kein MQTT handler vorhanden")   
        
        results = {}
        mqtt_event = threading.Event()
        mqttResult = None
        def onMqtt( msg ):
            global mqttResult
            # in results die empfangenen ablegen
            mqttResult = msg
            results[ msg["topic"] ] = msg["payload"]
            mqtt_event.set()
                
        # funktion bei signal aufrufen
        mqtt.signal.connect( onMqtt )
        
        def publishThread( args ):
            global mqttResult
            mqttResult = None
            mqtt_event.clear()
            # Als Thread aufrufen, über mq.get() wird die Rückgabe von  _retrieve abgerufen
            thread = threading.Thread( target=mqtt.publish, args=( args,) )
            thread.start()
            # max 2 sekunden oder auf mqtt_event aus onMqtt warten 
            while not mqtt_event.wait( timeout=3 ):
                mqtt_event.set()
                
            return mqttResult
        
        # die eigenen script infos 
        result = publishThread({
            "topic": "cmnd/status"
        } ) 
    
        self.assertEqual(
            result["topic"], "stat/status", "Fehler bei cmnd/status abfrage")
        
        # python process vorhanden?
        result = publishThread({
            "topic": "cmnd/process",
            "payload" : "python"
        } ) 
        #print("----------------------cmnd/process", result )
        
        self.assertEqual(
            result["topic"], "stat/process", "Fehler bei process abfrage")
        
        # publish ohne topic - publish wird nicht aufgerufen
        # hier wird in publishThread auf timeout gewartet
        result = publishThread({
            "payload": "publish ohne topic - publish wird nicht aufgerufen"
        })
        self.assertIsNone(
            result, "Fehler bei process abfrage")
        
        # publish ohne payload - publish wird mit leerem payload aufgerufen
        result = publishThread({
            "topic": "cmnd/test/leer"
        })
        self.assertEqual(
            result["payload"], "", "Fehler bei leerem payload")
        
        # payload mit object - publish wird mit leerem payload aufgerufen nur (str, bytearray, int, float) ist ok
        result = publishThread({
            "topic": "cmnd/test/object",
            "payload": object()
        })
        self.assertEqual(
            result["payload"], "", "Fehler bei object payload")
        
        # payload als Text
        result = publishThread({
            "topic": "cmnd/test/string",
            "payload": "payload als Text"
        })
        
        self.assertEqual(
            result["payload"], "payload als Text", "Fehler bei text payload")
        
        # payload als dict
        result = publishThread({
            "topic": "cmnd/test/dict",
            "payload": {"text":"payload als dict"}
        })
        self.assertEqual(
            result["payload"], {"text":"payload als dict"}, "Fehler bei dict payload")
        
        # mqtt.client.subscribe( "gqa_dev/logging/#" )


        # mqtt funktionen über logger
        logger = logging.getLogger( "MQTT" )
        
        logger.setLevel( logging.DEBUG )
        
        logger.send()
        logger.send("test/publish")
    
        logger.progressStart( "test" )
        logger.progress( "test", 50 )
        logger.progressReady( "test" )
        
        # test über mqtt anstatt über sofort über logger
        mqtt.logging = True
        mqtt.info("config.info")
        mqtt.warning("config.warning")
        mqtt.error("config.error")
        
        # .. todo:: config ohne mqtt Ausgabe auf der Konsole
        config.mqttCleanup()
       
        mqtt.info("config.info nach cleanup")
        mqtt.warning("config.warning nach cleanup")
        mqtt.error("config.error nach cleanup")
        
        # config mit falschen mqtt Angaben 
        #
        config = ispConfig(  )
        port = config._config.server.mqtt.port
        config._config.server.mqtt.port = 111111
        
        config.mqttInitLogger( cleanup=True )
        
        mqtt = config.mqttGetHandler()
        self.assertIsNone(
            mqtt, "Trotz init Fehler MQTT handler vorhanden")   
        #mqtt.info("config.info nach Fehler bei MQTT config")
        
        config._config.server.mqtt.port = port
        config.mqttInitLogger( cleanup=True )
        
        time.sleep(4) # Sleep for 2 seconds um mqtt zu empfangen
        
        # hier gibt es keine Ausgaben, da mqtt nicht mehr da ist
        logger.info("logger.info nach MQTT init Fehler")
        logger.send("cmnd/test/publish", "nach MQTT init Fehler")
        
        time.sleep(2) # Sleep for 2 seconds um logger mqtt zu empfangen
        
        #print( results )
        
        self.assertIn(
            "cmnd/test/publish", results, "Fehler nach MQTT init Fehler")
        
        #mqtt.publish({
        #    "topic": "cmnd/status"
        #})
        
        
        #  mqtt in config schließen
        config.mqttCleanup( )
        #print( results )
 
    def test_config_files( self ):    
        # einfach config bereitstellen
        config = ispConfig(  )

        temp_conf = { 
            "unittest": True,
            "version" : "0.0.1",
            "variables": {
                "Version" : "0.0.1a",
            },
            "value": 0, 
            "content": "test"
        }

        config = ispConfig( config = temp_conf )
        test = {
            "value" : config.get("value"),
            "content" : config.get("content"),
            "info" : config.get("info")
        } 
        
        self.assertDictEqual(test, {
            "value" : 0,
            "content" : "test",
            "info" : None
        }, "config Rückgabe stimmt nicht")
        
        # Versions Angabe prüfen
        
        # zusätzliche Dateien anlegen
        unitest_json_file_00 = os.path.join( config.BASE_DIR, "config", "config-18200000.json") 
        with open(unitest_json_file_00, 'w') as f:
            f.write( '{ "value": 0, "content": "test" }' )
            
        unitest_json_file_01 = os.path.join( config.BASE_DIR, "config", "config-18200101.json") 
        with open(unitest_json_file_01, 'w') as f:
            f.write( '{ "value": 1, "info": "info 18200101" }' )
         
        unitest_json_file_05 = os.path.join( config.BASE_DIR, "config", "config-18200105.json") 
        with open(unitest_json_file_05, 'w') as f:
            f.write( '{ "value": 5, "info": "info 18200105" }' )
            
        config = ispConfig(  )
        test = {
            "value" : config.get("value"),
            "content" : config.get("content"),
            "info" : config.get("info")
        } 
    
        self.assertDictEqual(test, {
            "value" : 5,
            "content" : "test",
            "info" : "info 18200105"
        }, "config Rückgabe stimmt nicht")
        
        config = ispConfig( lastOverlay="18200101" )
        test = {
            "value" : config.get("value"),
            "content" : config.get("content"),
            "info" : config.get("info")
        } 
 
        self.assertDictEqual(test, {
            "value" : 1,
            "content" : "test",
            "info" : "info 18200101"
        }, "config Rückgabe stimmt nicht")
  
        os.remove( unitest_json_file_00 )
        os.remove( unitest_json_file_01 )
        os.remove( unitest_json_file_05 )
        
        # config-0000.json mit falschen Inhalt erzeugen,
        # Fehler prüfen und Datei wieder löschen
        #
        error_json_file = os.path.join( config.BASE_DIR, "config", "config-0000.json") 
        with open(error_json_file, 'w') as f:
            f.write( "#Falscher Inhalt" )
            
        config = ispConfig()
        
        self.assertEqual(
            config._loadErrors, [ error_json_file ], "load error wurde nicht ausgelöst")
        os.remove( error_json_file )

    def test_config_jinja(self):    
        '''jinja Template Funktionen der config testen.
        
        '''

        # eine eigene config mit resources im tests Ordner
        config = ispConfig( config={
            "server": {
                "webserver": {
                    "resources" : os.path.join( ABSPATH, "resources" )
                }
            }
        })
        
        # das aktuelle datum
        datum = datetime.now().strftime('%d.%m.%Y')
        
        result_A = """<ul>
<li>testuser</li>
</ul>
        <h2>Markdown</h2>
<ul>
<li>Datum aus variables <strong>Datenausgabe</strong> :{{Datenausgabe}}</li>
<li>Inhalt aus variables<ul>
<li>Version: </li>
<li>render_mode: </li>
</ul>
</li>
</ul>

<h2>icon</h2>
<i class="mdi mdi-check-outline green-text"></i>

<img src="/test.svg" alt="test.svg" />
        Datum mit now: #datum#""".replace( "#datum#", datum )

        result_B = """<ul>
<li>testuser</li>
</ul>
        <h2>Markdown</h2>
<ul>
<li>Datum aus variables <strong>Datenausgabe</strong> :#datum#</li>
<li>Inhalt aus variables<ul>
<li>Version: </li>
<li>render_mode: </li>
</ul>
</li>
</ul>

<h2>icon</h2>
<i class="mdi mdi-check-outline green-text"></i>

<img src="/test.svg" alt="test.svg" />
        Datum mit now: #datum#""".replace( "#datum#", datum )
         
        meta = {
            "user" : "testuser",
            "Datenausgabe": "{{ now.strftime('%d.%m.%Y') }}",
            "name": "{{user}}"
        }
        
        tpl = """{% markdown %}
        * {{ user }}
        {% endmarkdown %}
        {% include "test_template.jinja" %}
        Datum mit now: {{ now.strftime('%d.%m.%Y') }}"""
        
        result = config.render_template( tpl, meta, deep_replace=False )
        
        self.assertEqual(result, result_A, "template nicht OK")
        
        result = config.render_template( tpl, meta, deep_replace=True )   
        
        self.assertEqual(result, result_B, "template nicht OK")
        
        
    def test_webapp_base_system( self ):
        ''' Webapp Aufruf auf system funktionen
       
        '''             
        response = self.app.get( "api/system" ) 
        self.assertEqual(response.status_code, 200, "Api Status nicht 200")
        
        response = self.app.get( "api/system",  query_string = { "format" : "html" } ) 
        self.assertEqual(response.status_code, 200, "Api Status nicht 200")
        
        response = self.app.get( "api/system/test",  query_string = { "zahl" : 12 } ) 
        self.assertEqual(response.status_code, 200, "Api Status nicht 200")
        self.assertDictEqual( 
            response.json["data"], 
            { "_ispcp": {}, "bool": False, "text": "typenlos", "zahl": 12.0},
            "Response data nicht OK"
        )
        
        response = self.app.get( "api/system/15" ) 
        self.assertEqual(response.status_code, 200, "Api Status nicht 200")
        self.assertDictEqual( 
            response.json["data"]["kwargs"], 
            {'format': 'html', 'info': 'kwargs', 'systemId': '15'},
            "Response data nicht OK"
        )
        # print("test_webapp_base_system", response.json )
        
    def test_webapp_base_statics( self ):
        ''' Webapp Aufruf auf Statische Inhalte 
       
        '''           
       
        # index auf zwei arten aufrufen
        response = self.app.get( "/" ) 
        #self.assertEqual(response.status_code, 200, "Api Status nicht 200")
        index = response.data
        
        response = self.app.get( "/render/index", query_string = {
            "zahl":"012",
            "bool":True,
            "test":1,
            "_ispcp": json.dumps( {"name":"B"} )
            } ) 
        self.assertEqual(response.status_code, 200, "Api Status nicht 200")
        self.assertEqual(index, response.data, "index und render/index nicht gleich")
        
        # render auf nicht auf nicht vorhandenes Template in ui 
        response = self.app.get( "/render/keintemplate" )
        self.assertEqual(response.status_code, 404, "render auf nicht auf nicht vorhandenes Template in ui")

        # load auf nicht vorhandene Datei testen
        response = self.app.get( "/globals/js/keinedatei" )
        self.assertEqual(response.status_code, 404, "load auf nicht vorhandene Datei")
        
        
        # in ui eine unittest_route.phtml erzeugen 
        route_file = os.path.join( ABSPATH , "..", "ui", "unittest_route.phtml") 
        
        with open(route_file, 'w') as f:
            f.write( "value={{ value }}" )
        
        # ohne parameter
        response = self.app.get( "/unittest_route" )
        self.assertEqual(response.status_code, 200, "Api Status nicht 200")
        
        self.assertEqual(response.data, b"value=None", "Inhalt ist nicht value=None;_ispcp=")
        
        # zwei gleiche parameter (nur der erste wird verwendet)
        response = self.app.get( "/unittest_route?value=12&value=1" )
        self.assertEqual(response.status_code, 200, "Api Status nicht 200")
        
        self.assertEqual(response.data, b"value=12", "Inhalt ist nicht value=12;_ispcp= FirstValueURIParser")
        
        # unittest_route.phtml in ui wieder entfernen
        os.remove( route_file )
        
        # in ui eine unittest_route_ispcp.phtml erzeugen 
        route_file1 = os.path.join( ABSPATH , "..", "ui", "unittest_route_ispcp.phtml") 
        
        with open(route_file1, 'w') as f:
            f.write( "{{ params }}" )
            
        # Parameter als dict
        response = self.app.get( '/unittest_route_ispcp' , query_string = {
            "name":"A",
            "uuid":1,
            "id":1,
            "_ispcp": json.dumps( {"name":"B"} )
            } ) 
        
        self.assertEqual(response.status_code, 200, "Api Status nicht 200")  
        self.assertDictEqual( json.loads( response.data.decode('utf-8') ), {"uuid": "1", "id": "1", "name": "B"}, "Inhalt ist nicht mit dict")
        
        # unittest_route_ispcp.phtml in ui wieder entfernen
        os.remove(route_file1)
        
        #
        # mit fehler bei _ispcp
        response = self.app.get( "/render/index", query_string = {
            "zahl":"012",
            "bool":True,
            "test":1,
            "_ispcp":  "name"
            } ) 
        self.assertEqual(response.status_code, 200, "Api Status nicht 200")
                

    def test_webapp_base_extras( self ):
        ''' Website Aufruf für zusätzliche Inhalte 
       
        '''       
        
        # htmlcov laden geht nur wenn es schon erzeugt wurde 
        htmlcov_path = osp.join( ABSPATH , "..", ".htmlcov")
        if osp.isdir( htmlcov_path ):
            response = self.app.get( "/coverage" ) 
            self.assertEqual(response.status_code, 200, "Api Status nicht 200")
            response = self.app.get( "/coverage/coverage.css" ) 
            self.assertEqual(response.status_code, 200, "Api Status nicht 200")
        else:
            print( "(coverage) Test erst nach dem Erstellen möglich." )
            
        # über resources laden
        response = self.app.get( "resources/logo.png" ) 
        self.assertEqual(response.status_code, 200, "Api Status nicht 200")
        
        # über fonts laden aber mit Fehler für coverage
        response = self.app.get( "fonts/irgendwas" ) 
        self.assertEqual(response.status_code, 404, "Api Status nicht 404")
        
        # über dbadminframe laden
        response = self.app.get( "dbadminframe" ) 
        self.assertEqual(response.status_code, 200, "Api Status nicht 200")
        
        # docs iframe laden 
        response = self.app.get( "/docs" ) 
        self.assertEqual(response.status_code, 200, "Api Status nicht 200")

        # /docs/ wird zu /docs also auch iframe laden
        response = self.app.get( "/docs/" ) 
        self.assertEqual(response.status_code, 200, "Api Status nicht 200")
        
        # docs laden (beim ersten Aufruf erzeugen)
        response = self.app.get( "/docs/index.html" ) 
        # es kommt vor das erst beim 2. Aufruf alles erzeugt wird
        if response.status_code == 404:
            # 2. Versuch
            response = self.app.get( "/docs/index.html" ) 
        # jetzt OK
        self.assertEqual(response.status_code, 200, "docs Aufruf Api Status nicht 200. Wurde docs erzeugt?")
        
        # dbadmin laden
        response = self.app.get( "/dbadmin" ) 
        self.assertEqual(response.status_code, 200, "Api Status nicht 200")       

        # neue webapp ohne parameter
        webbapp =ispBaseWebApp(  )
        self.assertEqual(webbapp._config.get("server.webserver.TESTING"), True, "Testing ist nicht True")
        
        # neue webapp mit dict nur mit TESTING Angabe
        webbapp =ispBaseWebApp( {"server" : {"webserver" : { "TESTING": True } } } )
        self.assertEqual(webbapp._config.get("server.webserver.TESTING"), True, "Testing ist nicht True")

        
    def test_webapp_base_api( self ):
               
        # Inhalt von swagger mit der Angabe in custom_swagger_path prüfen
        response = self.app.get( "api/swagger.json" ) 
        self.assertEqual(response.status_code, 200, "Api Status nicht 200")
    
        self.assertEqual( 
            response.json["info"]["title"], "test_isp", "swagger file nicht ok")
         
        self.assertEqual( 
            list( response.json["paths"].keys() ),
            ['/dbtests/', '/dbtests/groupby', '/dbtests/groupsplit', '/dbtests/pandas', '/dbtests/test', '/dbtests/undefined', '/dbtests/{dbtestsId}/', '/dbtests/{dbtestsId}/dbtestsrel',
             '/dbtestsrel/', '/dbtestsrel/groupby', '/dbtestsrel/groupsplit', '/dbtestsrel/undefined', '/dbtestsrel/{dbtestsrelId}/', '/dbtestsrel/{dbtestsrelId}/dbtests',
             '/dummy/', '/dummy/pdf', '/dummy/test', '/dummy/{dummyId}/',
             '/system/', '/system/test', '/system/{systemId}/'
            ],
            "Fehlerhafte paths Angaben in swagger.json")
        
        response = self.app.get( "api/gibtsnicht" ) 
        self.assertEqual(response.status_code, 404, "Fehlerhafter api Zugriff ist nicht 404")
        
        
    def test_webapp_dummy_test( self ):
        ''' Api aufruf durchführen 
        GET /api/dummy/
 
        '''
        
        # --- dummy Klasse abfragen
        
        # dummy api_list abfragen
        response = self.app.get( "api/dummy" )  
        self.assertEqual(response.status_code, 200, "Api Status nicht 200")
       
        self.assertEqual( 
            response.json["data"], [{
                'attributes': {'function': 'api_list', 'kwargs': {'_ispcp': {}}}, 
                'id': '12', 
                'links': {'self': 'http://localhost/api/dummy/12/'}, 
                'type': 'dummy'
            }],
            "falsche api_list Rückgabe"
        ) 
        
        
        # dummy api_get abfragen wird dummyId mitgegeben
        response = self.app.get( "api/dummy/12" )  
        self.assertEqual(response.status_code, 200, "Api Status nicht 200")
        #print(response.json["data"][0])
        self.assertDictEqual( 
            response.json["data"], {
                'attributes': {'dummyId': '12'}, 
                'id': 12, 
                'links': {'self': 'http://localhost/api/dummy/12/'}, 
                'type': 'dummy'
            },
            "falsche id Rückgabe"
        ) 
        #print( response.json )
       
        
        # ohne Pflichfeld Angabe test gibt es nicht
    
        response = self.app.get( "api/dummy/test" ) 
        # print("api/dummy/test", response.json )
        self.assertEqual(response.status_code, 400, "Api Status nicht 400")
        self.assertDictEqual( 
            response.json,
            {
                "message": {
                    "zahl": "Eine Zahl"
                }
            },
            "nicht abgelehnt ohne Pflichfeld Angabe"
        ) 
        
        # ohne text (hat default) mit test (nicht vorhanden)
        # /api/system/test?zahl=012&bool=True&test=1&_ispcp={"name":"B"}
        response = self.app.get( "api/dummy/test", query_string={
            "zahl":"012",
            "bool":True,
            "test":1,
            "_ispcp": json.dumps( {"name":"B"} )
            } ) 
        # kommen auch zusätzliche Angaben und werden unnötige ausgefiltert
        self.assertEqual(response.status_code, 200, "Api Status nicht 200")
        self.assertDictEqual( 
            response.json["data"],
            {
                "_ispcp": {"name": "B"}, 
                "bool": True, 
                "text": "typenlos", 
                "zahl": 12.0
            },
            "Parameter Auswertung falsch"
        ) 
        
        response = self.app.get( "api/dummy/undefined" )
        
        # einen undefined holen
        self.assertEqual(response.status_code, 200, "Api Status nicht 200")
        self.assertEqual( 
            response.json["data"],
            {'attributes': {}, 'id': 'undefined', 'type': 'dummy'},
            "undefined fehlerhaft"
        )            
               
        # Dummy ohne funktion gibt undefined Datensatz 
        response = self.app.get( "api/dummy/gibtsnicht" )
        self.assertEqual(response.status_code, 200, "Api Status nicht 200")
        self.assertEqual( 
            response.json["data"],
            { 'attributes': {}, 'id': 'undefined', 'type': 'dummy' },
            "Dummy ohne funktion gibt keine undefined datensatz "
        )  
        
        
        # 
        response = self.app.get( "api/dummy/test", query_string={ "zahl": 1 } )
        self.assertEqual(response.status_code, 200, "Status nicht 200")
        self.assertEqual( 
            response.json["data"],
            [],
            "Test leere Liste"
        )
        response = self.app.get( "api/dummy/test", query_string={ "zahl": 2 } )
        self.assertEqual(response.status_code, 200, "Status nicht 200")
        self.assertEqual( 
            response.json["data"],
            [{"a": 1, "b": 2}],
            "Test Liste mit einem Element"
        )  
        
        # fehler bei der Umwandlung data bleibt leer
        response = self.app.get( "api/dummy/test", query_string={ "zahl": 3 } )
        self.assertEqual(response.status_code, 200, "Status nicht 200")
        self.assertEqual( 
            response.json["data"],
            [],
            "fehler bei der Umwandlung data bleibt leer"
        )  
        
        response = self.app.get( "api/dummy/test", query_string={ "zahl": 4 } )
        self.assertEqual(response.status_code, 200, "Status nicht 200")

        response = self.app.get( "api/dummy/test", query_string={ "zahl": 5, "_ispcp" : "{test}"} )
        self.assertEqual(response.status_code, 200, "Status nicht 200")
        self.assertEqual( 
            response.json['errors'],
            [{'title': 'swagger Parameter Json Error', 'detail': '_ispcp={test}', 'code': None}],
            "Parameter Json Error"
        )  
        
        # _int_query selbst aufrufen
        response = self.app.get( "api/dummy/test", query_string={ "zahl": 6 } )       
        self.assertEqual(response.status_code, 200, "Status nicht 200")
        self.assertEqual( 
            response.json['data'],
            [{'A': 1}, {'B': 2}],
            "Parameter Json Error"
        )  
 
        # _int_group_query selbst aufrufen
        response = self.app.get( "api/dummy/test", query_string={ "zahl": 7 } )
        
        self.assertEqual(response.status_code, 200, "Status nicht 200")
        self.assertEqual( 
            response.json['errors'],
            [],
            # [{'message': 'Fehler bei _int_group', 'info': "'dummyQuery' object has no attribute 'group_by'"}],
            "_int_group_query selbst aufrufen"
        )  
        
        # access_cls selbst aufrufen
        response = self.app.get( "api/dummy/test", query_string={ "zahl": 8 } )       
        self.assertEqual(response.status_code, 200, "Status nicht 200")
        self.assertEqual( 
            response.json['data'],
            [{'nicht da': ''}, {'sqlalchemy.BigInteger': ''}],
            "access_cls selbst aufrufen"
        )      
        
        # iso2date aufrufen
        response = self.app.get( "api/dummy/test", query_string={ "zahl": 9 } )

        self.assertEqual(response.status_code, 200, "Status nicht 200")
        self.assertEqual( 
            response.json['data'],
            [
                {'test=None': None}, 
                {'20180415=2018-04-15': '2018-04-15'}, 
                {'2018-04-15=2018-04-15': '2018-04-15'}, 
                {'2018-04-15=2018-04-15': '2018-04-15'}, 
                {'2018-04-15 14:36:25=2018-04-15': '2018-04-15'}, 
                {'2018-04-15=18-04-15 00:00:00': '2018-04-15 00:00:00'}, 
                {'2018-04-15 14:36:25=2018-04-15 14:36:25': '2018-04-15 14:36:25'}, 
                {'20180415 14:36:25=2018-04-15 14:36:25': '2018-04-15 14:36:25'}, 
                {'20180415 14:36=2018-04-15 14:36:00': '2018-04-15 14:36:00'}, 
                {'201A0415 14:36:25=None': None}, 
                {'201A0415 14:36=None': None}, 
                {'201A0415=None': None}
            ],
            "iso2date aufrufen"
        )    
        
        # versuchen eine vorhandene Funktion ohne rpc Kennung aufzurufen
        response = self.app.get( "api/dummy/norpc" )
        self.assertEqual(response.status_code, 400, "Status nicht 400")
        
        self.assertEqual( 
            response.json,
            {},
            "versuchen eine vorhandene Funktion ohne rpc Kennung aufzurufen"
        )  
        
        
        #print( response.json )
        
        
    def test_webapp_db_tests_A( self ):
        ''' Api aufruf durchführen 
        GET /tests/
 
        ''' 
        
        # zuerst den zugriff testen und prüfen ob die tabelle 5 datensätze hat
        #
        response = self.app.get( "api/dbtests/", query_string={})
        self.assertEqual(response.status_code, 200, "Api Status nicht 200")
        self.assertEqual( 
            len(response.json["data"]), 8, "keine 8 Datensätze"
        ) 
        
        return
    
        #
        # einen Datensatz zusätzlich einfügen
        #
        response = self.app.post( "api/dbtests/", headers={'Content-Type': 'application/json'}, data=json.dumps({ 
            "data" : {
                "attributes": {
                    "string":"sechs",     # Pflichtfeld
                    #"date":"2020-08-19", 
                    "integer":6
                },
                "type":"dbtests"
            }

        }), follow_redirects=True) 
        
        self.assertEqual(response.status_code, 201, "Api Status nicht 201 (Created)")
        self.assertEqual( response.json["data"]["id"], '6', "Datensatz id ist nicht 6")
        
        
        # record merken
        newRecord6 = response.json["data"]["attributes"]
        id6 = response.json["data"]["id"]
        link6 = response.json["data"]["links"]["self"]
        
        #
        # einen zweiten einfügen
        #
        response = self.app.post( "api/dbtests/", headers={'Content-Type': 'application/json'}, data=json.dumps({ 
            "data" : {
                "attributes": {
                    "string":"sieben",     # Pflichtfeld
                    #"date":"2020-08-19", 
                    "integer":7
                },
                "type":"dbtests"
            }

        }), follow_redirects=True) 
        self.assertEqual(response.status_code, 201, "Api Status nicht 201 (Created)")
        self.assertEqual( response.json["data"]["id"], '7', "Datensatz id ist nicht 7")
        # record merken
        newRecord7 = response.json["data"]["attributes"]
        id7 = response.json["data"]["id"]
        link7 = response.json["data"]["links"]["self"]

        
        #
        # jetzt alle holen und prüfen 
        #
        response = self.app.get( "api/dbtests/")
        self.assertEqual(response.status_code, 200, "Api Status nicht 200")
        
        self.assertEqual( len(response.json["data"]), 7, "Datensatzanzahl ist nicht 7")
        id = response.json["data"][5]["id"] # zählung ab 0 (5 ist record 6)
        record = response.json["data"][5]["attributes"]
        link = response.json["data"][5]["links"]["self"]
        self.assertEqual( id, id6, "Datensatz id=6 vom ersten stimmt nicht")
        self.assertEqual( record, newRecord6, "Datensatz Inhalt vom ersten stimmt nicht")
        
        #
        # den siebten Datensatz über den angegebenen link holen
        #
        response = self.app.get( link7 )
        
        self.assertEqual( response.json["data"]["id"], '7', "Datensatz Id Rückgabe ist nicht 7")
        self.assertEqual( type(response.json["data"]), dict, "Datensatz data ist kein dict")
        # Inhalt vergleichen
        self.assertEqual( response.json["data"]["attributes"], newRecord7, "Datensatz Inhalt stimmt nicht")
        
        #
        # siebten Datensatz ändern - die id muss in body und path angegeben werden
        #
        response = self.app.patch( link7, headers={'Content-Type': 'application/json'}, data=json.dumps({ 
            "data" : {
                "attributes": {
                   # "date":"2020-08-19 00:00",  # 2020-08-20, 00:00
                   "string":"changed",
                },
                "id": '7',
                "type":"dbtests"
            }

        }), follow_redirects=True) 
        
        # 200 - Request fulfilled, document follows
        self.assertEqual(response.status_code, 200, "Api Status nicht 200")
        # Inhalt darf nicht mehr gleich sein
        self.assertNotEqual( response.json["data"], newRecord7, "Datensatz Inhalt ist noch gleich")
        
        #
        # den zweiten Datensatz über den angegebenen link holen und Änderungen prüfen
        #
        response = self.app.get( link7 )        
        self.assertEqual(response.status_code, 200, "Api Status nicht 200")
        self.assertEqual( response.json["data"]["attributes"]["string"], "changed", "Feldinhalt ist nicht changed")
        
        # alle holen
        response = self.app.get( "api/dbtests/")
        self.assertEqual(response.status_code, 200, "Api Status nicht 200")
        lastCount = len(response.json["data"] )
        
        # Datensatz 6 und 7 löschen
        response = self.app.delete( link6, headers={'Content-Type': 'application/json'} )

        self.assertEqual(response.status_code, 204, "Api Status nicht 204")
        # alle verbleibenden holen und Anzahl prüfen
        response = self.app.get( "api/dbtests/")
        self.assertEqual(response.status_code, 200, "Api Status nicht 200")
        self.assertEqual(len(response.json["data"] ), lastCount - 1 , "Api Status nicht {}".format( lastCount - 1 ))
        
         # jetzt noch 7 löschen
        response = self.app.delete( link7, headers={'Content-Type': 'application/json'} )
        self.assertEqual(response.status_code, 204, "Api Status nicht 204")       
        
        # nach dem löschen Anzahl prüfen
        response = self.app.get( "api/dbtests/", query_string={})
        self.assertEqual(response.status_code, 200, "Api Status nicht 200")
        self.assertEqual( 
            len(response.json["data"]), 5, "keine 5 Datensätze nach dem löschen von 6 und 7"
        ) 
        
        # fehler bei falschem patch 
        response = self.app.patch( link7, headers={'Content-Type': 'application/json'}, data=json.dumps({ 
            "data" : {
                "attributes": {
                   "string_gibtsnicht":"changed",
                },
                "id": '99',
                "type":"dbtests"
            }

        }), follow_redirects=True) 
         
        self.assertEqual(response.status_code, 500, "Api Status nicht 500")
        self.assertEqual(
            response.json["App-Error"],
            [{'message': 'patch - unbekannter Fehler', 'info': '500'}],
            "fehler bei falschem patch"
        )
        
        
    def test_webapp_db_tests_rqlFilter( self ):
        ''' Api aufruf durchführen 
        GET /tests/
 
        '''         
                 
        # einen undefined holen
        response = self.app.get( "api/dbtests/undefined")
        self.assertEqual(response.status_code, 200, "Api Status nicht 200")
        self.assertEqual(
            response.json["data"],
            {'attributes': {
                'active': None, 
                'data': None, 
                'date': None, 
                'decimal': None,
                'float': None, 
                'gruppe': None, 
                'integer': None, 
                'isodate': None,
                'isodatetime': None,
                'numeric': None, 
                'string': None, 
                'tags': None
            }, 'id': 'undefined', 'type': 'dbtests'},
            "einen undefined holen"
        )
 
        # keine fehler 
        response = self.app.get( "api/dbtests/", query_string={
            "art" : "rqlFilter", 
            "filter" : "eq(id,1)"
        })      
        self.assertEqual(response.status_code, 200, "Api Status nicht 200")
        self.assertEqual( len(response.json["data"]), 1, "eq(id,1) hat keine Daten")
        
        # leere rückgabe bei nicht vorhandener value 
        response = self.app.get( "api/dbtests/", query_string={
            "art" : "rqlFilter", 
            "filter" : "eq(id,appDialog)"
        })
        self.assertEqual(response.status_code, 200, "Api Status nicht 200")
        self.assertEqual(response.json["data"], [], "eq(id,appDialog) hat Daten")
        self.assertEqual(
            response.json["infos"]["rql"],
            [
                {'title': 'filter', 'detail': 'eq(id,appDialog)', 'code': None}, 
                {'title': '_rql_where_clause', 'detail': {
                    'where': 'dbtests.id = :id_1', 'params': {'id_1': 'appDialog'}
                }, 'code': None }
            ], "eq(id,appDialog)" )
        
        response = self.app.get( "api/dbtests/", query_string={
            "art" : "rqlFilter", 
            "filter" : "and(eq(active,true),lt(float,numeric))"
        })
        self.assertEqual(response.status_code, 200, "Api Status nicht 200")
        
        # Fehler bei falscher Filterangabe 
        response = self.app.get( "api/dbtests/", query_string={
            "art" : "rqlFilter", 
            "filter" : "eq(id=1)"
        })      
        self.assertEqual(response.status_code, 200, "Api Status nicht 200")
        self.assertEqual(response.json["data"], [], "eq(tid=1) hat Daten")
        self.assertEqual(response.json["errors"],[{
            'title': '_int_rqlfilter', 
            'detail': 'rql-error: RQL Syntax error: (\'eq(id=1)\', 5, \'Expected ")"\')',
            'code': None
        } ], "Fehler bei falscher Filterangabe - eq(id=1)")
        
        response = self.app.get( "api/dbtests/", query_string={
            "art" : "rqlFilter", 
            "filter" : "eq(tid=1)"
        })
        #print("AppInfo203", response.json)
        self.assertEqual(response.status_code, 200, "Api Status nicht 200")
        self.assertEqual(response.json["data"], [], "eq(tid=1) hat Daten")
        self.assertEqual(response.json["errors"],[{
            'title': '_int_rqlfilter', 
            'detail': 'rql-error: RQL Syntax error: (\'eq(tid=1)\', 6, \'Expected ")"\')',
            'code': None
        } ], "Fehler bei falscher Filterangabe - eq(tid=1)")
        
        
        # einen nicht vorhandenen Datensatz abrufen
        # FIXME: Meldung auf der Konsole unterdrücken in method_wrapper vorher abfangen ?
        
        response = self.app.get( "api/dbtests/100")
        self.assertEqual(response.status_code, 404, "Api Status nicht 404 - notFound")

        
    def test_webapp_db_filter( self ):
        ''' Api aufruf durchführen 
        GET /dbtests?filter=
 
        '''         
       
        response = self.app.get( "api/dbtests/", query_string={
            "art" : "filter field", 
            "filter" : '[{"name":"string","op":"eq","val":"one"}]'
        })
        self.assertEqual(response.status_code, 200, "Api Status nicht 200")
        
        self.assertEqual( len(response.json["data"]), 1, "Anzahl filter field stimmt nicht")
        
        response = self.app.get( "api/dbtests/", query_string={
            "art" : "filter query", 
            "filter[string]" : "one"
        })
        self.assertEqual(response.status_code, 200, "Api Status nicht 200")
        self.assertEqual( len(response.json["data"]), 1, "Anzahl filter query stimmt nicht")
        
        response = self.app.get( "api/dbtests/", query_string={
            "art" : "filter rql", 
            "filter" : "eq(string,one)"
        })
        self.assertEqual(response.status_code, 200, "Api Status nicht 200")
        self.assertEqual( len(response.json["data"]), 1, "Anzahl filter rql stimmt nicht")
        
        response = self.app.get( "api/dbtests/", query_string={
            "art" : "filter search", 
            "filter" : "*one"
        })
        self.assertEqual(response.status_code, 200, "Api Status nicht 200")

        self.assertEqual( len(response.json["data"]), 2, "Anzahl filter search stimmt nicht")
        
        response = self.app.get( "api/dbtests/", query_string={
            "art" : "filter mixed", 
            "filter" : '[{"name":"active","op":"eq","val":true}]|*one'
        })
        self.assertEqual(response.status_code, 200, "Api Status nicht 200")
        self.assertEqual( len(response.json["data"]), 2, "Anzahl filter search stimmt nicht")
      
        
    def test_webapp_db_tests_C( self ):           
        # funktion test in dbtests aufrufen
        response = self.app.get( "api/dbtests/test", query_string={
            "art" : 'AppInfo203' 
        })
           
    
        self.assertEqual(response.status_code, 203, "Api Status nicht 203")
        self.assertEqual(
            response.json["infos"]["general"],
            [{'title': 'Test AppInfo', 'detail': 'App-Info mit code 203', 'code': 203}],
            "AppInfo203 fehlgeschlagen"
        )
        
        response = self.app.get( "api/dbtests/test", query_string={
            # ohne das Pflichtfeld art
        })
        self.assertEqual(response.status_code, 400, "Api Status nicht 400")
        self.assertEqual(
            response.json["message"],
            {'art': 'bestimmt die Art des Tests'},
            "Fehlende message bei fehlendem Pflichtfeld"    
        )
        
        response = self.app.get( "api/dbtests/test", query_string={
            "art" : 'query' 
        })
        self.assertEqual(response.status_code, 200, "Api Status nicht 200")
        self.assertEqual(
            response.json['infos']['query'],
            [{
                'title': 'sql-lastquery', 
                'detail': 'query is None', 
                'code': None
            }, {
                'title': 'sql-lastquery', 
                'detail': {
                    'query': 'SELECT dbtests.string \nFROM dbtests', 
                    'params': {}}, 
                'code': None
            }],
            "Fehlende message bei fehlendem Pflichtfeld"    
        )

        response = self.app.get( "api/dbtests/test", query_string={
            "art" : 'AppDialog' 
        })
        self.assertEqual(response.status_code, 200, "Api Status nicht 203")
       
        self.assertEqual(
            response.json["errors"],
            [],
            "error Meldung sollte nicht sein"    
        )
        self.assertEqual(
            response.json["infos"]["dialog"],
            [{
                'title': 'Test AppDialog', 
                'detail': {
                    'content': 'Einfach nur ein Dialog', 
                    'dimensions': [200, 200], 
                    'title': 'Test AppDialog'
                }, 
                'code': None
            }],
            "Fehler bei der Dialog Meldung"    
        )
        
        response = self.app.get( "api/dbtests/test", query_string={
            "art" : 'AppDialog403' 
        })
  
        
        self.assertEqual(response.status_code, 403, "Api Status nicht 403")
        self.assertEqual(
            response.json["infos"]["dialog"],
            [{
                'title': 'Test AppDialog', 
                'detail': {
                    'content': 'AppDialog mit AppError und code 403', 
                    'dimensions': [200, 200], 
                    'title': 'Test AppDialog'
                }, 
                'code': 403
            }],
            "Fehler bei der Dialog Meldung"    
        )
  
    
        response = self.app.get( "api/dbtests/test", query_string={
            "art" : 'AppError' 
        })

        self.assertEqual(response.status_code, 200, "Api Status nicht 200")
        self.assertEqual(
            response.json["errors"],
            [{
                'title': 'Test AppError', 
                'detail': 'App-Error ohne code', 
                'code': None
            }],
            "error Meldung ist falsch"    
        )
        
        response = self.app.get( "api/dbtests/test", query_string={
            "art" : 'AppError403' 
        })
        self.assertEqual(response.status_code, 403, "Api Status nicht 403")
        self.assertEqual(
            response.json["errors"],
            [{
                'title': 'Test AppError', 
                'detail': 'App-Error mit code 403', 
                'code': 403
            }],
            "error Meldung ist falsch"    
        )

        
        response = self.app.get( "api/dbtests/test", query_string={
            "art" : 'AppInfo' 
        })

        self.assertEqual(response.status_code, 200, "Api Status nicht 200")
        self.assertEqual(
            response.json["infos"]["general"],
            [{
                'title': 'Test AppInfo', 
                'detail': 'App-Info ohne code', 
                'code': None
            }],
            "error Meldung ist falsch"    
        )
       
 
        
        response = self.app.get( "api/dbtests/test", query_string={
            "art" : 'AppInfo203' 
        })
        self.assertEqual(response.status_code, 203, "Api Status nicht 203")
        self.assertEqual(
            response.json["infos"]["general"],
            [{
                'title': 'Test AppInfo', 
                'detail': 'App-Info mit code 203', 
                'code': 203
            }],
            "error Meldung ist falsch"    
        )
               
     
        
    def test_webapp_db_relation( self ):
        ''' Api aufruf für relative Tabellen 
        
        api/dbtestsrel?filter=eq(dbtests_id,2)
            [{'attributes': {'dbtests_id': 2, 'rdata': None, 'rdate': None, 'rgroup': 'B', 'rinteger': 12, 'rstring': 'r_zwei'}, 'id': '2', 'links': {'self': 'http://localhost/api/dbtestsrel/2/'}, 'relationships': {'dbtests': {'data': None, 'links': {'self': 'http://localhost/api/dbtestsrel/2/dbtests'}}}, 'type': 'dbtestsrel'}]
        ''' 
        
        
        # zuerst den zugriff testen und prüfen ob die tabelle leer ist
        #
        response = self.app.get( "api/dbtests/")
        self.assertEqual(response.status_code, 200, "Api Status nicht 200")
        self.assertEqual( 
            len( response.json["data"] ), 8, "keine 8 Datensätze"
        ) 
        
        response = self.app.get( "api/dbtestsrel/")
        self.assertEqual(response.status_code, 200, "Api Status nicht 200")
        self.assertEqual( 
            len(response.json["data"]), 5, "keine 5 Datensätze"
        ) 
        
        # daten über path und filter müssen gleich sein nur die globale links Angabe unterscheidet sich
        # http://127.0.0.1:5000/api/nutzung?_ispcp={%22_default%22:{%22ersatz_id%22:1754}}&filter=eq(ersatz_id,1754)&page[offset]=0&page[limit]=25
        response = self.app.get( "api/dbtests/2/dbtestsrel")
        self.assertEqual(response.status_code, 200, "Api Status nicht 200")
        reldata = response.json
        
 
        response = self.app.get( "api/dbtestsrel", query_string={
            "filter":"eq(dbtests_id,2)"
        })
        self.assertEqual(response.status_code, 200, "Api Status nicht 200")
        self.assertEqual(
            reldata["data"], response.json["data"], 
            "Rückgaben sind nicht gleich"
        )       
        
        
    def test_webapp_db_groupby( self ):
        ''' Api aufruf für relative Tabellen 
        # ohne group Angabe wird fields verwendet
            /api/<modul>/groupby?fields[<modul>]=<feld1>
        # mit group 
            /api/<modul>/groupby?fields[<modul>]=<feld1,feld2>&groups=<feld1,feld2>
        # mit group und delimiter
            /api/<modul>/groupby?fields[<modul>]=<feld1,feld2>&groups[<modul>]=<feld1,feld2>&delimiter=,
        # mit Filter
            /api/<modul>/groupby?fields[<modul>]=<feld1,feld2>&filter=eq(aktiv,true)
        # mit labels
            /api/<modul>/groupby?fields[<modul>]=<feld1,feld2>&labels={"dbtests.gruppe": "Hallo"}
        ''' 
  
        # mit fields Angabe
        response = self.app.get( "api/dbtests/groupby", query_string={
            "fields[dbtests]":"gruppe"
        })
        self.assertEqual(response.status_code, 200, "Api Status nicht 200")
        
        self.assertEqual( response.json["data"],[
            {'attributes': {'hasChildren': 2, 'gruppe': 'A'}, 'id': None, 'type': 'dbtests'}, 
            {'attributes': {'hasChildren': 2, 'gruppe': 'B'}, 'id': None, 'type': 'dbtests'}, 
            {'attributes': {'hasChildren': 3, 'gruppe': 'C'}, 'id': None, 'type': 'dbtests'},
            {'attributes': {'hasChildren': 1, 'gruppe': 'D'}, 'id': None, 'type': 'dbtests'}
        ], "groupby mit fields Angabe Rückgabe fehlerhaft " )
        
        # mit groups Angabe
        response = self.app.get( "api/dbtests/groupby", query_string={
            "groups":"gruppe"
        })
        self.assertEqual(response.status_code, 200, "Api Status nicht 200")
        self.assertEqual( response.json["data"],[
            {'attributes': {'hasChildren': 2, 'gruppe': 'A'}, 'id': None, 'type': 'dbtests'}, 
            {'attributes': {'hasChildren': 2, 'gruppe': 'B'}, 'id': None, 'type': 'dbtests'}, 
            {'attributes': {'hasChildren': 3, 'gruppe': 'C'}, 'id': None, 'type': 'dbtests'},
            {'attributes': {'hasChildren': 1, 'gruppe': 'D'}, 'id': None, 'type': 'dbtests'}
        ], "groupby mit groups Angabe Rückgabe fehlerhaft " )
        
         # mit groups Angabe und filter
        response = self.app.get( "api/dbtests/groupby", query_string={
            "groups":"gruppe",
            "filter":"eq(active,true)"
        })
        self.assertEqual(response.status_code, 200, "Api Status nicht 200")
        self.assertEqual( response.json["data"],[
            {'attributes': {'hasChildren': 2, 'gruppe': 'A'}, 'id': None, 'type': 'dbtests'}, 
            {'attributes': {'hasChildren': 1, 'gruppe': 'B'}, 'id': None, 'type': 'dbtests'}, 
            {'attributes': {'hasChildren': 2, 'gruppe': 'C'}, 'id': None, 'type': 'dbtests'},
            {'attributes': {'hasChildren': 1, 'gruppe': 'D'}, 'id': None, 'type': 'dbtests'}
        ], "groupby mit groups Angabe Rückgabe fehlerhaft " )
        
        # mit Filter und zwei Gruppierungs Feldern
        response = self.app.get( "api/dbtests/groupby", query_string={
            "groups[dbtests]":"gruppe,tags",
            "filter":"eq(active,true)"
        })
        self.assertEqual(response.status_code, 200, "Api Status nicht 200")
        self.assertEqual( response.json["data"],[
            {'attributes': {'gruppe': 'A', 'hasChildren': 1, 'tags': 'A,K'}, 'id': None, 'type': 'dbtests'}, 
            {'attributes': {'gruppe': 'A', 'hasChildren': 1, 'tags': 'B K A'}, 'id': None, 'type': 'dbtests'}, 
            {'attributes': {'gruppe': 'B', 'hasChildren': 1, 'tags': 'A,K'}, 'id': None, 'type': 'dbtests'}, 
            {'attributes': {'gruppe': 'C', 'hasChildren': 1, 'tags': None}, 'id': None, 'type': 'dbtests'}, 
            {'attributes': {'gruppe': 'C', 'hasChildren': 1, 'tags': 'M,K,one'}, 'id': None, 'type': 'dbtests'}, 
            {'attributes': {'gruppe': 'D', 'hasChildren': 1, 'tags': None}, 'id': None, 'type': 'dbtests'}
        ], "groupby mit Filter und zwei Gruppierungs Feldern fehlerhaft " )
        
       
        # groupby mit label testen
        response = self.app.get( "api/dbtests/groupby", query_string={
            "groups":"gruppe",
            "labels": '{"dbtests.gruppe": "lGruppe"}'
        })
        self.assertEqual(response.status_code, 200, "Api Status nicht 200")      
        self.assertEqual( response.json["data"], [
            {'attributes': {'hasChildren': 2, 'lGruppe': 'A'}, 'id': None, 'type': 'dbtests'}, 
            {'attributes': {'hasChildren': 2, 'lGruppe': 'B'}, 'id': None, 'type': 'dbtests'}, 
            {'attributes': {'hasChildren': 3, 'lGruppe': 'C'}, 'id': None, 'type': 'dbtests'}, 
            {'attributes': {'hasChildren': 1, 'lGruppe': 'D'}, 'id': None, 'type': 'dbtests'}
        ], "groupby mit label fehlerhaft " )
        
        # groupby mit zweifachen label testen
        response = self.app.get( "api/dbtests/groupby", query_string={
            "groups":"gruppe",
            "labels": '{"dbtests.gruppe": ["lGruppeA", "lGruppeB"]}'
        })
        self.assertEqual(response.status_code, 200, "Api Status nicht 200")       
        self.assertEqual( response.json["data"], [
            {'attributes': {'hasChildren': 2, 'lGruppeA': 'A', 'lGruppeB': 'A'}, 'id': None, 'type': 'dbtests'}, 
            {'attributes': {'hasChildren': 2, 'lGruppeA': 'B', 'lGruppeB': 'B'}, 'id': None, 'type': 'dbtests'}, 
            {'attributes': {'hasChildren': 3, 'lGruppeA': 'C', 'lGruppeB': 'C'}, 'id': None, 'type': 'dbtests'}, 
            {'attributes': {'hasChildren': 1, 'lGruppeA': 'D', 'lGruppeB': 'D'}, 'id': None, 'type': 'dbtests'}
        ], "groupby mit label fehlerhaft " )
      
        # groupby mit fields und label testen
        response = self.app.get( "api/dbtests/groupby", query_string={
            "fields[dbtests]":"gruppe",
            "labels": '{"dbtests.gruppe": "lGruppe"}'
        })
        self.assertEqual(response.status_code, 200, "Api Status nicht 200")        
        self.assertEqual(response.json["data"], [     
            {'attributes': {'hasChildren': 2, 'lGruppe': 'A'}, 'id': None, 'type': 'dbtests'},
            {'attributes': {'hasChildren': 2, 'lGruppe': 'B'}, 'id': None, 'type': 'dbtests'}, 
            {'attributes': {'hasChildren': 3, 'lGruppe': 'C'}, 'id': None, 'type': 'dbtests'}, 
            {'attributes': {'hasChildren': 1, 'lGruppe': 'D'}, 'id': None, 'type': 'dbtests'}
        ], "groupby mit fields und label fehlerhaft" )
        
        # groupby mit fields und zweifachen label testen
        response = self.app.get( "api/dbtests/groupby", query_string={
            "fields[dbtests]":"gruppe",
            "labels": '{"dbtests.gruppe": ["lGruppeA", "lGruppeB"]}'
        })

        self.assertEqual(response.status_code, 200, "Api Status nicht 200")
        self.assertEqual( response.json["data"], [
            {'attributes': {'hasChildren': 2, 'lGruppeA': 'A', 'lGruppeB': 'A'}, 'id': None, 'type': 'dbtests'}, 
            {'attributes': {'hasChildren': 2, 'lGruppeA': 'B', 'lGruppeB': 'B'}, 'id': None, 'type': 'dbtests'},
            {'attributes': {'hasChildren': 3, 'lGruppeA': 'C', 'lGruppeB': 'C'}, 'id': None, 'type': 'dbtests'}, 
            {'attributes': {'hasChildren': 1, 'lGruppeA': 'D', 'lGruppeB': 'D'}, 'id': None, 'type': 'dbtests'}    
        ], "groupby mit fields und label fehlerhaft" )
        
        # id als gruppe wird ausgefiltert
        response = self.app.get( "api/dbtests/groupby", query_string={
            "groups":"id"
        })
        self.assertEqual(response.status_code, 200, "Api Status nicht 200")
        self.assertEqual( response.json["data"], [
            {'attributes': {'hasChildren': 1}, 'id': 1, 'type': 'dbtests'}, 
            {'attributes': {'hasChildren': 1}, 'id': 2, 'type': 'dbtests'}, 
            {'attributes': {'hasChildren': 1}, 'id': 3, 'type': 'dbtests'}, 
            {'attributes': {'hasChildren': 1}, 'id': 4, 'type': 'dbtests'}, 
            {'attributes': {'hasChildren': 1}, 'id': 5, 'type': 'dbtests'},
            {'attributes': {'hasChildren': 1}, 'id': 6, 'type': 'dbtests'}, 
            {'attributes': {'hasChildren': 1}, 'id': 7, 'type': 'dbtests'}, 
            {'attributes': {'hasChildren': 1}, 'id': 8, 'type': 'dbtests'}
        ] , "id als gruppe wird ausgefiltert" )
        
        
    def test_webapp_db_groupsplit( self ):
        ''' Api aufruf für gruppierte Felddaten 

            /api/<modul>/groupsplit?group=<feld1>

            /api/<modul>/groupsplit?group=<feld1>&delimiter=,
            /api/<modul>/groupsplit?group=<feld1>&delimiter=,&filter=eq(active,1)

        WITH split(word, str) AS (
        	SELECT '',tags||',' FROM dbtests WHERE active=1
        	UNION ALL 
        		SELECT substr(str, 0, instr(str, ',')), substr(str, instr(str, ',')+1) FROM split WHERE str!=''
        ) 
        SELECT word as tags, count(*) AS hasChildren FROM split WHERE word!='' GROUP BY word
    
        ''' 
          
        # groupsplit mit default delimiter (space) 
        response = self.app.get( "api/dbtests/groupsplit", query_string={
            "group":"tags",
        })
       
        self.assertEqual(response.status_code, 200, "Api Status nicht 200")        
        self.assertEqual( response.json["data"],[
            {'attributes': {'hasChildren': 1, 'id': 'A', 'tags': 'A'}, 'id': 'A', 'type': 'dbtests'},
            {'attributes': {'hasChildren': 2, 'id': 'A,K', 'tags': 'A,K'}, 'id': 'A,K', 'type': 'dbtests'},
            {'attributes': {'hasChildren': 1, 'id': 'B', 'tags': 'B'}, 'id': 'B', 'type': 'dbtests'},
            {'attributes': {'hasChildren': 1, 'id': 'B,M', 'tags': 'B,M'}, 'id': 'B,M', 'type': 'dbtests'},
            {'attributes': {'hasChildren': 2, 'id': 'K', 'tags': 'K'}, 'id': 'K', 'type': 'dbtests'},
            {'attributes': {'hasChildren': 1, 'id': 'L,A', 'tags': 'L,A'}, 'id': 'L,A', 'type': 'dbtests'},
            {'attributes': {'hasChildren': 1, 'id': 'M,K,one', 'tags': 'M,K,one'}, 'id': 'M,K,one', 'type': 'dbtests'}
        ] , "groupsplit mit default (space) delimiter: Rückgabe fehlerhaft " )

        # groupsplit mit delimiter 
        response = self.app.get( "api/dbtests/groupsplit", query_string={
            "group":"tags",
            "delimiter": ","
        })
        self.assertEqual(response.status_code, 200, "Api Status nicht 200")
        self.assertEqual( response.json["data"],[
            {'attributes': {'hasChildren': 2, 'id': 'A', 'tags': 'A'}, 'id': 'A', 'type': 'dbtests'}, 
            {'attributes': {'hasChildren': 1, 'id': 'A K', 'tags': 'A K'}, 'id': 'A K', 'type': 'dbtests'}, 
            {'attributes': {'hasChildren': 1, 'id': 'B', 'tags': 'B'}, 'id': 'B', 'type': 'dbtests'}, 
            {'attributes': {'hasChildren': 1, 'id': 'B K A', 'tags': 'B K A'}, 'id': 'B K A', 'type': 'dbtests'}, 
            {'attributes': {'hasChildren': 3, 'id': 'K', 'tags': 'K'}, 'id': 'K', 'type': 'dbtests'},
            {'attributes': {'hasChildren': 1, 'id': 'L', 'tags': 'L'}, 'id': 'L', 'type': 'dbtests'}, 
            {'attributes': {'hasChildren': 2, 'id': 'M', 'tags': 'M'}, 'id': 'M', 'type': 'dbtests'}, 
            {'attributes': {'hasChildren': 1, 'id': 'one', 'tags': 'one'}, 'id': 'one', 'type': 'dbtests'}
        ], "groupsplit mit ',' delimiter: Rückgabe fehlerhaft " )
        
        
        # groupsplit mit delimiter und filter
        response = self.app.get( "api/dbtests/groupsplit", query_string={
            "group":"tags",
            "filter": "eq(active,1)", 
            "delimiter": ","
        })
        self.assertEqual(response.status_code, 200, "Api Status nicht 200")
         
        self.assertEqual( response.json["data"],[
            {'attributes': {'hasChildren': 2, 'id': 'A', 'tags': 'A'}, 'id': 'A', 'type': 'dbtests'},
            {'attributes': {'hasChildren': 1, 'id': 'B K A', 'tags': 'B K A'}, 'id': 'B K A', 'type': 'dbtests'},
            {'attributes': {'hasChildren': 3, 'id': 'K', 'tags': 'K'}, 'id': 'K', 'type': 'dbtests'},
            {'attributes': {'hasChildren': 1, 'id': 'M', 'tags': 'M'}, 'id': 'M', 'type': 'dbtests'},
            {'attributes': {'hasChildren': 1, 'id': 'one', 'tags': 'one'}, 'id': 'one', 'type': 'dbtests'}
        ], "groupsplit mit ',' delimiter und filter 'eq(active,1)': Rückgabe fehlerhaft " )       
        
    def todo_test_webapp_db_typen( self ):
        ''' Verschiedene feldtype testen
       
        ''' 
        
        # .. todo:: numerische Felder - 
        # datums Felder - date
        # json Felder - data
        response = self.app.post( "api/dbtests/", headers={'Content-Type': 'application/json'}, data=json.dumps({ 
            "data" : {
                "attributes": {
                    "string":"sechs",     # Pflichtfeld
                    "date":"2020-08-19", 
                    "integer": 6,
                    "data": {"A":1},
                    "float": 1/3,
                    "decimal" : 1.2345,   # soll nur 1.23 ergeben
                    "numeric" : 5.6789,
                    "isodate" :"2020-08-19",
                    "isodatetime" :"2020-08-19 14:37"
                },
                "type":"dbtests"
            }

        }), follow_redirects=True) 
        
        print( "TODO: test_webapp_db_typen", response.json["data"] )
        
        #self.assertEqual( response.status_code, 201, "Api Status nicht 201 (Created)")
        #self.assertEqual( response.json["data"]["attributes"]["date"], '2020-08-19', "Datensatz datum ist nicht 2020-08-19")     
        #self.assertEqual( response.json["data"]["attributes"]["data"], {"A":1}, 'Datensatz data ist nicht {"A":1}')                        
        #self.assertEqual( response.json["data"]["attributes"]["float"], 0.3333333333333333, 'Datensatz float ist nicht 0.3333333333333333')                        
                             
        
        #print( response.json["data"] )
        pass
    
        
    def test_isp_mpdf_fonts( self ):
        """Testet Fonts für die PDF Erstellung mit fc-list 
        
        Benötigte Fonts:
            
        * DejaVuSerif
        * Material Design Icons
            
        Returns
        -------
        None.
        
        """
        import subprocess
        
        cmd = '/usr/bin/fc-list --format="%{family[0]}\n" | sort | uniq'

        output = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE ).communicate()[0] 
                
        self.assertIn( 
            b"Material Design Icons",
            output,
            "Der Font 'Material Design Icons' fehlt im System"
            )
        
        
        self.assertIn( 
            b"DejaVu Serif",
            output,
            "Der Font 'DejaVuSerif' fehlt im System"
            )    

        
    def test_isp_mpdf_base( self ):
        ''' Ein PDF Dokument erstellen
       
        '''           
        
        response = self.app.get( "api/dummy/pdf" )
        self.assertEqual(response.status_code, 400, "Status nicht 400")
        self.assertEqual( 
            response.data,
            b"Keine PDF Datei (nofile.pdf) gefunden",
            "Testet Fehler bei Rückgabe eine fehlenden PDF Datei "
        )  
        
        config = ispConfig( )  
        v1 = config.variables.get("Version")
        # informationen zu pdf Erstellung
        response = self.app.get( "api/dummy/pdf", query_string={ 
            "name" : "test-info"
        } )
        self.assertEqual(response.status_code, 200, "Status nicht 200") 
        
        self.assertEqual( 
            response.json["data"]["varianten"], 
            {'v1': v1, 'v2': 'u.0.1', 'v3': 'u.0.1'}, 
            "resources Angabe stimmt nicht" 
        )
        
        # ein leeres PDF mit overlay
        response = self.app.get( "api/dummy/pdf", query_string={ 
            "name" : "test-1"
        } )
        self.assertEqual(response.status_code, 200, "Status nicht 200")
        self.assertEqual( response.json["data"]["body"], "", "PDF body ist nicht leer" )
        self.check_pdf_data( response.json["data"], contents=0, pages=1, intern_check=True )
        
        # text und markdown mit Header (h2) 
        response = self.app.get( "api/dummy/pdf", query_string={ 
            "name" : "test-2"
        } )
        self.assertEqual(response.status_code, 200, "Status nicht 200")
       
        # kommt es hier zu einem Fehler stimmt die css Einbindung von weasyprint nicht
        self.check_pdf_data( response.json["data"], contents=1, pages=1, intern_check=True )
        
        # wie test 2 aber markdown zuerst
        response = self.app.get( "api/dummy/pdf", query_string={ 
            "name" : "test-2a"
        } )
        self.assertEqual(response.status_code, 200, "Status nicht 200")
        #print( response.json["data"] )
        self.check_pdf_data( response.json["data"], contents=1, pages=1, intern_check=True )
       
        response = self.app.get( "api/dummy/pdf", query_string={ 
            "name" : "test-3"
        } )
        self.assertEqual(response.status_code, 200, "Status nicht 200")
        self.check_pdf_data( response.json["data"],  contents=2, pages=4, intern_check=True )
       
        response = self.app.get( "api/dummy/pdf", query_string={ 
            "name" : "test-4"
        } )
        self.assertEqual(response.status_code, 200, "Status nicht 200")
        # kommt es hier zu einem Fehler stimmt die font Einbindung von weasyprint nicht
        self.check_pdf_data( response.json["data"], contents=2, pages=3, intern_check=True )
        
        # Inhalte über template file einfügen
        response = self.app.get( "api/dummy/pdf", query_string={ 
            "name" : "test-5"
        } )
        self.assertEqual(response.status_code, 200, "Status nicht 200")
        # selbst prüfen, da debug informationen vorliegen
        self.assertEqual( 
            response.json["data"]["pages"], 
            2,
            "Anzahl der Seiten stimmt nicht"            
        )
        #print( response.json["data"] )
       
        
        #print( response.json )
        
        # .. todo:: rückgabe als pdf
        
          
def suite( testClass:None ):
    '''Fügt alle Funktionen, die mit test_ beginnen aus der angegeben Klasse der suite hinzu
    

    Parameters
    ----------
    testClass : unittest.TestCase
        Zu testende Klasse

    Returns
    -------
    suite : unittest.TestSuite

    '''
    if not testClass:
        testClass = ispTest
        
    suite = unittest.TestSuite( )
    
    logger.setLevel( logging.ERROR ) # ERROR DEBUG WARNING 
    
    if testClass:
        
        #suite.addTest( testClass('test_webapp_db_tests_filter') )
        
        
        #suite.addTest( testClass('test_webapp_db_groupby') )
        
        #suite.addTest( testClass('test_webapp_db_groupsplit') )
       # return suite
    
        for m in dir( testClass ):
            if m.startswith('test_config_'):
                suite.addTest( testClass(m), )
                pass
            elif m.startswith('test_webapp_base_'):
                suite.addTest( testClass(m),  )
                pass
            elif m.startswith('test_webapp_dummy_'):
                suite.addTest( testClass(m),  )
                pass
            elif m.startswith('test_webapp_db_'):
                suite.addTest( testClass(m),  )
                pass
            elif m.startswith('test_isp_mpdf_'):
                suite.addTest( testClass(m),  )
                pass
    
    return suite
   

# -----------------------------------------------------------------------------    
if __name__ == '__main__':

    '''
    0 (quiet): you just get the total numbers of tests executed and the global result
    1 (default): you get the same plus a dot for every successful test or a F for every failure
    2 (verbose): you get the help string of every test and the result
    '''
    
    runner = unittest.TextTestRunner()
    runner.run( suite( ispTest ) )
   