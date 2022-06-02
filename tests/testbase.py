# -*- coding: utf-8 -*-
'''

Use Ghostscript (gs) to convert pdf to png. Solution found in /tests/conftest.py

render_png() shape size A4 210x297mm

Parsing PDF in imagemagick has been disabled 
 - it can be enabled manually by editing /etc/ImageMagick-7/policy.xml file and removing PDF 
 from <policy domain="coder" rights="none" pattern="{PS,PS2,PS3,EPS,PDF,XPS}" />
 
TODO: change convert to other converting. Don't disable ImageMagick's security checks to make this work.


'''
import os
from os import path as osp
import sys
from subprocess import Popen, PIPE, STDOUT

import json
from shutil import copyfile
from skimage import io as img_io
from skimage.util import compare_images
import numpy as np

ABSPATH = osp.dirname( osp.abspath( __file__) )

import unittest

class testCaseBase(unittest.TestCase):
    
    
    def convert_to_png(self, pdf_filepath ):
        # 794x1123
        # -density xxx will set the DPI to xxx (common are 150 and 300).
        # -quality xxx will set the compression to xxx for PNG, JPG and MIFF file formates (100 means no compression).
        # +append horizontally instead of vertically with -append
        
        png_name = osp.splitext( pdf_filepath )[0] + '.png'
        
        geometry = 'x585' # x1754 (1/1) 'x877' (1/2) 'x585' (1/3) 

        output_type =  "png"
        
        # -background white -quality 90
        flags = '-background white -alpha remove -colorspace RGB  +append -density 72 -quality 50'
       # test_flags = '-alpha deactivate'      
        cmd = "convert {} -geometry {} {}:- '{}' '{}'".format( flags, geometry, output_type, pdf_filepath, png_name )
        
        # print( cmd )
        
        CLOSE_FDS = not sys.platform.startswith('win')
        process = Popen(
            cmd, shell=True,
            stdin=PIPE, stdout=PIPE, stderr=STDOUT,
            close_fds=CLOSE_FDS
        )
        
        result, error = process.communicate() 
 
        # bei Fehlern
        if error:
            print( "convert ERROR", cmd, result, error )
            return process.returncode
        else:
            return png_name
       
        
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
             "PDF data fehlerhaft. Filename fehlt"
        )

        check = {}

        #
        # Vorbereitungen
        #

        if intern_check == True:
            test_dir = osp.join( ABSPATH, "files", "pdf" )
            check_dir = osp.join( ABSPATH, "resources", "check" )
        else:
            test_dir = os.path.dirname( data["pdf_filepath"] )
            check_dir = osp.join( test_dir, "check" )
        

        # create the folders if not already exists
        if not osp.exists( check_dir ):
            try:
                os.makedirs( check_dir )
            except IOError as e:
                 print("Unable to create dir.", e)

        test_writable = True
        if not os.access(test_dir, os.W_OK):
            test_writable = False
            msg = 'testbase.check_pdf_data: keine Schreibrechte auf: {}'.format( test_dir )
            print(  msg )
            
        check_writable = True
        if not os.access(check_dir, os.W_OK):
            check_writable = False
            msg = 'testbase.check_pdf_data: keine Schreibrechte auf: {}'.format( check_dir )
            print(  msg )
            
        
        # Dateiname für den Inhalt festlegen
        json_test_name = osp.join( test_dir, data["pdf_filename"] ) + ".json"
        json_check_name = osp.join( check_dir, data["pdf_filename"] ) + ".json"

        pdf_check_name = osp.join( check_dir, data["pdf_filename"] )

        png_check_name = osp.splitext(pdf_check_name)[0] + '.png'
        png_new_name = osp.splitext(data["pdf_filepath"] )[0] + '.png'
        
        # create preview image from pdf
        if test_writable:
            self.convert_to_png( data["pdf_filepath"] )
               
        # changeback resources path in content
        if "_variables" in data:
            json_data = json.dumps( data["content"])
           
            json_data = json_data.replace( data["_variables"]["resources"], "{{resources}}")
            json_data = json_data.replace( data["_variables"]["templates"], "{{templates}}")
            data["content"] = json.loads(json_data)
        
        
        # immer den content in unittest ablegen
        if test_writable:
            with open(json_test_name, "w" ) as json_file:
                json.dump( data["content"] , json_file, indent=2 )
        
        if check_writable:
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

        #return
        # erzeugte png vergleichen und diff speichern
        png_check = img_io.imread( png_check_name )
        png_new = img_io.imread( png_new_name )
        
        # python 3.7 - cairo 1.16.0 (https://cairographics.org) - %PDF-1.5
        #   (1120, 790, 3) tests/files/pdf/test-1.pdf
        # python 3.8 - WeasyPrint 54.0 - %PDF-1.7
        #   (1123, 794, 3) tests/files/pdf/test-1.pdf
        #   (1123, 794, 4) 
        #return
        # check only size not depth
        self.assertEqual(
            list(png_check.shape)[:2], 
            list(png_new.shape)[:2], 
            "Die Bildgrößen in '{}' stimmen nicht.PDF files:\n{}\n{}".format( 
                data["pdf_filepath"],
                data["pdf_filepath"],
                pdf_check_name
            )
        )

        # Bild verleich erstellen und speichern
        compare = compare_images(png_check, png_new, method='diff')
        img_io.imsave( png_check_name + ".diff.png",  compare )

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

        # small changes depends on diffrent font rendering
        le = 350.0
        le = 100
        self.assertLessEqual( mse, le,
            "Der PNG Vergleichsbild MSE stimmt nicht. Diff image '{}' prüfen. PDF files:\n{}\n{}".format( 
                png_new_name + ".diff.png",
                data["pdf_filepath"],
                pdf_check_name
            )
        )