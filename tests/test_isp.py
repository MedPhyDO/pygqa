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

# Module auch von der Konsole erreichbar machen 
ABSPATH = os.path.dirname( os.path.abspath( __file__) )
path =  osp.join( ABSPATH , "..")

import sys
sys.path.insert(0, path)

import shutil
from shutil import copyfile

#print(sys.path)
import unittest
import json

import time
from datetime import datetime

import warnings
warnings.filterwarnings("ignore")

import pandas as pd
import io
import matplotlib.pyplot as plt
        
from skimage import io as img_io
from skimage.util import compare_images
import numpy as np

from flask import Response 

import dotmap

import threading

from safrs import jsonapi_rpc
from isp.config import ispConfig, dict_merge
from isp.webapp import ispBaseWebApp
from isp.safrs import db, system, ispSAFRSModel, ispSAFRSDummy, iso2date, isoDateType, isoDateTimeType
from isp.mpdf import PdfGenerator
from isp.plot import plotClass, rcParams

from sqlalchemy import MetaData

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


class dummy( ispSAFRSDummy ):
    """
        description: Tests - Test von ispSAFRSDummy
        ---
        
    """
    __tablename__ = "dummy"
    _database_key = ""
        
    config = None
    
    metadata = MetaData()
    
    @classmethod
    def init(self, kwargs:dict={} ):
        """
        Wird von den jsonapi_rpc funktionen aufgerufen

        Parameters
        ----------
        kwargs : dict, optional
            DESCRIPTION. The default is {}.

        Returns
        -------
        kwargs : TYPE
            DESCRIPTION.

        """    
        
        return kwargs
    
    @jsonapi_rpc( http_methods=['GET'] )
    def api_list(cls, **kwargs):
        """
            summary : alle Angaben
            description: alle Angaben
            parameters:
                - name : _ispcp
                  type: OrderedMap
                  in : query
                  default : {}
                  description : zusätzliche parameter
        ----
        {'data': [{
            'attributes': { }
            'id': '1', 
            'links': {'self': 'http://localhost/api/dbtests/1/'}, 
            'type': 'dbtests'
            }]
         'included': [], 
         'jsonapi': {'version': '1.0'}, 
         'links': {'self': 'http://localhost/api/dbtests/?page[offset]=0&page[limit]=250'}, 
         'meta': {'count': 7, 'limit': 250, 'offset': 0}, 
         'App-Error': [], 
         'App-Info': []
        }
        
        ist:
        {'data': [{
            'function': 'api_list', 
            'kwargs': {'_ispcp': {}}
            }], 
            'included': [], 
            'jsonapi': {'version': '1.0'}, 
            'meta': {'count': 0, 'limit': 250, 'offset': 0}, 
            'App-Error': [], 
            'App-Info': [{'message': 'safrs', 'info': 'Funktion: __main__.dummy.api_list()'}, {'message': 'kwargs', 'info': {'_ispcp': {}}}]}
        es fehlt:
            links
        """
        #print("dummy.api_list")
        cls.appInfo("kwargs", kwargs )
        _result = [ { 
            "attributes": { "function": "api_list", "kwargs" : kwargs }, 
            "id":"12", 
            "links": {"self": "http://localhost/api/dummy/12/"}, # autom. erzeugen
            "type": "dummy" # autom. erzeugen
        } ]  
        return cls._int_json_response( { "data": _result } )   
    
    @jsonapi_rpc( http_methods=['GET'] )
    def api_get(cls, **kwargs):
        """
            summary : eine Angabe
            description: eine Angabe
            parameters:
                - name : Id
                  in : path
                  type: integer
                  required : true
                  description : id - der Informationen
                - name : _ispcp
                  type: OrderedMap
                  in : query
                  default : {}
                  description : zusätzliche parameter
        ----
        
        {'data': {
            'attributes': {}, 
            'id': '7', 
            'links': {'self': 'http://localhost/api/dbtests/7/'}, 
            'type': 'dbtests'
            }, 
            'included': [], 
            'jsonapi': {'version': '1.0'}, 
            'links': {'self': 'http://localhost/api/dbtests/7/'}, 
            'meta': {'count': 1, 'instance_meta': {}, 'limit': 250, 'offset': 0}, 
            'App-Error': [], 
            'App-Info': []
        }
        
        """
        #print("dummy.api_get")
        # log.warning("gqa.api_get: {} id:{}".format( json.dumps(kwargs), cls.object_id ) )
        cls.appInfo("kwargs", kwargs )
        # normalerweise kein Datansatz in der Datenbank
        if kwargs[cls._s_object_id] == "gibtsnicht":
            
            _result = cls._int_get_empty_record( {"attributes": {cls._s_object_id : kwargs[cls._s_object_id] } })
        else:
            _result = {
                "attributes": {cls._s_object_id : kwargs[cls._s_object_id] },
                "id": 12,
                "links": {"self": "http://localhost/api/{}/{}/".format(cls.__name__, 12)}, # autom. erzeugen
                "type": cls.__name__ # autom. erzeugen
            }
        
        return cls._int_json_response( { "data": _result } )
    
    @classmethod
    @jsonapi_rpc( http_methods=['GET'] )
    def test( cls, **kwargs ):
        """
        description: test von api Funktionen und Parametern
        parameters:
                - name : _ispcp
                  in : query
                  default : {}
                  description : zusätzliche parameter
                  type: object
                - name : zahl
                  in : query
                  required : true
                  description : Eine Zahl
                  type: number
                - name : bool
                  in : query
                  required : false
                  default : false
                  description : Eine boolean Wert    
                  type: boolean
                - name : text
                  in : query
                  required : false
                  default : typenlos
                  description : Eine typenloser Wert mit default   
                 
        ----

        """
        #import sqlalchemy    
        
        cls.appInfo("kwargs", kwargs )
        
        _result = kwargs
        # verschiedene Rückgaben
       
        if kwargs["zahl"] == 1:
            # leere liste
            result = []   
        elif kwargs["zahl"] == 2:
            # liste mit einem Element
            result = [ {"a":1, "b":2} ]  
        elif kwargs["zahl"] == 3:
            # liste mit einem Element
            result = cls._int_json_response( "kein result" )
            
        elif kwargs["zahl"] == 4:
            # interne prüfungen
            cls._int_add_meta( info= "{\"is\":\"dict\"}" )
            result = []
        elif kwargs["zahl"] == 5:
            cls._int_parse_args( )
            result = []
        elif kwargs["zahl"] == 6:
            result = cls._int_query( [ { "A":1 }, { "B":2 } ] )
        elif kwargs["zahl"] == 7:
            result = cls._int_groupby_query( cls._s_query, { "A":1, "B":2 } )
        elif kwargs["zahl"] == 8:
            result = []
            db = cls.access_cls( "nicht da" )
            result.append( {"nicht da": ""} )
            db = cls.access_cls( "BigInteger" )
            result.append( {"sqlalchemy.BigInteger": ""} )
        elif kwargs["zahl"] == 9:
            result = [
                {'test=None': iso2date(None) }, 
                {'20180415=2018-04-15': iso2date('20180415', True) }, 
                {'2018-04-15=2018-04-15': iso2date('2018-04-15', True) }, 
                {'2018-04-15 14:36:25=2018-04-15': iso2date('2018-04-15 14:36:25', True) }, 
                {'2018-04-15=18-04-15 00:00:00': iso2date('2018-04-15') }, 
                {'2018-04-15 14:36:25=2018-04-15 14:36:25': iso2date('2018-04-15 14:36:25') }, 
                {'20180415 14:36:25=2018-04-15 14:36:25': iso2date('20180415 14:36:25') },
                {'20180415 14:36=2018-04-15 14:36:00': iso2date('20180415 14:36') },
                {'201A0415 14:36:25=None': iso2date('201A0415 14:36:25') },
                {'201A0415 14:36=None': iso2date('201A0415 14:36') },
                {'201A0415=None': iso2date('201A0415') }, 
            ]
        else: 
            # dict
            result = cls._int_json_response( { "data": _result } )  
            
        return result
             
    @classmethod
    @jsonapi_rpc( http_methods=['GET'] )
    def pdf( cls, **kwargs ):
        '''
        description: test von pdf Funktionen und Parametern
        parameters:
                - name : _ispcp
                  in : query
                  default : {}
                  description : zusätzliche Json parameter
                  type: object
                - name : name
                  in : query
                  required : false
                  default : nofile
                  description : Name der PDF Datei bestimmt die Art der pdf Erzeugung  
        ----
        
        '''
        cls.appInfo("kwargs", kwargs )
        
        mimetype='text/html'
        status = 200 
        
        # verschiedene Rückgaben
        if kwargs["name"] == "nofile":
            status = 400 
            result = "Keine PDF Datei ({}.pdf) gefunden".format( kwargs["name"] )
            cls.appError( "dummy/pdf", result)
            # Fehler in der leere liste
            return Response(result, status=status, mimetype=mimetype)
           
        pdfFile = "{}.pdf".format(kwargs["name"])
        variables = {
            "Klinik" : "MedPhyDO",
            "Abteilung" : "App Skeleton",
            "logo": "logo.png",
            "Datenausgabe" : "16.03.2020", 
            "Titel" : "unittest",
            "Betreff" : "PdfGenerator",
            "Auswertung" : "mpdf Test auch mit langem Text",
            "Erstelldatum": "",
            "Erstellt_von": "",
            "Geprüft_von": "",
            "Gültig_ab": "",
            "Freigegeben_von": "",
            "tip": "mpdf test tip für die Erstellung eines Unittest mit verschiedenen Elementen und PDF Rückgabe ",
            "Version" : "",
            "path": osp.join( ABSPATH , "files", "pdf"),
        }

        # print(pdfFile)
        # Inhalte vorbereiten
        
        # Testdateien  
        test_resources = osp.join( ABSPATH , "resources" ) 
        test_files = {
            "alpha" : osp.join( test_resources, 'alphachannel.svg' ),
            "python" : osp.join( test_resources, 'python.svg' ),
            "text" : osp.join( test_resources, 'test_text.txt' ),
            "markdown" : osp.join( test_resources, 'test_markdown.md' ),
            "markdown1" : osp.join( test_resources, 'test_markdown1.md' ),
            "markdown2" : osp.join( test_resources, 'test_markdown2.md' ),
            "logo" : 'logo.png',  # immer aus den normalen resources
        }
        
        # text
        text = """
            <h1>Lorem ipsum</h1>
            Lorem ipsum dolor sit amet, consectetuer adipiscing elit, sed diam nonummy nibh euismod tincidunt ut laoreet dolore magna aliquam erat volutpat. Ut wisi enim ad minim veniam, quis nostrud exerci tation ullamcorper suscipit lobortis nisl ut aliquip ex ea commodo consequat.
            <br>
            <b>kleiner Blindtext</b>
            Hallo. Ich bin ein kleiner Blindtext. Und zwar schon so lange ich denken kann. Es war nicht leicht zu verstehen, was es bedeutet, ein blinder Text zu sein: Man ergibt keinen Sinn. Wirklich keinen Sinn. Man wird zusammenhangslos eingeschoben und rumgedreht – und oftmals gar nicht erst gelesen. 
            
            Aber bin ich allein deshalb ein schlechterer Text als andere? 
            <br>
            """
        
        # data
        # pandas daten verwenden
        data = {
            "A" : { "A" : 1, "B": 1.5, "C": "test", "D":-0.2 },
            "B" : { "A" : 2, "B": 2.6, "C": "", "D": 1.2 },
            "C" : { "A" : 3, "B": 3.2, "C": "test", "D": 0.4 },
            "D" : { "A" : 4, "B": 4.1, "C": "", "D": -0.6 }
        }
        
        data_frame = pd.DataFrame(data)
        # zeilen und spalten tauschen, und nach C sortieren
        data_frame = data_frame.transpose().sort_values(by="C", ascending=False)
        # Für die tests Fontsize auf 10, sonst wird 20 verwendet
        rcParams["font.size"] = 10

        # rcParams["figure.figsize"] = (6.4, 4.8)
        # plt defaults setzen
        plt.rcParams.update( rcParams )
               
        # plot mit Pandas anzeigen
        data_frame.plot(kind='bar', title='Rating');
        # layout opimieren
        plt.tight_layout(pad=0.4, w_pad=0.5, h_pad=1.0)
        #plt.show()
        image_data = io.BytesIO()
        
        plt.savefig( image_data, format='png' )
        
        #
        # weasyprint
        #
        # erstmal nur mit config Angaben
        pdf = PdfGenerator( config=ispConfig( mqttlevel=logging.WARNING )  )
        
        # jetzt mit den anderen lädt config intern  
        pdf = PdfGenerator( filename=pdfFile, variables=variables )
        
        from isp.mpdf import DEFAULT_TEMPLATES
        
        # default templates erneut setzen um config änderungen für den test nicht zu verwenden
        # styles bereitstellen
        pdf.PAGE_STYLE = DEFAULT_TEMPLATES["PAGE_STYLE"]
        pdf.OVERLAY_STYLE = DEFAULT_TEMPLATES["OVERLAY_STYLE"]
 
        # html Gerüst bereitstellen
        pdf.header_html = DEFAULT_TEMPLATES["header_html"]
        pdf.footer_html = DEFAULT_TEMPLATES["footer_html"]
       
        if kwargs["name"] == "test-1":
            # leeres pdf erstellen
            # nur update metadata für coverage prüfen
            #pdf.updateMetadata( ) 
            pass
        elif kwargs["name"] == "test-2":
            
            # einfachen Text darstellen
            pdf.textFile( test_files["text"], { "width": 80 })
            
            # testet die HTML Ausgabe
            pdf.html( '<b>HTML Test</b>', attrs={ "font-size":"9px" } )
           
            # Markdown darstellen
            pdf.textFile( test_files["markdown"], { "width": 80 } )

            
        elif kwargs["name"] == "test-2a":
            # wie test 2 aber zuerst markdown und dann text 

            # Markdown darstellen
            pdf.textFile( test_files["markdown"], { "width": 80 } )  
            
            # testet die HTML Ausgabe
            pdf.html( '<b>HTML Test</b>', attrs={ "font-size":"9px" } )
             
            # einfachen Text darstellen
            pdf.textFile( test_files["text"], { "width": 80 })

            
        elif kwargs["name"] == "test-3":
            # Seiten erstellung 
            c1 = pdf.setContentName("Seite 1")
            pdf.text( "Inhalt 1" )
             
            # neuer Content / neue Seite  
            pdf.setContentName("Seite 2")
            pdf.text( "Inhalt 2" )
             
            pdf.newPage()
            pdf.text( "Inhalt 3" )
             
            pdf.newPage()
            pdf.text( "<h2>Seite 4</h2>" )
             
            pdf.text( "Inhalt 4" )
             
            # zum schluß noch in Content 1 auf der ersten Seite etwas einfügen
            pdf.setContentName(c1, False)
            pdf.text( "Inhalt 5 auf Seite 1" )    
             
        elif kwargs["name"] == "test-4":
            
            icon_data = [
                  { "acceptance": "True (5)", "icon": pdf.resultIcon( acceptance=True, iconOnly=True ) },
                  { "acceptance": "False (1)", "icon": pdf.resultIcon( acceptance=False, iconOnly=True ) },
                  { "acceptance": "1", "icon": pdf.resultIcon( acceptance=1, iconOnly=True ) },
                  { "acceptance": "2", "icon": pdf.resultIcon( acceptance=2, iconOnly=True ) },
                  { "acceptance": "3", "icon": pdf.resultIcon( acceptance=3, iconOnly=True ) },
                  { "acceptance": "4", "icon": pdf.resultIcon( acceptance=4, iconOnly=True ) },
                  { "acceptance": "5", "icon": pdf.resultIcon( acceptance=5, iconOnly=True ) },
                  { "acceptance": "falsch", "icon": pdf.resultIcon( acceptance="falsch", iconOnly=True ) },
            ]
            icon_frame = pd.DataFrame( icon_data )
            
            # Text darstellen
            pdf.text( text, { "width": 80 }, attrs={"border":"1px solid #FF0000"})
            
            # Text aus einer nicht vorhandenen Datei verwenden
            pdf.textFile( "gibtsnicht.md", { "width": 80 } )
            
            # Text aus einer vorhandenen Datei verwenden
            pdf.textFile( test_files["text"], { "width": 40, "top": 130 }, attrs={"border":"1px solid #FF0000"} )

            #
            # Angegebenes Bild anzeigen (svg)
            pdf.image( test_files["alpha"], { "width": 50, "top":125, "left":60 }, attrs={"border":"1px solid #FF0000"}  )
            
            # Bild aus resources (png)
            pdf.image(  test_files["logo"] , { "width": 30, "top":55, "left":95 }, attrs={"border":"1px solid #FF0000"}  )
            
            # Bild eines data_frame.plot autom. höhe nach Inhalt 
            img = '<div style="float:right;">'
            img += pdf.image( image_data, { "width": 60 }, render=False)
            img += "</div>"
            pdf.html(  img, { "width": 80, "top":80, "left":10 }, attrs={"border":"1px solid #FF0000"} )            
                  
            
            # pandas dataframe als Tabelle
            html = (
                data_frame.round(2).style
                .set_uuid( "test_pandas_" )
                .set_table_attributes('class="alayout-fill-width"') \
                .format( { 'A':'{0:.1f}', 'B':'{0:.1f}', 'D':'{0:.3f}'} )
                .hide_index()
                .highlight_max(subset=["D"], color='yellow', axis=0)
                .render()
            )
            pdf.html( html, attrs={ "font-size":"9px", "margin-left": "10px" } )
                
            
            # ohne Angaben (nicht passiert)  
            pdf.pandas()
            # leeres dataframe (nicht passiert)
            pdf.pandas(  pd.DataFrame() )
                
            # pandas sofort ohne id
            pdf.pandas( data_frame, 
                area={ "width": 50, "top": 180 },
                attrs={ "id": "test", "class":"unittest" }, # id des dataframe
                fields=[
                    { "field": "gibtsnicht" },
                    { "field": "A", "label":"is A", "format":"{}", "style": [('text-align', 'center')] },
                    { "field": "D", "format":"{0:.3f}", "style": [('text-align', 'right')] }
                ] 
            )
            
            pdf.pandas( icon_frame, 
                area={ "width": 50, "top": 5, "right": 0 },
               # attrs={ "id": "test", "class":"unittest" }, # id des dataframe
            )
            # pandas sofort mit id
            pdf.pandas( data_frame, 
                area={ "width": 50, "top": 180, "left": 60 },
                fields=[
                    { "field": "B", "label":"is B" },
                    { "field": "D" }
                ] 
            )
            # pandas ohne passende fields
            pdf.pandas( data_frame, 
                area={ "width": 50, "top": 180, "left": 120 },
                fields=[
                    { "field": "gibtsnicht" },
                ] 
            )
            pdf.resultIcon( 1 )
            # neuer contentName (erzeugt seitenumbruch)
            pdf.setContentName("Seite 3")
            
            # Text aus einer vorhandenen Datei verwenden
            pdf.textFile( test_files["markdown2"], { "width": 160 } )
            
            # leeren Text einfügen
            pdf.text( )
            
            # text intern einfügen
            pdf.text( 12 )
            
            # markdown intern einfügen
            pdf.markdown( "* Markdown **List** Element" )
            
            # seitenumbruch immer
            pdf.newPage()
            pdf.resultIcon( 5 )
            
            # neue Seite
            pdf.text( "Seite 3" )
            
            # ohne Angaben (nicht passiert)  
            pdf.pandasPlot()
      
            # mit Angaben in der Angegebenen größe plotten
            pdf.pandasPlot( data_frame, area={ "width": 100, "top": 30, "left": 20 }, kind='line', rot=75 )
       
            #  Text und TeX Formel nach SVG mit mathtext  
            pdf.mathtext( r"$a/b$" )
            
            # nur den htmlcode für eine neue Seite erzeugen
            pdf.newPage( False )
            
            # einfach ein icon zum prüfen der fonts
            pdf.icon( "mdi-paperclip", "x4") 

            # Plot Funktionen über die plotClass
            
            # plot anlegen
            plot = plotClass( )
            fig, ax = plot.initPlot( )
      
            # limits legende und grid
            ax.set_ylim( [-2.0, 2.0] )

            ax.grid( )
            ax.legend( )
            
            # als bar plot ausgeben
            data_frame.plot( ax=ax, kind='bar', rot=75)
            
            plt.tight_layout(pad=0.4, w_pad=0.5, h_pad=1.0)
            
            # chart im PDF anzeigen 
            pdf.image( plot.getPlot(), area={ "width": 100, "top": 130, "left": 20 } )
            # close all figures
            plt.close('all')
            # showPlot nur so für coverage durchführen
            plot.showPlot()
            
            
            
        if kwargs["name"] == "test-1":
            #
            # finish durchführen (coverage test)
            #        
            
            # 1. nur pdf erzeugen
            result = pdf.finish( )    
            pdf._variables["unittest"] = True
            # 2. als unittest pdf und png erzeugen (wie render_pdf_and_png)
            result = pdf.finish( )    
        else:
            #
            # pdf und png Datei erstellen
            #
            result = pdf.render_pdf_and_png( )           
        
        #
        # pdf und png Datei erstellen
        #        
        result = pdf.render_pdf_and_png( )
        
        
        return cls._int_json_response( { "data": result } )  
        
    
    @classmethod
    #@jsonapi_rpc( http_methods=['GET'] )
    def norpc( cls, **kwargs ):
        '''
        '''
        return ""
    
class dbtestsrel( ispSAFRSModel ):
    """
        description:  Tests - Test von ispSAFRSModel mit relationen
        ---
        
    """
    __table_args__ = {'extend_existing': True}
    
    __tablename__ = "dbtestsrel"
    
    id = db.Column('id', db.Integer, primary_key=True, unique=True, autoincrement=True)
    dbtests_id = db.Column( 'dbtests_id', db.Integer, db.ForeignKey("dbtests.id") ) 
    
    rstring = db.Column('rstring', db.String, nullable=False) # 

    rdate = db.Column('rdate', db.Date, nullable=True) # YYYYMMDD
    rinteger = db.Column('rinteger', db.Integer, nullable=True)
    rdata = db.Column('rdata', db.JSON ) # .. todo::json type?
    
    # relationen 
    dbtests = db.relationship("dbtests", back_populates="dbtestsrel", foreign_keys=[dbtests_id]) # one to many

class dbtests( ispSAFRSModel ):
    """
        description:  Tests - Test von ispSAFRSModel mit relationen
        ---
        
        In der Datenbank wird immer komplett abgelegt
        
       
        Specify 'extend_existing=True' to redefine options and columns on an existing Table object.


        Numeric auch DECIMAL
        
        precision=None,
        scale=None,
        decimal_return_scale=None, 
        asdecimal=True, - es wird ein formatierter string zurückgegeben (gerundet)
        
        db.Float( precision=5, asdecimal=True, decimal_return_scale=4 )
    """
    __table_args__ = {'extend_existing': True}
    
    __tablename__ = "dbtests"
    
    id = db.Column('id', db.Integer, primary_key=True, unique=True, autoincrement=True)
    string = db.Column('string', db.String, nullable=False) # 
    date = db.Column('date', db.Date, nullable=True) # YYYYMMDD
    isodatetime = db.Column('isodatetime', isoDateTimeType, nullable=True) # YYYY-MM-DD HH:mm:SS
    isodate = db.Column('isodate', isoDateType, nullable=True) # YYYY-MM-DD
    integer = db.Column('integer', db.Integer, nullable=True)
    data = db.Column('data', db.JSON ) # .. todo::json type?
    tags = db.Column('tags',  db.String, nullable=True)
    gruppe = db.Column('gruppe',  db.String, nullable=True)
    aktiv = db.Column('aktiv', db.Integer, nullable=False, default=True)
    float = db.Column('float', db.Float( asdecimal=True ), nullable=False, default=0) # (5,True,4) gibt 0.3333 als str
    
    decimal = db.Column('decimal', db.DECIMAL( 5, 2, 1, True ), nullable=False, default=0)
    numeric = db.Column('numeric', db.Numeric( 5, 2, 3, False ), nullable=False, default=0 )
    
    # relationen
    dbtestsrel = db.relationship("dbtestsrel", back_populates="dbtests", foreign_keys=[dbtestsrel.dbtests_id], lazy="dynamic", cascade="delete") # one to many
    
    def to_dict(self):
        # bei der Angabe asdecimal=True kommt ein str zurück deshalb diesen wieder in float umwandeln 
        result = ispSAFRSModel.to_dict(self)
        result["decimal"] = float( result["decimal"] )
        #print( result )
        return result
        
    @classmethod
    @jsonapi_rpc( http_methods=['GET'] )
    def test( cls, **kwargs ):
        """
            description : Zusätzliche Funkton
            parameters:
                - name : _ispcp
                  in : query
                  default : {}
                  description : zusätzliche parameter
                  type: object
                - name : zahl
                  in : query
                  required : true
                  description : Eine Zahl
                  type: number
                - name : bool
                  in : query
                  required : false
                  default : false
                  description : Eine boolean Wert    
                  type: boolean
                - name : text
                  in : query
                  required : false
                  default : typenlos
                  description : Eine typenloser Wert mit default   
                  
        ----   
        """
        #print( cls.object_id )
        
        cls.appDialog("dbtests", { "content" : " test Dialog", "dimensions" : [ 500, 200] }) 
        result = []
        #_result = kwargs
        if kwargs["zahl"] == 8:
            # Datenbank Klasse bestimmen
            db = cls.access_cls( "dbtests" )
        else:
            result = cls._int_get_empty_record( {"tags": "defaulttag"} )
            
        cls.appInfo("kwargs", kwargs, status_code=205 )
        return cls._int_json_response( { "data": result } )
        
         
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
    
    # _config.update( config )
    
    #print( _config )
    
    _apiConfig = {
        "models": [ system, dummy, dbtests, dbtestsrel ],
    }
    
    _webconfig = {
        # nur um update von webconfig zu testen
        "name" : "test_isp",
    }

    # Webserver starten
    webApp = ispBaseWebApp( _config, db, webconfig=_webconfig, apiconfig=_apiConfig )
    return webApp

class testBase(unittest.TestCase):
    '''
    setUp(), tearDown(), and __init__() will be called once per test.
    
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
        config_path = os.path.join( ABSPATH, '..', 'config')
        
        if not os.path.exists( files_path ):
            os.mkdir( files_path )
            
        # alte Datenbank löschen: über Pfad Angaben falls in der config nicht die testdatei steht 
        db_file = os.path.join( files_path, "tests.db" ) 
        if os.path.exists( db_file ):
            os.remove( db_file )

        # alle erzeugten pdf und den Pfad pdf löschen
        if os.path.exists( pdf_path ):
            shutil.rmtree( pdf_path )
        
        swagger_file = os.path.join( files_path, "swagger_test.json" )
        if not os.path.exists( swagger_file ):   
            with open(swagger_file, 'w') as fp: 
                obj = {
                    "info": {
                        "title": "swagger test"
                    }
                }
                json.dump(obj, fp, indent=2)
                     
        # webapp mit unitest config
        cls.webapp = run( {
            "loglevel" :{
                "safrs" : logging.DEBUG
                #"webapp" : logging.INFO,
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
                    "custom_swagger_config": os.path.join( files_path, "swagger_test.json" )
                }
               
            },
            "templates":{
                 "PDF-HEADER": None
            },
            "database": {
                "main": "tests",
                "tests" : {
                    "connection": "sqlite:///{{BASE_DIR}}/tests/files/tests.db"
                }
            }
        } )
        cls.app = cls.webapp.app
        
        #print("setUpClass", cls.webapp.config.get() )
        # Grunddaten in die Datenbank laden
        data = {
            "dbtests" : [ 
                { "string": "eins", "integer": 1, "gruppe":"A", "tags":"A,K", "aktiv":True  },
                { "string": "zwei", "integer": 2, "gruppe":"B", "tags":"B,M", "aktiv":False  },
                { "string": "drei", "integer": 3, "gruppe":"C", "tags":"M,K", "aktiv":True  },
                { "string": "vier", "integer": 4, "gruppe":"C", "aktiv":False  },
                { "string": "fünf", "integer": 5, "gruppe":"B", "tags":"A,K", "aktiv":True  }
            ],
            "dbtestsrel" : [
                { "dbtests_id": "1", "rstring": "r_eins", "rinteger": 11 },
                { "dbtests_id": "2", "rstring": "r_zwei", "rinteger": 12 },
                { "dbtests_id": "3", "rstring": "r_drei", "rinteger": 13 },
                { "dbtests_id": "4", "rstring": "r_vier", "rinteger": 14 },
                { "dbtests_id": "5", "rstring": "r_fünf", "rinteger": 15 }
            ]
        }
        for d in data["dbtests"]:
            response = cls.app.post( "api/dbtests/", headers={'Content-Type': 'application/json'}, data=json.dumps({ 
                "data": {
                    "attributes": d,
                    "type":"dbtests"
                }
            }))
        for d in data["dbtestsrel"]:
            response = cls.app.post( "api/dbtestsrel/", headers={'Content-Type': 'application/json'}, data=json.dumps({ 
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
            type(config.test), dotmap.DotMap, "__getitem__ Fehler bei nicht vorhandenen in der config")
        
        # __getattr__ wird bei nicht vorhandenen aufgerufen
        self.assertEqual(
            config._test, None, "__getitem__ Fehler bei nicht vorhandenen im Object")
        
        # __getitem__
        self.assertEqual(
            config["_loadErrors"], [], "__getitem__ Fehler")
        
        # __getitem__
        self.assertEqual(
            type(config["versions"]), dotmap.DotMap, "__getitem__ mit dotmap Fehler")
        
        # __getattr__ mit dotmap (config Values) 
        self.assertEqual(
            type(config.versions), dotmap.DotMap, "__getattr__ mit dotmap Fehler")
        
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
        <ul>
<li>Datum aus Parameter <strong>datum</strong> :{{datum}}</li>
<li>Inhalt aus Parameter: {{user}}</li>
</ul>
        Datum mit now: #datum#""".replace( "#datum#", datum )

        result_B = """<ul>
<li>testuser</li>
</ul>
        <ul>
<li>Datum aus Parameter <strong>datum</strong> :#datum#</li>
<li>Inhalt aus Parameter: testuser</li>
</ul>
        Datum mit now: #datum#""".replace( "#datum#", datum )
        
        meta = {
            "user" : "testuser",
            "datum": "{{ now.strftime('%d.%m.%Y') }}",
            "name": "{{user}}"
        }
        tpl = """{% markdown %}
        * {{ user }}
        {% endmarkdown %}
        {% include "test_template.tmpl" %}
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
            response.json["info"]["title"], "swagger test", "swagger file nicht ok")
         
        self.assertEqual( 
            list( response.json["paths"].keys() ),
            ['/dbtests/', '/dbtests/groupby', '/dbtests/test', '/dbtests/undefined', '/dbtests/{dbtestsId}/', '/dbtests/{dbtestsId}/dbtestsrel',
             '/dbtestsrel/', '/dbtestsrel/groupby', '/dbtestsrel/undefined', '/dbtestsrel/{dbtestsrelId}/', '/dbtestsrel/{dbtestsrelId}/dbtests',
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
            [{'attributes': {}, 'id': 'undefined', 'type': 'dummy'}],
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
        #print( response.json )
        
        response = self.app.get( "api/dummy/test", query_string={ "zahl": 5, "_ispcp" : "{test}"} )
        self.assertEqual(response.status_code, 200, "Status nicht 200")
        self.assertEqual( 
            response.json['App-Error'],
            [{'message': 'swagger Parameter Json Error', 'info': '_ispcp={test}'}],
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
            response.json['App-Error'],
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
            len(response.json["data"]), 5, "keine 5 Datensätze"
        ) 
        
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
        
        
    def test_webapp_db_tests_B( self ):
        ''' Api aufruf durchführen 
        GET /tests/
 
        '''         
        
        # einen undefined holen
        response = self.app.get( "api/dbtests/undefined")
        self.assertEqual(response.status_code, 200, "Api Status nicht 200")
        
        self.assertEqual(
            response.json["data"],
            [{'attributes': {
                'aktiv': None, 
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
            }, 'id': 'undefined', 'type': 'dbtests'}],
            "einen undefined holen"
        )
        
        # funktion test in dbtests aufrufen - gibt 205 als code
        response = self.app.get( "api/dbtests/test", query_string={
            "zahl" : 12 # Pflichfeld
        })
       
        #print(response.json["data"])
        self.assertEqual(response.status_code, 205, "Api Status nicht 205")
        self.assertDictEqual(
            response.json["data"],
            {'attributes': {
                'aktiv': None, 
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
                'tags': 'defaulttag'
            }, 'id': 'undefined', 'type': 'dbtests'},
            "einen undefined holen"
        )
        
        # fehler bei falscher Filterangabe 
        response = self.app.get( "api/dbtests/", query_string={
            "zahl" : 12, # Pflichfeld
            "filter" : "eq(tid=1)"
        })
        self.assertEqual(response.status_code, 200, "Api Status nicht 200")
        self.assertEqual(
            response.json["App-Error"],
            [{
                'message': '_int_filter', 
                'info': 'RQL Syntax error: (\'eq(tid=1)\', 6, \'Expected ")"\')'
             }],
            "fehler bei falscher Filterangabe "
        )
        
                
        # wird nur für htmlcov aufgerufen  
        response = self.app.get( "api/dbtests/test", query_string={
            "dbtestsId" : 2, # mit cls.object_id
            "zahl" : 12 # Pflichfeld
        })
        self.assertEqual(response.status_code, 205, "Api Status nicht 205")
        
        
    def test_webapp_db_tests_C( self ):           
        # einen nicht vorhandenen Datensatz abrufen
        # FIXME: Meldung auf der Konsole unterdrücken in method_wrapper vorher abfangen ?
        
        response = self.app.get( "api/dbtests/100")
        self.assertEqual(response.status_code, 404, "Api Status nicht 404 - notFound")
        
  
        
        
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
            len( response.json["data"] ), 5, "keine 5 Datensätze"
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
        
        
    def test_webapp_db_group( self ):
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
            {'attributes': {'hasChildren': 1, 'gruppe': 'A'}, 'id': None, 'type': 'dbtests'}, 
            {'attributes': {'hasChildren': 2, 'gruppe': 'B'}, 'id': None, 'type': 'dbtests'}, 
            {'attributes': {'hasChildren': 2, 'gruppe': 'C'}, 'id': None, 'type': 'dbtests'}
        ], "groupby mit fields Angabe Rückgabe fehlerhaft " )
        
        # mit groups Angabe
        response = self.app.get( "api/dbtests/groupby", query_string={
            "groups":"gruppe"
        })
        self.assertEqual(response.status_code, 200, "Api Status nicht 200")
        self.assertEqual( response.json["data"],[
            {'attributes': {'hasChildren': 1, 'gruppe': 'A'}, 'id': None, 'type': 'dbtests'}, 
            {'attributes': {'hasChildren': 2, 'gruppe': 'B'}, 'id': None, 'type': 'dbtests'}, 
            {'attributes': {'hasChildren': 2, 'gruppe': 'C'}, 'id': None, 'type': 'dbtests'}
        ], "groupby mit groups Angabe Rückgabe fehlerhaft " )
        
        
        # mit Filter und zwei Gruppierungs Feldern
        response = self.app.get( "api/dbtests/groupby", query_string={
            "groups[dbtests]":"gruppe,tags",
            "filter":"eq(aktiv,true)"
        })
        self.assertEqual(response.status_code, 200, "Api Status nicht 200")
        self.assertEqual( response.json["data"],[
            {'attributes': {'gruppe': 'A', 'hasChildren': 1, 'tags': 'A,K'}, 'id': None, 'type': 'dbtests'}, 
            {'attributes': {'gruppe': 'B', 'hasChildren': 1, 'tags': 'A,K'}, 'id': None, 'type': 'dbtests'}, 
            {'attributes': {'gruppe': 'C', 'hasChildren': 1, 'tags': 'M,K'}, 'id': None, 'type': 'dbtests'}
        ], "groupby mit Filter und zwei Gruppierungs Feldern fehlerhaft " )
        
        # mit delimiter
        response = self.app.get( "api/dbtests/groupby", query_string={
            "groups":"tags",
            "delimiter": ","
        })
        self.assertEqual(response.status_code, 200, "Api Status nicht 200")
        self.assertEqual( response.json["data"],[
            {'attributes': {'tags': 'A'}}, 
            {'attributes': {'tags': 'B'}}, 
            {'attributes': {'tags': 'K'}}, 
            {'attributes': {'tags': 'M'}}
        ], "groupby mit delimiter Rückgabe fehlerhaft " )
        
        # groupby mit label testen
        response = self.app.get( "api/dbtests/groupby", query_string={
            "groups":"gruppe",
            "labels": '{"dbtests.gruppe": "lGruppe"}'
        })
        self.assertEqual(response.status_code, 200, "Api Status nicht 200")
        self.assertEqual( response.json["data"], 
            [
                {'attributes': {'hasChildren': 1, 'lGruppe': 'A'}, 'id': None, 'type': 'dbtests'}, 
                {'attributes': {'hasChildren': 2, 'lGruppe': 'B'}, 'id': None, 'type': 'dbtests'}, 
                {'attributes': {'hasChildren': 2, 'lGruppe': 'C'}, 'id': None, 'type': 'dbtests'}
            ]          
            , "groupby mit label fehlerhaft " )
        
        # groupby mit zweifachen label testen
        response = self.app.get( "api/dbtests/groupby", query_string={
            "groups":"gruppe",
            "labels": '{"dbtests.gruppe": ["lGruppeA", "lGruppeB"]}'
        })
        
        self.assertEqual(response.status_code, 200, "Api Status nicht 200")
        self.assertEqual( response.json["data"], 
            [
                {'attributes': {'hasChildren': 1, 'lGruppeA': 'A', 'lGruppeB': 'A'}, 'id': None, 'type': 'dbtests'}, 
                {'attributes': {'hasChildren': 2, 'lGruppeA': 'B', 'lGruppeB': 'B'}, 'id': None, 'type': 'dbtests'}, 
                {'attributes': {'hasChildren': 2, 'lGruppeA': 'C', 'lGruppeB': 'C'}, 'id': None, 'type': 'dbtests'}
            ]          
            , "groupby mit label fehlerhaft " )
        
        # groupby mit fields und label testen
        response = self.app.get( "api/dbtests/groupby", query_string={
            "fields[dbtests]":"gruppe",
            "labels": '{"dbtests.gruppe": "lGruppe"}'
        })

        self.assertEqual(response.status_code, 200, "Api Status nicht 200")
        self.assertEqual(response.json["data"], 
            [
                {'attributes': {'lGruppe': 'A', 'hasChildren': 1}, 'id': None, 'type': 'dbtests'}, 
                {'attributes': {'lGruppe': 'B', 'hasChildren': 2}, 'id': None, 'type': 'dbtests'}, 
                {'attributes': {'lGruppe': 'C', 'hasChildren': 2}, 'id': None, 'type': 'dbtests'}
            ]  
            , "groupby mit fields und label fehlerhaft" )
        
        # groupby mit fields und zweifachen label testen
        response = self.app.get( "api/dbtests/groupby", query_string={
            "fields[dbtests]":"gruppe",
            "labels": '{"dbtests.gruppe": ["lGruppeA", "lGruppeB"]}'
        })

        self.assertEqual(response.status_code, 200, "Api Status nicht 200")
        self.assertEqual( response.json["data"], 
            [
                {'attributes': {'hasChildren': 1, 'lGruppeA': 'A', 'lGruppeB': 'A'}, 'id': None, 'type': 'dbtests'}, 
                {'attributes': {'hasChildren': 2, 'lGruppeA': 'B', 'lGruppeB': 'B'}, 'id': None, 'type': 'dbtests'}, 
                {'attributes': {'hasChildren': 2, 'lGruppeA': 'C', 'lGruppeB': 'C'}, 'id': None, 'type': 'dbtests'}
            ]  
            , "groupby mit fields und label fehlerhaft" )
        
        
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
            {'attributes': {'hasChildren': 1}, 'id': 5, 'type': 'dbtests'}
            ] , "id als gruppe wird ausgefiltert" )
        
        
        
    def test_webapp_db_typen( self ):
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
        
        #print( response.json["data"] )
        
        #self.assertEqual( response.status_code, 201, "Api Status nicht 201 (Created)")
        #self.assertEqual( response.json["data"]["attributes"]["date"], '2020-08-19', "Datensatz datum ist nicht 2020-08-19")     
        #self.assertEqual( response.json["data"]["attributes"]["data"], {"A":1}, 'Datensatz data ist nicht {"A":1}')                        
        #self.assertEqual( response.json["data"]["attributes"]["float"], 0.3333333333333333, 'Datensatz float ist nicht 0.3333333333333333')                        
                             
        
        response = self.app.post( "api/dbtests/", headers={'Content-Type': 'application/json'}, data=json.dumps({ 
            "data" : {
                "attributes": {
                    "string":"sechs",     # Pflichtfeld
                    "date":"2020-08-19", 
                    "integer": 6,
                    "data": {"A":1},
                    "float": 1/3,
                    "decimal" : 12345.3456,   # soll nur 12345.35 ergeben
                    "numeric" : 5.6789,
                    "isodate" :"2020-08-19",
                    "isodatetime" :"2020-08-19 14:37"
                },
                "type":"dbtests"
            }

        }), follow_redirects=True) 
        
        #print( response.json["data"] )
        pass
    
    def check_pdf_data( self, data, contents=-1, pages=-1, intern_check:bool=False ):
        ''' Prüft pdf data mit vorher gespeicherten data
        
        Erzeugt im unittest dir resources ein dir 'check', um dort die Vergleichsdaten zu speichern
        Gibt es dieses schon werden die dort vorhandenen Dateien als check verwendet
        
        Parameters
        ----------
        data : dict
            - body: dict
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
        #print( data["content"] )
        self.assertIn("pdf_filename", data,
            "PDF data fehlerhaft filename fehlt"
        )   
  
        self.assertIn("png_filepath", data,
             "PNG data fehlerhaft filepath fehlt"
        )
               
        check = {}
        
        if intern_check == True:
            check_dir = osp.join( ABSPATH, "resources", "check" )
        else:
            check_dir = osp.join( os.path.dirname( data["pdf_filepath"] ), "check" )
            
        # create the folders if not already exists
        if not os.path.exists( check_dir ):
            try:
                os.makedirs( check_dir )
            except IOError as e:
                 print("Unable to create dir.", e)
                 
        # Dateiname für den Inhalt festlegen
        json_check_name = osp.join( check_dir, data["pdf_filename"] ) + ".json"
        
        png_check_name = osp.join( check_dir, data["png_filename"] ) 
        
        png_new_name  = data["png_filepath"]
        
        # akltuellen content speichern
        with open( data["pdf_filepath"]  + ".json" , "w" ) as json_file:
            json.dump( data["content"] , json_file, indent=2 )
        
        # beim erstenmal pdfData content in unittest anlegen
        if not os.path.exists( json_check_name ):
            with open(json_check_name, "w" ) as json_file:
                # print("save", json_check_name)
                json.dump( data["content"] , json_file, indent=2 )
         
        if intern_check == True:
            pdf_check_name = osp.join( check_dir, data["pdf_filename"] )
            # beim erstenmal pdf nach check kopieren
            if not os.path.exists( pdf_check_name ):            
                # adding exception handling
                try:
                    copyfile( data["pdf_filepath"], pdf_check_name)
                except IOError as e:
                    print("Unable to copy file.", e)
                    
        # beim erstenmal png nach check kopieren
        if not os.path.exists( png_check_name ):            
            # adding exception handling
            try:
                copyfile(png_new_name, png_check_name)
            except IOError as e:
                print("Unable to copy file.", e)
                
        page_names = data["content"].keys()
        #print(page_names)
        # ggf Anzahl der Bereiche prüfen
        if contents > -1:
            self.assertEqual(
                len( page_names ),
                contents,
                "Anzahl der content Bereiche in '{}' stimmt nicht.".format( data["pdf_filepath"] )
            )
        # ggf Anzahl der Seiten prüfen
        if pages > -1:    
            self.assertEqual(
                data["pages"],
                pages,
                "Anzahl der Seiten in '{}' stimmt nicht.".format( data["pdf_filepath"] )
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
        
        # passende check daten (json_check_name) laden
        with open( json_check_name ) as json_file:
            check = json.load( json_file )
            
        # einige content Inhalte prüfen 
        from bs4 import BeautifulSoup 
        for page_name, content in data["content"].items():
            bs_data = BeautifulSoup( content, 'html.parser')
            bs_check = BeautifulSoup( check[ page_name ], 'html.parser')    
            
            # zuerst die texte
            data_text = bs_data.find_all('div', {"class": "text"} )
            check_text = bs_check.find_all('div', {"class": "text"} )
            self.assertEqual(
                data_text,
                check_text,
                "PDF content .text in '{}' ist fehlerhaft".format( data["pdf_filepath"] )
            )
            
            
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
        
        #print( "Der PNG Vergleichsbild MSE von '{}' ist '{}'.".format( data["png_filepath"] + ".diff.png", mse ) )
        #mse=0.0
        self.assertEqual( 0.0, mse, 
            "Der PNG Vergleichsbild MSE stimmt nicht. Diff image '{}' prüfen. Test erneut durchführen.".format( data["png_filepath"] + ".diff.png" )
        )
        
        
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
        
        # zuerst nur ein leeres PDF mit overlay
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
        
        #print( response.json )
        
        # .. todo:: rückgabe als pdf
        
    def check_weasyprint( self ):
        ''' Ein PDF Dokument mit weasyprint erstellen
       
        '''        
        
        # pdf weasyprint test 
        
        from weasyprint import HTML, CSS
        from weasyprint.fonts import FontConfiguration
        
        font_config = FontConfiguration()
        
        from weasyprint import default_url_fetcher

        files_loaded = []
        def log_url_fetcher(url):
            
            files_loaded.append( url )
            return default_url_fetcher(url)
        
        # HTML('<h1>foo') would be filename
        base_dir = os.path.join( ABSPATH, "..", "resources" )
        
        html = HTML(string='''
            <h1>The title</h1>
            <div class="blue-text">blauer Text</div>
            <span>mdi-check-outline: </span><span><i class="mdi mdi-check-outline"></></span><span> Oder?</span>
        ''')
        
        css = CSS(string='''
            @import url(mpdf_styles.css);
            h1 { font-family: Arial,"Helvetica Neue",Helvetica,sans-serif }
        ''', font_config=font_config, url_fetcher=log_url_fetcher, base_url=base_dir )
   
        pdf_file_name = os.path.join( ABSPATH, 'files', 'weasyprint.pdf')
        html.write_pdf( pdf_file_name, stylesheets=[css], font_config=font_config)

        # es sollten min. 5 Dateien eingelesen werden
        self.assertGreaterEqual(len(files_loaded), 5, "Anzahl nicht >= 5")
        
        
        # only test 4
        response = self.app.get( "api/dummy/pdf", query_string={ 
            "name" : "test-4"
        } )
        self.assertEqual(response.status_code, 200, "Status nicht 200")
        
        # kommt es hier zu einem Fehler stimmt die font Einbindung von weasyprint nicht
        self.check_pdf_data( response.json["data"], contents=2, pages=3, intern_check=True )
        # print( files_loaded, len(files_loaded) )
          
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
        
        #suite.addTest( testClass('test_config_jinja') )
        
        #suite.addTest( testClass('check_weasyprint') )
        #suite.addTest( testClass('test_webapp_db_tests_C') )
        #suite.addTest( testClass('test_webapp_db_tests_B') )
        #return suite
    
        for m in dir( testClass ):
            if m.startswith('test_config_'):
                suite.addTest( testClass(m),  )
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
   