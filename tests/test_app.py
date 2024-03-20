# -*- coding: utf-8 -*-

"""


"""

# append project baspath to site
import os, site
from os import path as osp

ABSPATH = osp.dirname( osp.abspath( __file__) )
BASEPATH = osp.abspath(osp.join( ABSPATH , ".."))
FILESPATH = osp.abspath(osp.join( BASEPATH, 'data', 'unittest'))

site.addsitedir(BASEPATH)

import shutil

from urllib.parse import urlencode

# Coverage am Anfang initialisieren damit alles berücksichtigt wird
cov = None
import coverage

# ausschalten wenn coverage nicht durchgeführt werden soll
runCoverage = False

if runCoverage:
    cov = coverage.Coverage()
    # mqtt und config seperat über isp.py prüfen
    cov.config.set_option("run:omit", ["*/isp/mqtt.py", "*/isp/config.py"] )
    cov.start()

import unittest

import json

import warnings
warnings.filterwarnings("ignore")

import pandas as pd

import logging
logger = logging.getLogger( "MQTT" )

from testbase import testCaseBase

from testdb import dbtests
from testdummy import dummy

from app import run

from app.ariadicom import ariaDicomClass
from app.aria import ariaClass

class testBase(testCaseBase):
    """
    setUp(), tearDown(), and __init__() will be called once per test.

    """

    results_path = ""
    check_path = ""
    dicom_path = ""

    called_tests = {}
    called_tests_results = {}

    check_pdf = True
    check_data = True

    # dicom 
    adc = None

    unitNames = []

    @classmethod
    def setUpClass(self):
        """Wird beim initialisieren der Testklasse aufgerufen.

        - Api bereitstellen
        - test Ergebnisse zum Vergleich laden
        """
        self.gqa_data_ready = False
        # This attribute controls the maximum length of diffs output by assert methods that report diffs on failure.
        # It defaults to 80*8 characters
        self.maxDiff = None

        if not os.path.exists( FILESPATH ):
            os.mkdir( FILESPATH )

        self.results_path = osp.join( FILESPATH, "results" )
        if not os.path.exists( self.results_path ):
            os.mkdir( self.results_path )

        self.check_path = os.path.join( FILESPATH, 'check')
        if not os.path.exists( self.check_path ):
            os.mkdir( self.check_path )
            
        self.dicom_path = osp.abspath(osp.join( FILESPATH, "..", "DICOM" ))
        if not os.path.exists( self.dicom_path ):
            os.mkdir( self.dicom_path )
        
        
        # webapp mit unitest config
        # 0 - NOTSET, 10 - DEBUG, 20 - INFO, 30 - WARNING, 40 - ERROR, 50 - CRITICAL
        # safrs, sqlalchemy, webapp, root, mqtt
        self.webapp = run( {
            "server" : {
                "webserver" : {
                    "name" : "app_test",
                    "port" : 5001,
                    "TESTING": True,
                    "reloader" : False
                },
                "logging" :{ 
                    "safrs" : logging.DEBUG, # 10
                    "sqlalchemy" : logging.DEBUG, # 10
                    "webapp" : logging.DEBUG, # 10
                },
            },
            "database": {
                "servername" : "VMSCOM",
                "main": "pygqa",
                "pygqa" : {
                    "name" : "pygqa_unittest.json"
                }
            },
            "dicom": {
                "servername" : "VMSCOM",
                "VMSCOM" : {
                    "local_dir" : self.dicom_path
                }
            },
            "resultsPath" : self.results_path,
            "version": "unittest",
            "variables" : {
                "Datenausgabe" : "unittest"
            }

        } ,additionalModels=[
           dbtests,
           dummy
        ])
        self.app = self.webapp.app

        for pid, unit in self.webapp._config.testunits.items():
            if not unit:
                continue
            self.unitNames.append(unit)

        # Vergleichs Daten laden 
        self.data_file = osp.join( self.webapp._config.resultsPath, self.webapp._config.database.gqa.name )
        self.check_data_file = osp.join( self.check_path, 'pygqa.json')

        if osp.isfile( self.check_data_file ):
            self.gqa = pd.read_json( self.check_data_file, orient="table", precise_float=10 )

            # index definiert in app.results
            if self.gqa.index.names == ['unit', 'energy', 'test', 'date',  'group']:
                self.gqa_data_ready = True

        # tags und gqa ids der Tests bestimmen
        self.testTags = {}
        self.testIds = {}

        for testid, item in self.webapp._config.GQA.items():
            if "tag" in item:
                self.testTags[ item["tag"] ] = testid
                self.testIds[ testid ] = item["tag"]

        if self.gqa_data_ready == True:
            print( "testBase::setUpClass - Verwende '{}' zum überprüfen.".format(self.check_data_file) )
        else:
            print("testBase::setUpClass - Es liegen noch keine Vergleichsdaten in '{}' vor. Die Testergebnisse könnnen nicht geprüft werden".format(self.check_data_file) )

    @classmethod
    def tearDownClass(cls):
        '''Wird beim schießen der Testklasse aufgerufen.
        
        Parameters
        ----------
        cls : TYPE
            DESCRIPTION.

        Returns
        -------
        None.

        '''
        
        if cls.gqa_data_ready == False:
          print( )
          print( "Kopiere Vergleichsdaten von {} nach {}".format(cls.data_file, cls.check_data_file) ) 
          if osp.isfile( cls.data_file ):
            shutil.copyfile( cls.data_file, cls.check_data_file )
          
        if cls.adc:
           cls.adc.closeAE()
           cls.adc = None

        allResults = {
            "BASEPATH": BASEPATH,
            "results_path" : cls.results_path.replace(BASEPATH, ""),
            "dicom_path" : cls.dicom_path.replace(BASEPATH, ""),
            "checkPath" : cls.check_path.replace(BASEPATH, ""),
            "calledTests" : cls.called_tests,
            "calledTestsResults" : cls.called_tests_results,
        }
        print( )
        print( "Called tests:")
        print( "=============")
        print( json.dumps(cls.called_tests, indent=2 )  )

        with open(osp.join(cls.results_path, "unittestResults.json"), "w" ) as json_file:
            json.dump( allResults, json_file, indent=2 )
        
    def setUp(self):
        ''' wird vor jedem test aufgerufen
        '''
        pass

    def webdriver_setUp(self):

        # create a new Firefox session
        #self.driver = webdriver.Firefox()
        #self.driver.implicitly_wait(30)
        #self.driver.maximize_window()
        # navigate to the application home page
        #self.driver.get("http://www.google.com/")

        # self.driver = webdriver.Chrome("/Users/nabeel/Documents/selenium/chromedriver73", options=op)
        pass

    def tearDown(self):
        ''' wird nach jeden test aufgerufen

        Returns
        -------
        None.

        '''

    def open_dicom(self):
        _database_key = self.webapp._config.get( "database.servername", "" )
        _dicom_key = self.webapp._config.get( "dicom.servername", "" )
               
        self.adc = ariaDicomClass( _database_key, _dicom_key, self.webapp._config )
        status = self.adc.initAE()

        self.assertEqual(status, 0x0000, "Dicom Zugriff ist nicht möglich")

    def run_test(self, params):
        ''' Einen Test über die Api durchführen

        Parameters
        ----------
        params : dict
            DESCRIPTION.

        Returns
        -------
        None.

        '''
        
        # nur wenn unit !== null
        if not params["unit"] :
            return None

        testComplete = None

        url = '/api/gqa/run'

        testUrl = "{}?{}".format( url, urlencode( params ) ) 
        self.called_tests[ testUrl ] = False
        
        # Unittest immer verwenden, damit das Ergebnis und nicht alle Daten des Jahres geliefert werden
        params["unittest"] = True

        response = self.app.get( url, query_string = params )
        if response.status_code != 200:
           testComplete = False

        # es dürfen keine App-Error Angaben vorliegen
        appError = response.json.get('App-Error', [] )
        if len( appError ) > 0:
           testComplete = False

        result = response.json.get('data', {} )
        if len( result ) == 0:
           testComplete = False

        # pro pdffile die test_results im Ergebnis prüfen wenn es eine results Datei gibt
        if self.gqa_data_ready:
            self.running_test_results = []
            testComplete = True
            for pdf_name, data in result.items():
                running_test_name = pdf_name.replace(self.results_path, "")
                result = {
                    "complete": None,
                    "hasCompareData": None,
                    "compareData": None,
                    "pdf.filename" : None,
                    "pdf.pageCount" : None,
                    "pdf.pageNames" : None,
                    "pdf.content" : None,
                    "pdf.content.pages" : {},
                    "pdf.pngDiff" : None,
                    "pdf.pngDiff.pages": {}
                }

                if self.check_data:
                    result.update( self.check_result_data( data ))

                if self.check_pdf:
                    result.update( self.check_pdf_data( data["pdfData"] ) )

                # alle bereiche (compareData, pdf.content, pdf.pngDiff, ) müssen true sein
                # 
                if result["compareData"] and result["pdf.content"] and result["pdf.pngDiff"]:
                    result["complete"] = True
                else:
                    testComplete = False
                    
                self.called_tests_results[running_test_name] = result

        self.called_tests[testUrl] = testComplete
        return testComplete
        
    def check_result_data(self, data):

        result = {
            "hasCompareData": False,
            "compareData": False,
        }
        # pro test im pdffile
        for test in data["result"]:
            # print( pdf_name, test )
            #testid = self.testIds
            try:
                orgData = self.gqa.loc[ test["unit"], test["energy"], test["test"], test["date"], test["group"] ].to_dict(  )
            except:
                orgData = {}


            if orgData == {}:
                print( "keine Vergleichsdaten vorhanden: '{unit}', '{energy}', '{test}', '{date}', {group}".format( **test ) )
                print( "Testresult (json pandas format):" )
                test_json = {
                    "unit": test["unit"],
                    "energy": test["energy"],
                    "test": test["test"],
                    "date": test["date"],
                    "group": test["group"],
                    "year": test["year"],
                    "month": test["month"],   
                    "acceptance": test["acceptance"],
                    "data": test["data"]                     
                } 
                print( json.dumps( test_json, indent=2 ) )
   
            else:
                result["hasCompareData"] = True
                # über pandas mit double_precision=4 auswerten
                # in data liegt als []
                # json.loads( df[ fields ].to_json(orient='index', double_precision=10, indent=2 ) )
            
                #print( json.dumps(orgData['data'], indent=2 ) )

                #print(orgData['data'])
                #print(test['data'])
                orgData_data = []
                test_data = []
            
                double_precision = 4 # oder 5
                for datas in orgData['data']:
                  
                    df_org_data = pd.read_json( json.dumps(orgData['data'][0]), orient='index' ).sort_index()
                    orgData_data.append( json.loads(df_org_data.to_json( orient='index', double_precision=double_precision ) ) )
                  
                    if len(test['data']) > 0:
                        df_test_data = pd.read_json( json.dumps(test['data'][0]), orient='index' ).reindex(columns=df_org_data.columns).sort_index()
                        test_data.append( json.loads(df_test_data.to_json( orient='index', double_precision=double_precision ) ) )
                        df_compare = df_org_data.compare( df_test_data )
                        # Daten sind unterschiedlich
                        if len(df_compare) > 0:
                            print( "orgData_data", json.dumps(orgData['data'], indent=2 ) )
                            print( "test_data", json.dumps(test['data'], indent=2 ) ) 
                        else:
                            result["compareData"] = True


                    '''
                    if len(df_compare) > 0:
                        print( "Vergleichsdaten unterschiedlich: '{unit}', '{energy}', '{test}', '{date}', {group}".format( **test ) )

                        print( "orgData_data", json.dumps(orgData['data'], indent=2 ) )
                        print( "test_data", json.dumps(test['data'], indent=2 ) )       
                    '''
                '''
                self.assertListEqual(
                    orgData_data,
                    test_data,
                    "Datenfehler im Testresult: '{unit}', '{energy}', '{test}', '{date}', {group}'".format( **test )
                )
                result["compareData"] = True
                '''

                '''
                # komplette genauigkeit testen
                self.assertListEqual(
                    orgData['data'] or [],
                    test['data'] or [],
                    "Datenfehler im Testresult: '{unit}', '{energy}', '{test}', '{date}', {group}'".format( **test )
                )
                '''

        return result


#
# ---- ab hier kommen die Tests -----------------------------------------------
#

class WebAppTest( testBase ):

    def _test_other_dicom( self ):  
  
        self.open_dicom()    
        
        # eine mögliche dicom uid holen
        check_image_uid = None
        for name, unit in self.webapp._config.get( "units" ).items():
            if not unit:
               continue
            sql = "SELECT PatientSer, PatientId, FirstName, LastName FROM [{dbname}].[dbo].[Patient] [Patient]"
            sql = sql + " WHERE [PatientId] = '{}' ".format( name )
            result = self.adc.execute( sql )
            self.assertNotEqual(len( result ), 0, "keine unit in der Datenbank")

            images, sql = self.adc.getImages( name )
            self.assertNotEqual(len( images ), 0, "keine Bilder in der Datenbank")
            
            check_image_uid = images[0]["SliceUID"]

            
        # läuft asynchron
        result, signals = self.adc.retrieve( {
            "SOPInstanceUID" : check_image_uid,
            "override" : True,
            "subPath" : "systeminfo"
        })

        self.assertNotEqual(len( signals ), 0, "keine Dicom Rückgabe")

        if len(signals) > 0:
            for signal in signals:
                exists, filename = self.adc.archive_hasSOPInstanceUID( check_image_uid )
         
                self.assertNotEqual(exists, 0, "kein DICOM Bild geholt {} ".format(filename))

        self.adc.closeAE()
        self.adc = None
        
    def test_other_Tagging(self):
        ''' Gibt eine Liste alle Testbeschreibungen (config) mit Anleitungen

        '''
        url = '/api/gqa/tagging'
        params = {}

        response = self.app.get( url, query_string = params )

        self.assertEqual(response.status_code, 200, "Api Rückgabe fehlerhaft")

         # für coverage die varianten als html
        params = {
            "art" : "sum",
            "format": "html"
        }
        response = self.app.get( url, query_string = params )
        self.assertEqual(response.status_code, 200, "Api Rückgabe fehlerhaft")

        params = {
            "art" : "test",
            "format": "html"
        }
        response = self.app.get( url, query_string = params )
        self.assertEqual(response.status_code, 200, "Api Rückgabe fehlerhaft")

        params = {
            "art" : "tags",
            "format": "html"
        }
        response = self.app.get( url, query_string = params )
        self.assertEqual(response.status_code, 200, "Api Rückgabe fehlerhaft")


    def test_other_Tests(self):

        url = '/api/gqa/2020'
        params = {}
        response = self.app.get( url, query_string = params )


    def test_other_Matrix(self):
        ''' Gibt eine Liste alle Testbeschreibungen (config) mit Anleitungen
        '''
        url = '/api/gqa/matrix'

        response = self.app.get( url, query_string = {} )
        self.assertEqual(response.status_code, 200, "Api Rückgabe fehlerhaft")

        # für coverage nochmal als html
        response = self.app.get( url, query_string = {"format": "html"} )
        self.assertEqual(response.status_code, 200, "Api Rückgabe fehlerhaft")


    def test_other_configs(self):
        ''' Gibt eine Liste alle Testbeschreibungen (config) mit Anleitungen
        '''
        url = '/api/gqa/configs'

        response = self.app.get( url, query_string = {"format" : "json"} )
        self.assertEqual(response.status_code, 200, "Api Rückgabe fehlerhaft")

        # für coverage nochmal als html
        response = self.app.get( url, query_string = {"format": "html"} )
        self.assertEqual(response.status_code, 200, "Api Rückgabe fehlerhaft")


    # ---- MLC -----------------------------------------------
        
    def test_mlc_JT_10_3_1_2019(self):
        ''' Jahrestest - JT_10.3.1 - Leafabstand bei FWHM für alle Leafpaare

        Dieser Test wird auch für das Prüfen der Dicomübertragung verwendet

        .. todo:: im Test selbst fehlt noch der gesamt Check
        '''
        resultError = []
        for unit in self.unitNames:
            result = self.run_test( {
              "testid": "JT-10_3_1",
              "unit": unit,
              "year": 2019
            } )
            if result == False:
                resultError.append( unit )
        self.assertEqual( resultError, [], "Test fehlerhaft" )
  
    def test_mlc_JT_10_3_1_2021(self):
        ''' Jahrestest - JT_10.3.1 - Leafabstand bei FWHM für alle Leafpaare

        Dieser Test wird auch für das Prüfen der Dicomübertragung verwendet

        .. todo:: im Test selbst fehlt noch der gesamt Check
        '''
        resultError = []
        for unit in self.unitNames:
            result = self.run_test( {
              "testid": "JT-10_3_1",
              "unit": unit,
              "year": 2021
            } )
            if result == False:
                resultError.append( unit )
        self.assertEqual( resultError, [], "Test fehlerhaft" )        

    def test_mlc_JT_4_2_2_1_A_2019(self):
        ''' Jahrestest - JT_4.2.2.1-A - Leaf Transmission

        '''
        resultError = []
        for unit in self.unitNames:
            result = self.run_test( {
              "testid": "JT-4_2_2_1-A",
              "unit": unit,
              "year": 2019
            } )
            if result == False:
                resultError.append( unit )
        self.assertEqual( resultError, [], "Test fehlerhaft" )

    def test_mlc_JT_4_2_2_1_B_2019(self):
        ''' Jahrestest - JT_4.2.2.1-B - Interleaf Transmission
        '''
        resultError = []
        for unit in self.unitNames:
            result = self.run_test( {
              "testid": "JT-4_2_2_1-B",
              "unit": unit,
              "year": 2019
            } )
            if result == False:
                resultError.append( unit )
        self.assertEqual( resultError, [], "Test fehlerhaft" )          

    def test_mlc_JT_4_2_2_1_B_2021(self):
        ''' Jahrestest - JT_4.2.2.1-B - Interleaf Transmission
        '''
        resultError = []
        for unit in self.unitNames:
            result = self.run_test( {
              "testid": "JT-4_2_2_1-B",
              "unit": unit,
              "year": 2021
            } )
            if result == False:
                resultError.append( unit )
        self.assertEqual( resultError, [], "Test fehlerhaft" )      

    def test_mlc_JT_4_2_2_1_C_2019(self):
        ''' Jahrestest - JT_4.2.2.1-C - Interleaf Gap
        '''
        resultError = []
        for unit in self.unitNames:
            result = self.run_test( {
              "testid": "JT-4_2_2_1-C",
              "unit": unit,
              "year": 2019
            } )
            if result == False:
                resultError.append( unit )
        self.assertEqual( resultError, [], "Test fehlerhaft" )

    def todo_test_mlc_JT_LeafSpeed_2018(self):
        ''' Jahrestest - JT_LeafSpeed - Geschwindigkeit der Lamellen DIN 6875-3, Teil 4.2.5 (Variationen von Dl, Gantry und Kollimator)
            96 Felder
        '''
        resultError = []
        for unit in self.unitNames:
            result = self.run_test( {
              "testid": "JT-LeafSpeed",
              "unit": unit,
              "year": 2018
            } )
            if result == False:
                resultError.append( unit )
        self.assertEqual( resultError, [], "Test fehlerhaft" )          
    
    def test_mlc_JT_LeafSpeed_2020(self):
        ''' Jahrestest - JT_LeafSpeed - Geschwindigkeit der Lamellen DIN 6875-3, Teil 4.2.5 (Variationen von Dl, Gantry und Kollimator)
            27 Felder
        '''
        resultError = []
        for unit in self.unitNames:
            result = self.run_test( {
              "testid": "JT-LeafSpeed",
              "unit": unit,
              "year": 2020
            } )
            if result == False:
                resultError.append( unit )
        self.assertEqual( resultError, [], "Test fehlerhaft" )

    def test_mlc_MT_LeafSpeed_2019(self):
        ''' Monatstest - MT_LeafSpeed - IMRT - Geschwindigkeit und Geschwindigkeitsänderung der Lamellen
        '''
        resultError = []
        for unit in self.unitNames:
            result = self.run_test( {
              "testid": "MT-LeafSpeed",
              "unit": unit,
              "year": 2019,
              "month": 9
            } )
            if result == False:
                resultError.append( unit )
        self.assertEqual( resultError, [], "Test fehlerhaft" )

        
    def test_mlc_MT_LeafSpeed_2020(self):
        ''' Monatstest - MT_LeafSpeed - IMRT - Geschwindigkeit und Geschwindigkeitsänderung der Lamellen
    
        '''
        resultError = []
        for unit in self.unitNames:
            result = self.run_test( {
              "testid": "MT-LeafSpeed",
              "unit": unit,
              "year": 2020,
              "month": 1
            } )
            if result == False:
                resultError.append( unit )
        self.assertEqual( resultError, [], "Test fehlerhaft" )          

    def test_mlc_MT_8_02_1_2_2019(self):
        ''' Monattest MLC - MT_8.02-1_2

        Returns
        -------
        None.

        '''
        resultError = []
        for unit in self.unitNames:
            result =  self.run_test( {
              "testid": "MT-8_02-1-2",
              "unit": unit,
              "year": 2019,
              "month": 9
            } )
            if result == False:
                resultError.append( unit )
        self.assertEqual( resultError, [], "Test fehlerhaft" )

    def test_mlc_MT_8_02_1_2_2020(self):
        ''' Monattest MLC - MT_8.02-1_2

        Returns
        -------
        None.

        '''
        # Änderung: ohne Leaf 1 und 60  (noch nicht geändert in Testresult json)
        resultError = []
        for unit in self.unitNames:
            result = self.run_test( {
              "testid": "MT-8_02-1-2",
              "unit": unit,
              "year": 2020,
              "month": 5
            } )
            if result == False:
                resultError.append( unit )
        self.assertEqual( resultError, [], "Test fehlerhaft" )          
               
    def test_mlc_MT_8_02_3_2019(self):
        ''' Monattest MLC - 8.02-3

        Returns
        -------
        None.

        '''
        resultError = []
        for unit in self.unitNames:
            result = self.run_test( {
              "testid": "MT-8_02-3",
              "unit": unit,
              "year": 2019,
              "month": 9
            } )
            if result == False:
                resultError.append( unit )
        self.assertEqual( resultError, [], "Test fehlerhaft" )

    def test_mlc_MT_8_02_4_2020(self):
        ''' Monattest MLC - 8.02-4

        Returns
        -------
        None.

        Wegen einer Änderung der Auswertung ab 2020/05 in mlc.doMLC_VMAT wird 2020 verwendet

        '''
        resultError = []
        for unit in self.unitNames:
            result = self.run_test( {
              "testid": "MT-8_02-4",
              "unit": unit,
              "year": 2020,
              "month": 6
            } )
            if result == False:
                resultError.append( unit )
        self.assertEqual( resultError, [], "Test fehlerhaft" )

    def test_mlc_MT_VMAT_0_2_2020(self):
        ''' Monatstest - MT_VMAT_0.2 -

            Wegen einer Änderung der Auswertung ab 2020/05 in mlc.doMLC_VMAT wird 2020 verwendet
        '''
        resultError = []
        for unit in self.unitNames:
            result = self.run_test( {
              "testid": "MT-VMAT-0_2",
              "unit": unit,
              "year": 2020,
              "month": 6
            } )
            if result == False:
                resultError.append( unit )
        self.assertEqual( resultError, [], "Test fehlerhaft" )          

    def test_mlc_MT_VMAT_1_1_2020(self):
        ''' Monatstest - MT_VMAT_1.1 -

                Wegen einer Änderung der Auswertung ab 2020/05 in mlc.doMLC_VMAT wird 2020 verwendet
        '''
        resultError = []
        for unit in self.unitNames:
            result = self.run_test( {
              "testid": "MT-VMAT-1_1",
              "unit": unit,
              "year": 2020,
              "month": 6
            } )
            if result == False:
                resultError.append( unit )
        self.assertEqual( resultError, [], "Test fehlerhaft" )

    def test_mlc_MT_VMAT_1_2_2020(self):
        ''' Monatstest - MT_VMAT_1.2 -

                Wegen einer Änderung der Auswertung ab 2020/05 in mlc.doMLC_VMAT wird 2020 verwendet
        '''
        resultError = []
        for unit in self.unitNames:
            result = self.run_test( {
              "testid": "MT-VMAT-1_2",
              "unit": unit,
              "year": 2020,
              "month": 6
            } )
            if result == False:
                resultError.append( unit )
        self.assertEqual( resultError, [], "Test fehlerhaft" )

    # ---- field ----------------------------------------------

    def test_field_JT_7_2_2020(self):
        ''' Jahrestest - JT_7.2 -

        '''
        resultError = []
        for unit in self.unitNames:
            result = self.run_test( {
              "testid": "JT-7_2",
              "unit": unit,
              "year": 2020
            } )
            if result == False:
                resultError.append( unit )
        self.assertEqual( resultError, [], "Test fehlerhaft" )

    def test_field_JT_7_3_2020(self):
        '''Jahrestest - JT_7.3

        '''
        resultError = []
        for unit in self.unitNames:
            result = self.run_test( {
              "testid": "JT-7_3",
              "unit": unit,
              "year": 2020
            } )
            if result == False:
                resultError.append( unit )
        self.assertEqual( resultError, [], "Test fehlerhaft" )    

    def test_field_JT_7_4_2019(self):
        ''' Jahrestest - JT_7.4 - Abhängikeit Kalibrierfaktoren vom Tragarm Rotationswinkel

        '''
        resultError = []
        for unit in self.unitNames:
            result = self.run_test( {
              "testid": "JT-7_4",
              "unit": unit,
              "year": 2019
            } )
            if result == False:
                resultError.append( unit )
        self.assertEqual( resultError, [], "Test fehlerhaft" )          

    def test_field_JT_7_4_2020(self):
        ''' Jahrestest - JT_7.4 - Abhängikeit Kalibrierfaktoren vom Tragarm Rotationswinkel

        '''
        resultError = []
        for unit in self.unitNames:
            result =  self.run_test( {
              "testid": "JT-7_4",
              "unit": unit,
              "year": 2020
            } )
            if result == False:
                resultError.append( unit )
        self.assertEqual( resultError, [], "Test fehlerhaft" )      
        

    def test_field_JT_7_5_2019(self):
        '''
        Jahrestest - JT_7.5 - Abhängikeit Kalibrierfaktoren der Tragarmrotation
        ''' 
        resultError = []
        for unit in self.unitNames:
            result =  self.run_test( {
              "testid": "JT-7_5",
              "unit": unit,
              "year": 2019
            } )
            if result == False:
                resultError.append( unit )
        self.assertEqual( resultError, [], "Test fehlerhaft" )        

    def test_field_JT_7_5_2020(self):
        '''
        Jahrestest - JT_7.5 - Abhängikeit Kalibrierfaktoren der Tragarmrotation

        TODO: keine Vergleichsdaten -> erzeugen
        '''
        
        resultError = []
        for unit in self.unitNames:
            result = self.run_test( {
              "testid": "JT-7_5",
              "unit": unit,
              "year": 2020
            } )
            if result == False:
                resultError.append( unit )
        self.assertEqual( resultError, [], "Test fehlerhaft" )     

    def test_field_JT_9_1_2_2019(self):
        '''
        Jahrestest - JT_9.1.2 - Abhängigkeit der Variation des Dosisquerprofils vom Tragarm-Rotationswinkel
        Test funktioniert mit EPID nur mit Aufbauplatte
        '''

        resultError = []
        for unit in self.unitNames:
            result = self.run_test( {
              "testid": "JT-9_1_2",
              "unit": unit,
              "year": 2019
            } )
            if result == False:
                resultError.append( unit )
        self.assertEqual( resultError, [], "Test fehlerhaft" )          

    def test_field_MT_4_1_2_2020(self):
        '''
        Monatstest - MT_4.1.2 - Linearität MU MT_4.1.2
        erst ab 2020 - result hat zwei Ergebnisse (tabellen) im json liegt aber nur eine
        '''   
        resultError = []
        for unit in self.unitNames:
            result = self.run_test( {
              "testid": "MT-4_1_2",
              "unit": unit,
              "year": 2020,
              "month": 1
            } )
            if result == False:
                resultError.append( unit )
        self.assertEqual( resultError, [], "Test fehlerhaft" )

    def test_field_MT_8_02_5_2019(self):
        '''
        Monatstest - MT_8.02-5 -

        '''
        resultError = []
        for unit in self.unitNames:
            result = self.run_test( {
              "testid": "MT-8_02-5",
              "unit": unit,
              "year": 2019,
            "month": 9
            } )
            if result == False:
                resultError.append( unit )
        self.assertEqual( resultError, [], "Test fehlerhaft" )

    def test_field_MT_VMAT_0_1_2019(self):
        '''
        Monatstest - MT_VMAT_0.1 -
        '''
        resultError = []
        for unit in self.unitNames:
            result = self.run_test( {
              "testid": "MT-VMAT-0_1",
              "unit": unit,
              "year": 2019,
              "month": 9
            } )
            if result == False:
                resultError.append( unit )
        self.assertEqual( resultError, [], "Test fehlerhaft" )         

    def test_field_JT_10_3_2019(self):
        '''
        Jahrestest - JT_10.3 - Vierquadrantentest

        Returns
        -------
        None.

        '''
        resultError = []
        for unit in self.unitNames:
            result = self.run_test( {
                "testid": "JT-10_3",
                "unit": unit,
                "year": 2019
            } )
            if result == False:
               resultError.append( unit )
        self.assertEqual( resultError, [], "Test fehlerhaft" )

    # ---- VMAT ----------------------------------------------

    def test_vmat_MT_VMAT_2_2019(self):
        '''
        Monatstest - MT_VMAT_2 -
        '''
        resultError = []
        for unit in self.unitNames:
            result = self.run_test( {
                "testid": "MT-VMAT-2",
                "unit": unit,
                "year": 2019,
                "month": 9
            } )
            if result == False:
                resultError.append( unit )
        self.assertEqual( resultError, [], "Test fehlerhaft" )
          

    def test_vmat_MT_VMAT_3_2019(self):
        '''
        Monatstest - MT_VMAT_3 -
        '''
        resultError = []
        for unit in self.unitNames:
            result = self.run_test( {
                "testid": "MT-VMAT-3",
                "unit": unit,
                "year": 2019,
                "month": 9
            } )
            if result == False:
               resultError.append( unit )
        self.assertEqual( resultError, [], "Test fehlerhaft" )
          

    # ---- WL ----------------------------------------------
    def test_wl_MT_WL_2019(self):
        '''
        Monatstest - MT_WL -
        '''
        resultError = []
        for unit in self.unitNames:
            result = self.run_test( {
              "testid": "MT-WL",
              "unit": unit,
              "year": 2019,
              "month": 9
            } )  
            if result == False:
                resultError.append( unit )
        self.assertEqual( resultError, [], "Test fehlerhaft" )            
          
    # ---- komplettes Jahr ---------------------------------
    def test_all_2021_01( self ):
        '''
            alle Jahrestests und Monatstests Januar 
        '''
        resultError = []
        for testid, item in self.webapp._config.GQA.items():
            month = 0
            if testid[0] == "M":
                month = 1
            for unit in self.unitNames:                
                result = self.run_test( {
                    "testid": testid,
                    "unit": unit,
                    "year": 2021,
                    "month": month
                } )  
                
                if result == False:
                    resultError.append( "{}.{}".format(testid, unit) )

        self.assertEqual( resultError, [], "Test fehlerhaft" )   
       
def suite( testClass:None ):
    '''Fügt alle Funktionen, die mit test_ beginnen aus der angegeben Klasse der suite hinzu

    Parameters
    ----------
    testClass : TYPE
        DESCRIPTION.

    Returns
    -------
    suite : TYPE
        DESCRIPTION.

    '''

    if not testClass:
        testClass = WebAppTest

    suite = unittest.TestSuite( )

    logger.setLevel( logging.WARNING ) # DEBUG WARNING


    #suite.addTest( testClass('test_other_Tagging') )
    #suite.addTest( testClass('test_other_configs') )
    # TODO: der alte test mit 96 Feldern gibt Fehler
    #suite.addTest( testClass('test_mlc_JT_LeafSpeed_2018') )
    #suite.addTest( testClass('test_mlc_JT_LeafSpeed_2020') )
   
    #suite.addTest( testClass('test_field_JT_10_3_2019') )
    #suite.addTest( testClass('test_mlc_MT_8_02_4_2020') )
    #suite.addTest( testClass('test_mlc_MT_VMAT_0_2_2020') )
    #suite.addTest( testClass('test_mlc_MT_VMAT_1_1_2020') )
   
    #suite.addTest( testClass('test_wl_MT_WL_2019') )
        
    #suite.addTest( testClass('test_all_2021_01') )
    
    
    #return suite


    if testClass:

        for m in dir( testClass ):
            if m.startswith('test_other_'):
                suite.addTest( testClass(m), )
                pass
            elif m.startswith('test_mlc_'):
                suite.addTest( testClass(m), )
                pass
            elif m.startswith('test_field_'):
                suite.addTest( testClass(m), )
                pass
            elif m.startswith('test_wl_'):
                suite.addTest( testClass(m), )
                pass
            elif m.startswith('test_vmat_'):
                suite.addTest( testClass(m), )
                pass
            elif m.startswith('test_all_'):
                suite.addTest( testClass(m), )
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
    test_result = runner.run( suite( WebAppTest ) )

    if cov:
        cov.stop()
        cov.save()

        cov.html_report()
