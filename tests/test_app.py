# -*- coding: utf-8 -*-

"""


"""
import os
from os import path as osp
from shutil import copyfile

# Module auch von der Konsole erreichbar machen 

ABSPATH = os.path.dirname( os.path.abspath( __file__) )
path =  osp.join( ABSPATH , "..")

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
from skimage import io as img_io
from skimage.util import compare_images
import numpy as np

import logging
logger = logging.getLogger( "MQTT" )

from app import run
 
class testBase(unittest.TestCase):
    """
    setUp(), tearDown(), and __init__() will be called once per test.
    
    """
 
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
                "main": "gqa",
                "gqa" : {
                    "name" : "gqa_unittest.json"
                }
            },
            "dicom": {
                "VMSDBD" : {
                    "local_dir" : "files/DICOM"
                }
            },
            "resultsPath" : "files/results",
            "version": "unittest",
            "variables" : {
                "Datenausgabe" : "unittest"
            }
            
        } )
        self.app = self.webapp.app
               
        # Vergleichs Daten laden 
        check_data_file = osp.join( 'resources', 'check', 'gqa_unittest.json')
        if osp.isfile( check_data_file ):
            self.gqa = pd.read_json( check_data_file, orient="table", precise_float=10 )
                        
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
        
        # Unittest verwenden, damit das Ergebnis und nicht alle Daten des Jahres geliefert werden
        params["unittest"] = True
        
        response = self.app.get( url, query_string = params ) 
        
        self.assertEqual(response.status_code, 200, "Api Rückgabe fehlerhaft")
        
        result = response.json["data"]
        appError = response.json['App-Error']
        appInfo = response.json['App-Info']
                
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
                self.check_pdf_data( data["pdfData"] )
                
                # pro test im pdffile
                for test in data["result"]:
                    #print("run_test - test", test )
                    #testid = self.testIds
                    try: 
                        orgData = self.gqa.loc[ test["unit"], test["energy"], test["test"], test["date"], test["group"] ].to_dict(  )
                    except:
                        orgData = {}
                                       
                    self.assertNotEqual(
                        orgData, {}, 
                        "keine Vergleichsdaten vorhanden: '{unit}', '{energy}', '{test}', '{date}', {group}".format( **test )
                    )
                      
                    self.assertListEqual( 
                        orgData["data"],
                        test["data"],
                        "Datenfehler im Testresult: '{unit}', '{energy}', '{test}', '{date}', {group}'".format( **test )
                    )     
       

    def check_pdf_data( self, data, contents=-1, pages=-1, intern_check:bool=False ):
        ''' Prüft pdf data mit vorher gespeicherten data
        
        Erzeugt in unittest dir auf dem Server ein dir 'check', um dort die Vergleichsdaten zu speichern
        
        Parameters
        ----------
        data : dict
            - content: dict
                page_names : dict
            - overlays: dict
            - pages: int
            - pdf_filename: string
            - pdf_filepath: string
            - png_filename: string
            - png_filepath: string
        contents : int
            Anzahl der Seiten im Content
        pages : int
            Anzahl der Seiten im PDF
        intern_check:
            Wenn True wird in tests und nicht im normalem pdf Ablegeort geprüft. Default is False 
            
        Returns
        -------
        None.
        
        '''

        self.assertIn("pdf_filepath", data,
             "PDF data fehlerhaft filename fehlt"
        )             
        self.assertIn("png_filepath", data,
             "PNG data fehlerhaft filepath fehlt"
        )
               
        check = {}
        
        #
        # Vorbereitungen
        #
        
        if intern_check == True:
            test_dir = osp.join( ABSPATH, "resources" )
        else:
            test_dir = os.path.dirname( data["pdf_filepath"] )
            
        check_dir = osp.join( test_dir, "check" )
        
        # create the folders if not already exists
        if not os.path.exists( check_dir ):
            try:
                os.makedirs( check_dir )
            except IOError as e:
                 print("Unable to create dir.", e)
                 
        # Dateiname für den Inhalt festlegen
        json_test_name = osp.join( test_dir, data["pdf_filename"] ) + ".json"
        json_check_name = osp.join( check_dir, data["pdf_filename"] ) + ".json"
        
        pdf_check_name = osp.join( check_dir, data["pdf_filename"] )
        
        png_check_name = osp.join( check_dir, data["png_filename"] ) 
        
        png_new_name  = data["png_filepath"]
        
        # immer den content in unittest ablegen
        with open(json_test_name, "w" ) as json_file:
            json.dump( data["content"] , json_file, indent=2 )
                
        # beim erstenmal content nach check kopieren
        if not os.path.exists( json_check_name ):
            try:
                copyfile(json_test_name, json_check_name)
            except IOError as e:
                print("Unable to copy file.", e)

        # beim erstenmal pdf nach check kopieren
        if not os.path.exists( pdf_check_name ):            
            try:
                copyfile(data["pdf_filepath"], pdf_check_name)
            except IOError as e:
                print("Unable to copy file.", e)
                    
        # beim erstenmal png nach check kopieren
        if not os.path.exists( png_check_name ):            
            try:
                copyfile(png_new_name, png_check_name)
            except IOError as e:
                print("Unable to copy file.", e)
        #    
        # Überprüfungen
        #
                
        # passende check daten (json_check_name) laden
        with open( json_check_name ) as json_file:
            check = json.load( json_file )
            
        page_names = data["content"].keys()
        # Anzahl der Bereiche prüfen
        if contents > -1:
            self.assertEqual(
                len( page_names ),
                contents,
                "Anzahl der content Bereiche in '{}' stimmt nicht.".format( data["pdf_filepath"] )
            )
        # Namen der Bereiche
        self.assertEqual(
            page_names,
            check.keys(),
            "Namen der Bereiche '{}' stimmt nicht.".format( data["pdf_filepath"] )
        )    
        
        # Anzahl der Seiten prüfen
        if pages > -1:    
            self.assertEqual(
                data["pages"],
                pages,
                "Anzahl der Seiten in '{}' stimmt nicht.".format( data["pdf_filepath"] )
            ) 
            
        # einige content Inhalte prüfen 
        from bs4 import BeautifulSoup 
        for page_name, content in data["content"].items():
            bs_data = BeautifulSoup( content, 'html.parser')
            bs_check = BeautifulSoup( check[ page_name ], 'html.parser')    
        
            # die text Bereiche
            data_text_list = bs_data.find_all('div', {"class": "text"} )
            check_text_list = bs_check.find_all('div', {"class": "text"} )

            self.assertEqual(
                data_text_list,
                check_text_list,
                "PDF content .text in '{}' ist fehlerhaft".format( data["pdf_filepath"] )
            )
           
        # erzeugte png vergleichen und diff speichern 
        png_check = img_io.imread( png_check_name )
        png_new = img_io.imread( png_new_name )

        self.assertEqual( 
            png_check.shape, 
            png_new.shape, 
            "Die Bildgrößen in '{}' stimmen nicht.".format( data["pdf_filepath"] )
        )
        
        # Bild verleich erstellen und speichern
        compare = compare_images(png_check, png_new, method='diff')
        img_io.imsave( png_new_name + ".diff.png",  compare )
              
        # gesamt check der Bilder
        def check_mse(imageA, imageB):
        	# the 'Mean Squared Error' between the two images is the
        	# sum of the squared difference between the two images;
        	# NOTE: the two images must have the same dimension
        	err = np.sum((imageA.astype("float") - imageB.astype("float")) ** 2)
        	err /= float(imageA.shape[0] * imageA.shape[1])
        	
        	# return the MSE, the lower the error, the more "similar"
        	# the two images are
        	return err

        # MeanCheck durchführen 
        try:
            mse = check_mse( png_check, png_new )
        except:
            mse = -1
        self.assertEqual( 0.0, mse, 
            "Der PNG Vergleichsbild MSE stimmt nicht. Diff image '{}' prüfen".format( data["png_filepath"] + ".diff.png" )
        )

# ---- ab hier kommen die Tests   
    
class WebAppTest( testBase ):    
    
    def test_base_2020( self ):
        url = '/api/gqa/2021'
            
        response = self.app.get( url ) 
        self.assertEqual(response.status_code, 200, "Api Rückgabe fehlerhaft") 

        
    def test_other_Tagging(self):
        ''' Gibt eine Liste alle Testbeschreibungen (config) mit Anleitungen 
        
        '''     
        url = '/api/gqa/tagging'
        
        # als json
        params = {}
        response = self.app.get( url, query_string = params )     
        self.assertEqual(response.status_code, 200, "Api Rückgabe fehlerhaft") 

        #  als html
        params = {
            "art" : "sum",
            "format": "html"
        }
        response = self.app.get( url, query_string = params )     
        self.assertEqual(response.status_code, 200, "Api Rückgabe fehlerhaft")      
         
        # als json
        params = {
            "art" : "test",
            "format": "html"
        }
        response = self.app.get( url, query_string = params )     
        self.assertEqual(response.status_code, 200, "Api Rückgabe fehlerhaft") 
        
        # als json
        params = {
            "art" : "tags",
            "format": "html"
        }
        response = self.app.get( url, query_string = params )     
        self.assertEqual(response.status_code, 200, "Api Rückgabe fehlerhaft")         
        
      
    def test_other_Tests(self):    
        
        url = '/api/gqa/2021'
        params = {}
        response = self.app.get( url, query_string = params )  
        self.assertEqual(response.status_code, 200, "Api Rückgabe fehlerhaft")  
        
    def test_other_Matrix(self):
        ''' Gibt eine Liste alle Testbeschreibungen (config) mit Anleitungen 
        '''     
        url = '/api/gqa/matrix'
        
        # als json
        response = self.app.get( url, query_string = {} )     
        self.assertEqual(response.status_code, 200, "Api Rückgabe fehlerhaft")   
        
        # als html
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
        
    def test_field_MT_4_1_2(self):
        '''
        Monatstest - MT_4.1.2 - Linearität MU MT_4.1.2
        '''

        self.run_test( { 
            "testid": "MT-4_1_2", 
            "unit": "Linac-1", 
            "year": 2021, 
            "month": 1
        } )
        
        self.run_test( { 
            "testid": "MT-4_1_2", 
            "unit": "Linac-2", 
            "year": 2021, 
            "month": 1
        } )
        
    def test_mlc_MT_LeafSpeed(self):
        ''' Jahrestest - JT_LeafSpeed - Geschwindigkeit der Lamellen DIN 6875-3, Teil 4.2.5 (Variationen von Dl, Gantry und Kollimator)
        '''

        self.run_test( { 
            "testid": "MT-LeafSpeed", 
            "unit": "Linac-1", 
            "year": 2021, 
            "month": 1
        } )
        
        self.run_test( { 
            "testid": "MT-LeafSpeed", 
            "unit": "Linac-2", 
            "year": 2021, 
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
