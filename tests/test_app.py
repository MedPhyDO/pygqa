# -*- coding: utf-8 -*-

"""


"""

# append project baspath to site
import os, site
from os import path as osp

ABSPATH = osp.dirname( osp.abspath( __file__) )
BASEPATH = osp.join( ABSPATH , "..")
FILESPATH = osp.join( BASEPATH, 'data', 'tests') 

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
from app import run

class testBase(testCaseBase):
    """
    setUp(), tearDown(), and __init__() will be called once per test.

    """

    called_tests = []  
    called_tests_url = []
    
    check_pdf = False
    check_data = False

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

        resources_path = os.path.join( ABSPATH, "resources" ) 
        check_path = os.path.join( FILESPATH, 'check')
        if not os.path.exists( check_path ):
            os.mkdir( check_path )
            
        # webapp mit unitest config
        self.webapp = run( {
            "loglevel" :{
                "safrs" : logging.DEBUG,
                #"webapp" : logging.INFO,
            },
            "server" : {
                "webserver" : {
                    "name" : "app_test",
                    "port" : 5001,
                    "TESTING": True,
                    "reloader" : False
                }
            },
            "database": {
                "servername" : "VMSCOM",
                "main": "gqa",
                "gqa" : {
                    "name" : "pygqa_unittest.json"
                }
            },
            "dicom": {
                "servername" : "VMSCOM",
                "VMSCOM" : {
                    "local_dir" : osp.join( FILESPATH, "DICOM" )
                }
            },
            "resultsPath" : FILESPATH,
            "version": "unittest",
            "variables" : {
                "Datenausgabe" : "unittest"
            }

        } )
        self.app = self.webapp.app
                    
        # Vergleichs Daten laden 
        self.data_file = osp.join( self.webapp._config.resultsPath, self.webapp._config.database.gqa.name )
        self.check_data_file = osp.join( check_path, 'pygqa.json')

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
          
        print( )
        print( "Called tests:")
        print( "=============")
        print( json.dumps(cls.called_tests_url, indent=2 )  )

        
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
        #self.app.
        # close the browser window
        #self.driver.quit()
        pass


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
            return

        url = '/api/gqa/run'

        self.called_tests.append( params )
        
        self.called_tests_url.append( "{}?{}".format( url, urlencode( params ) ) )
        
        # Unittest immer verwenden, damit das Ergebnis und nicht alle Daten des Jahres geliefert werden
        params["unittest"] = True

        response = self.app.get( url, query_string = params )
        
        self.assertEqual(response.status_code, 200, "Api Rückgabe fehlerhaft")
        
        result = response.json["data"]

        appError = response.json.get('App-Error', [] )
        # appInfo = response.json.get('App-Info', [] )

        # es dürfen keine App-Error Angaben vorliegen
        self.assertListEqual(
            appError, [],
            "App-Error: {}".format( json.dumps(appError)  )
        )

        self.assertGreater(
            len( result ), 0,
            "keine Test Rückgabe: '{unit}', '{testid}'".format( **params )
        )


        # pro pdffile die test_results im Ergebnis prüfen wenn es eine results datei gibt
        if self.gqa_data_ready:

            for pdf_name, data in result.items():
                self.called_tests.append(pdf_name )

                if self.check_pdf:
                    self.check_pdf_data( data["pdfData"] )
                
                if self.check_data:
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
                            '''
                            self.assertNotEqual(
                                orgData, {},
                                "keine Vergleichsdaten vorhanden: '{unit}', '{energy}', '{test}', '{date}', {group}".format( **test )
                            )
                            '''
                        else:
                            # über pandas mit double_precision=4 auswerten
                            # in data liegt als []
                            # json.loads( df[ fields ].to_json(orient='index', double_precision=10, indent=2 ) )
                        
                            #print( json.dumps(orgData['data'], indent=2 ) )

                            #print(orgData['data'])
                            #print(test['data'])
                            orgData_data = []
                            test_data = []
                            double_precision = 4 # oder 5
                            for data in orgData['data']:
                                #print( orgData['data'] )
                                df_org_data = pd.read_json( json.dumps(orgData['data'][0]), orient='index' ).sort_index()
                            
                                df_test_data = pd.read_json( json.dumps(test['data'][0]), orient='index' ).reindex(columns=df_org_data.columns).sort_index()
                                
                                orgData_data.append( json.loads(df_org_data.to_json( orient='index', double_precision=double_precision ) ) )
                                test_data.append( json.loads(df_test_data.to_json( orient='index', double_precision=double_precision ) ) )
                                '''
                                
                                df_compare = df_org_data.compare( df_test_data )
                                if len(df_compare) > 0:
                                    print( "Vergleichsdaten unterschiedlich: '{unit}', '{energy}', '{test}', '{date}', {group}".format( **test ) )
    
                                    print( "orgData_data", json.dumps(orgData['data'], indent=2 ) )
                                    print( "test_data", json.dumps(test['data'], indent=2 ) )       
                                '''  
                            
                            self.assertListEqual(
                                orgData_data,
                                test_data,
                                "Datenfehler im Testresult: '{unit}', '{energy}', '{test}', '{date}', {group}'".format( **test )
                            )
                            '''
                            # komplette genauigkeit testen
                            self.assertListEqual(
                                orgData['data'] or [],
                                test['data'] or [],
                                "Datenfehler im Testresult: '{unit}', '{energy}', '{test}', '{date}', {group}'".format( **test )
                            )
                            '''
                        

#
# ---- ab hier kommen die Tests -----------------------------------------------
#

class WebAppTest( testBase ):

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
    def test_mlc_MT_LeafSpeed_2020(self):
        ''' Monatstest - MT_LeafSpeed - IMRT - Geschwindigkeit und Geschwindigkeitsänderung der Lamellen
        '''
        
        for pid, unit in self.webapp._config.testunits.items():
          if self.webapp._config.units[ unit ]:
            self.run_test( {
                "testid": "MT-LeafSpeed",
                "unit": unit,
                "year": 2020,
                "month": 1
            } )


    # ---- MLC -----------------------------------------------

    def test_mlc_JT_10_3_1_2019(self):
        ''' Jahrestest - JT_10.3.1 - Leafabstand bei FWHM für alle Leafpaare

        Dieser Test wird auch für das Prüfen der Dicomübertragung verwendet

        .. todo:: im Test selbst fehlt noch der gesamt Check
        '''

        for pid, unit in self.webapp._config.testunits.items():
          self.run_test( {
              "testid": "JT-10_3_1",
              "unit": unit,
              "year": 2019
        } )
          

    def test_mlc_JT_4_2_2_1_A_2019(self):
        ''' Jahrestest - JT_4.2.2.1-A - Leaf Transmission

        '''

        for pid, unit in self.webapp._config.testunits.items():
          self.run_test( {
              "testid": "JT-4_2_2_1-A",
              "unit": unit,
              "year": 2019
        } )
          

    def test_mlc_JT_4_2_2_1_B_2019(self):
        ''' Jahrestest - JT_4.2.2.1-B - Interleaf Transmission
        '''

        for pid, unit in self.webapp._config.testunits.items():
          self.run_test( {
              "testid": "JT-4_2_2_1-B",
              "unit": unit,
              "year": 2019
        } )
          

    def test_mlc_JT_4_2_2_1_C_2019(self):
        ''' Jahrestest - JT_4.2.2.1-C - Interleaf Gap
        '''

        for pid, unit in self.webapp._config.testunits.items():
          self.run_test( {
              "testid": "JT-4_2_2_1-C",
              "unit": unit,
              "year": 2019
        } )

    def todo_test_mlc_JT_LeafSpeed_2018(self):
        ''' Jahrestest - JT_LeafSpeed - Geschwindigkeit der Lamellen DIN 6875-3, Teil 4.2.5 (Variationen von Dl, Gantry und Kollimator)
            96 Felder
        '''

        for pid, unit in self.webapp._config.testunits.items():
          self.run_test( {
              "testid": "JT-LeafSpeed",
              "unit": unit,
              "year": 2018
        } )
          
    
    def test_mlc_JT_LeafSpeed_2020(self):
        ''' Jahrestest - JT_LeafSpeed - Geschwindigkeit der Lamellen DIN 6875-3, Teil 4.2.5 (Variationen von Dl, Gantry und Kollimator)
            27 Felder
        '''

        for pid, unit in self.webapp._config.testunits.items():
          self.run_test( {
              "testid": "JT-LeafSpeed",
              "unit": unit,
              "year": 2020
        } )

    def test_mlc_MT_LeafSpeed_2019(self):
        ''' Monatstest - MT_LeafSpeed - IMRT - Geschwindigkeit und Geschwindigkeitsänderung der Lamellen
        '''

        for pid, unit in self.webapp._config.testunits.items():
          self.run_test( {
              "testid": "MT-LeafSpeed",
              "unit": unit,
              "year": 2019,
              "month": 9
        } )
          
        
    def test_mlc_MT_LeafSpeed_2020(self):
        ''' Monatstest - MT_LeafSpeed - IMRT - Geschwindigkeit und Geschwindigkeitsänderung der Lamellen
    
        '''
        for pid, unit in self.webapp._config.testunits.items():
          self.run_test( {
              "testid": "MT-LeafSpeed",
              "unit": unit,
              "year": 2020,
              "month": 1
        } )
          

        
    def test_mlc_MT_LeafSpeed_2021(self):
        ''' Monatstest - MT_LeafSpeed - IMRT - Geschwindigkeit und Geschwindigkeitsänderung der Lamellen
            ab 202106 mit collimator Angabe im result
        '''

        for pid, unit in self.webapp._config.testunits.items():
          self.run_test( {
              "testid": "MT-LeafSpeed",
              "unit": unit,
              "year": 2021,
              "month": 1
        } )
        
    def test_mlc_MT_8_02_1_2_2019(self):
        ''' Monattest MLC - MT_8.02-1_2

        Returns
        -------
        None.

        '''
        
        for pid, unit in self.webapp._config.testunits.items():
          self.run_test( {
              "testid": "MT-8_02-1-2",
              "unit": unit,
              "year": 2019,
              "month": 9
        } )


    def test_mlc_MT_8_02_1_2_2020(self):
        ''' Monattest MLC - MT_8.02-1_2

        Returns
        -------
        None.

        '''
        # Änderung: ohne Leaf 1 und 60  (noch nicht geändert in Testresult json)
        
        for pid, unit in self.webapp._config.testunits.items():
          self.run_test( {
              "testid": "MT-8_02-1-2",
              "unit": unit,
              "year": 2020,
              "month": 5
        } )
          
               

    def test_mlc_MT_8_02_3_2019(self):
        ''' Monattest MLC - 8.02-3

        Returns
        -------
        None.

        '''
        
        for pid, unit in self.webapp._config.testunits.items():
          self.run_test( {
              "testid": "MT-8_02-3",
              "unit": unit,
              "year": 2019,
              "month": 9
        } )

    def test_mlc_MT_8_02_4_2020(self):
        ''' Monattest MLC - 8.02-4

        Returns
        -------
        None.

        Wegen einer Änderung der Auswertung ab 2020/05 in mlc.doMLC_VMAT wird 2020 verwendet

        '''
        
        for pid, unit in self.webapp._config.testunits.items():
          self.run_test( {
              "testid": "MT-8_02-4",
              "unit": unit,
              "year": 2020,
              "month": 6
        } )
          

    def test_mlc_MT_VMAT_0_2_2020(self):
        ''' Monatstest - MT_VMAT_0.2 -

            Wegen einer Änderung der Auswertung ab 2020/05 in mlc.doMLC_VMAT wird 2020 verwendet
        '''

        for pid, unit in self.webapp._config.testunits.items():
          self.run_test( {
              "testid": "MT-VMAT-0_2",
              "unit": unit,
              "year": 2020,
              "month": 6
        } )
          

    def test_mlc_MT_VMAT_1_1_2020(self):
        ''' Monatstest - MT_VMAT_1.1 -

                Wegen einer Änderung der Auswertung ab 2020/05 in mlc.doMLC_VMAT wird 2020 verwendet
        '''

        for pid, unit in self.webapp._config.testunits.items():
          self.run_test( {
              "testid": "MT-VMAT-1_1",
              "unit": unit,
              "year": 2020,
              "month": 6
        } )


    def test_mlc_MT_VMAT_1_2_2020(self):
        ''' Monatstest - MT_VMAT_1.2 -

                Wegen einer Änderung der Auswertung ab 2020/05 in mlc.doMLC_VMAT wird 2020 verwendet
        '''

        for pid, unit in self.webapp._config.testunits.items():
          self.run_test( {
              "testid": "MT-VMAT-1_2",
              "unit": unit,
              "year": 2020,
              "month": 6
        } )

    # ---- field ----------------------------------------------

    def test_field_JT_7_2_2020(self):
        ''' Jahrestest - JT_7.2 -

        '''
        
        for pid, unit in self.webapp._config.testunits.items():
          self.run_test( {
              "testid": "JT-7_2",
              "unit": unit,
              "year": 2020
        } )



    def test_field_JT_7_3_2020(self):
        '''Jahrestest - JT_7.3

        '''

        for pid, unit in self.webapp._config.testunits.items():
          self.run_test( {
              "testid": "JT-7_3",
              "unit": unit,
              "year": 2020
        } )
        

    def test_field_JT_7_4_2019(self):
        ''' Jahrestest - JT_7.4 - Abhängikeit Kalibrierfaktoren vom Tragarm Rotationswinkel

        '''

        
        for pid, unit in self.webapp._config.testunits.items():
          self.run_test( {
              "testid": "JT-7_4",
              "unit": unit,
              "year": 2019
        } )
          

    def test_field_JT_7_4_2020(self):
        ''' Jahrestest - JT_7.4 - Abhängikeit Kalibrierfaktoren vom Tragarm Rotationswinkel

        '''
        
        
        for pid, unit in self.webapp._config.testunits.items():
          self.run_test( {
              "testid": "JT-7_4",
              "unit": unit,
              "year": 2020
        } )
          
       

    def test_field_JT_7_5_2019(self):
        '''
        Jahrestest - JT_7.5 - Abhängikeit Kalibrierfaktoren der Tragarmrotation
        ''' 
        for pid, unit in self.webapp._config.testunits.items():
            
          self.run_test( {
              "testid": "JT-7_5",
              "unit": unit,
              "year": 2019
        } )
        

    def test_field_JT_7_5_2020(self):
        '''
        Jahrestest - JT_7.5 - Abhängikeit Kalibrierfaktoren der Tragarmrotation

        TODO: keine Vergleichsdaten -> erzeugen
        '''
        
        for pid, unit in self.webapp._config.testunits.items():
          self.run_test( {
              "testid": "JT-7_5",
              "unit": unit,
              "year": 2020
        } )
          

    def test_field_JT_9_1_2_2019(self):
        '''
        Jahrestest - JT_9.1.2 - Abhängigkeit der Variation des Dosisquerprofils vom Tragarm-Rotationswinkel
        Test funktioniert mit EPID nur mit Aufbauplatte
        '''

        for pid, unit in self.webapp._config.testunits.items():
          self.run_test( {
              "testid": "JT-9_1_2",
              "unit": unit,
              "year": 2019
        } )
          

    def test_field_MT_4_1_2_2020(self):
        '''
        Monatstest - MT_4.1.2 - Linearität MU MT_4.1.2
        erst ab 2020 - result hat zwei Ergebnisse (tabellen) im json liegt aber nur eine
        '''
        
        for pid, unit in self.webapp._config.testunits.items():
          self.run_test( {
              "testid": "MT-4_1_2",
              "unit": unit,
              "year": 2020,
              "month": 1
          } )

    def test_field_MT_8_02_5_2019(self):
        '''
        Monatstest - MT_8.02-5 -

        '''
        
        for pid, unit in self.webapp._config.testunits.items():
          self.run_test( {
              "testid": "MT-8_02-5",
              "unit": unit,
              "year": 2019,
            "month": 9
        } )


    def test_field_MT_VMAT_0_1_2019(self):
        '''
        Monatstest - MT_VMAT_0.1 -
        '''

        for pid, unit in self.webapp._config.testunits.items():
          self.run_test( {
              "testid": "MT-VMAT-0_1",
              "unit": unit,
              "year": 2019,
              "month": 9
        } )
          

    def test_field_JT_10_3_2019(self):
        '''
        Jahrestest - JT_10.3 - Vierquadrantentest

        Returns
        -------
        None.

        '''
        
        for pid, unit in self.webapp._config.testunits.items():
          self.run_test( {
              "testid": "JT-10_3",
              "unit": unit,
              "year": 2019
            
        } )


    # ---- VMAT ----------------------------------------------

    def test_vmat_MT_VMAT_2_2019(self):
        '''
        Monatstest - MT_VMAT_2 -
        '''

        for pid, unit in self.webapp._config.testunits.items():
          self.run_test( {
              "testid": "MT-VMAT-2",
              "unit": unit,
              "year": 2019,
              "month": 9
        } )
          

    def test_vmat_MT_VMAT_3_2019(self):
        '''
        Monatstest - MT_VMAT_3 -
        '''

        for pid, unit in self.webapp._config.testunits.items():
          self.run_test( {
              "testid": "MT-VMAT-3",
              "unit": unit,
              "year": 2019,
              "month": 9
        } )
          

    # ---- WL ----------------------------------------------
    def test_wl_MT_WL_2019(self):
        '''
        Monatstest - MT_WL -
        '''
        
        for pid, unit in self.webapp._config.testunits.items():
          self.run_test( {
              "testid": "MT-WL",
              "unit": unit,
              "year": 2019,
              "month": 9
        } )  
          
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
   
    #suite.addTest( testClass('test_mlc_MT_8_02_4_2020') )
    #suite.addTest( testClass('test_mlc_MT_VMAT_0_2_2020') )
    #suite.addTest( testClass('test_mlc_MT_VMAT_1_1_2020') )
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

    return suite

# -----------------------------------------------------------------------------
if __name__ == '__main__':

    '''
    0 (quiet): you just get the total numbers of tests executed and the global result
    1 (default): you get the same plus a dot for every successful test or a F for every failure
    2 (verbose): you get the help string of every test and the result
    '''

    runner = unittest.TextTestRunner()
    runner.run( suite( WebAppTest ) )

    if cov:
        cov.stop()
        cov.save()

        cov.html_report()
