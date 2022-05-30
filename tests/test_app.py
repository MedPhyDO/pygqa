# -*- coding: utf-8 -*-

"""


"""

# append project baspath to site
import os, site
ABSPATH = os.path.dirname( os.path.abspath( __file__) )
base_path = os.path.join( ABSPATH , ".." )
site.addsitedir(base_path)

from os import path as osp
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

        resources_path = os.path.join( ABSPATH , "resources" ) 
        
        check_path = os.path.join( resources_path, 'check')
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
                    "local_dir" : "files/DICOM"
                }
            },
            "resultsPath" : "files",
            "version": "unittest",
            "variables" : {
                "Datenausgabe" : "unittest"
            }

        } )
        self.app = self.webapp.app
                    
        # Vergleichs Daten laden 
        self.data_file = osp.join( self.webapp._config.resultsPath, self.webapp._config.database.gqa.name )
        self.check_data_file = osp.join( 'resources', 'check', 'pygqa.json')
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

        if self.gqa_data_ready == False:
            print("Es liegen noch keine Vergleichsdaten vor. Die Tests könnnen nicht geprüft werden.")

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

        self.assertGreater(
            len( result ), 0,
            "keine Test Rückgabe: '{unit}', '{testid}'".format( **params )
        )
        # es dürfen keine App-Error Angaben vorliegen
        self.assertListEqual(
            appError, [],
            "App-Error: {}".format( json.dumps(appError)  )
        )

        # pro pdffile die test_results im Ergebnis prüfen wenn es eine results datei gibt
        if self.gqa_data_ready:

            for pdf_name, data in result.items():
                self.called_tests.append(pdf_name )
                self.check_pdf_data( data["pdfData"] )
                
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

    def test_field_MT_4_1_2_2020(self):
        '''
        Monatstest - MT_4.1.2 - Linearität MU MT_4.1.2
        erst ab 2020 - result hat zwei Ergebnisse (tabellen) im json liegt aber nur eine
        '''
       
        for unit in self.webapp._config.units_TestsApp:
          self.run_test( {
              "testid": "MT-4_1_2",
              "unit": self.webapp._config.units[ unit ],
              "year": 2020,
              "month": 1
          } )


    def test_mlc_MT_LeafSpeed_2020(self):
        ''' Monatstest - MT_LeafSpeed - IMRT - Geschwindigkeit und Geschwindigkeitsänderung der Lamellen
        '''
        
        for unit in self.webapp._config.units_TestsApp:
          self.run_test( {
              "testid": "MT-LeafSpeed",
              "unit": self.webapp._config.units[ unit ],
              "year": 2020,
              "month": 1
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
