# -*- coding: utf-8 -*-


import io
from datetime import datetime
from os import path as osp

from dotmap import DotMap
import pandas as pd
import matplotlib.pyplot as plt

from flask import Response 
from sqlalchemy import MetaData
from safrs import jsonapi_rpc

from isp.mpdf import PdfGenerator
from isp.config import ispConfig
from isp.plot import plotClass, rcParams
from isp.safrs import ispSAFRSDummy, iso2date

# Module auch von der Konsole erreichbar machen 
ABSPATH = osp.dirname( osp.abspath( __file__) )
BASEPATH = osp.join( ABSPATH , "..")
FILESPATH = osp.join( BASEPATH, 'data', 'tests') 

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
            cls._int_add_meta( detail= "{\"is\":\"dict\"}" )
            result = []
        elif kwargs["zahl"] == 5:
            cls._int_parse_args( )
            result = []
        elif kwargs["zahl"] == 6:
            result = cls._int_query( [ { "A":1 }, { "B":2 } ] )
        elif kwargs["zahl"] == 7:
            result = cls._int_groupby_query(  { "A":1, "B":2 }, cls._s_query )
        elif kwargs["zahl"] == 8:
            result = []
            db = cls.access_cls( "nicht da" )
            result.append( {"nicht da": ""} )
            db = cls.access_cls( "BigInteger" )
            result.append( {"sqlalchemy.BigInteger": ""} )
        elif kwargs["zahl"] == 9:
           
            d = datetime(2018, 4, 15)

            result = [
                {'test=None': iso2date(None) }, 
                {'20180415=2018-04-15': iso2date('20180415', True) }, 
                {'2018-04-15=2018-04-15': iso2date('2018-04-15', True) }, 
                {'2018-04-15=2018-04-15': iso2date(d, True) }, 
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
            - name : format
              in : query
              required : false
              default : file
              description : Format der Ausgabe [ file, html, pdf ]
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
           
        # Testdateien  
        test_resources = osp.join( ABSPATH , "resources" ) 
        
        pdfFile = "{}.pdf".format(kwargs["name"])
        
        #print("test_resources", test_resources)
        # Inhalte vorbereiten
        
        test_files = {
            "alpha" : 'alphachannel.svg',
            "python" : 'python.svg',
            "logo" :  'logo.png',
            "text" :  'test_text.txt',
            "markdown" : 'test_markdown.md',
            "markdown1" :'test_markdown1.md' ,
            "markdown2" : 'test_markdown2.md' ,
            
           # "logo" : 'logo.png',  # immer aus den normalen resources
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
        data_frame.plot(kind='bar', title='Rating')
        # layout opimieren
        plt.tight_layout(pad=0.4, w_pad=0.5, h_pad=1.0)
        #plt.show()
        image_data = io.BytesIO()
        
        plt.savefig( image_data, format='png' )
        
        #
        # weasyprint
        #
        
        variables = {
            "Klinik" : "MedPhyDO",
            "Abteilung" : "tests",
            "logo": "logo.png",
            "Datenausgabe" : "jetzt", 
            "Titel" : "unittest",
            "Betreff" : "PdfGenerator",
            "Auswertung" : "mpdf Test auch mit langem Text",
            "Erstelldatum": "heute",
            "Erstellt_von": "unittest-1",
            "Geprüft_von": "unittest-2",
            "Gültig_ab": "sofort",
            "Freigegeben_von": "unittest-3",
            "tip": "mpdf test tip für die Erstellung eines Unittest mit verschiedenen Elementen und PDF Rückgabe ",
            "Version" : "u.0.1",
            "render_mode": kwargs["format"],
            #"path": osp.join( ABSPATH , "..", "tests", "files", "pdf"),
            "path": osp.join( FILESPATH , "pdf"),
            "resources": "file://{{BASE_DIR}}/tests/resources", 
            "resources_html": "/tests/resources",
        }
        
       
        # seperates config verwenden
        config = ispConfig( )
        # pdf erstellung bereitstellen
        config.update( DotMap({
          "resultsPath" :  FILESPATH,
          "pdf": {
            "page-style" : 'test_mpdf_page.css', # aus resources
            "overlay-style" : 'test_mpdf_overlay.css', # aus resources
          },
          "templates": {
            "PDF-PAGE_STYLE": "file://{{templates}}/test_mpdf_page_style.tmpl",
            "PDF-OVERLAY_STYLE": "file://{{templates}}/test_mpdf_overlay_style.tmpl",
            "PDF-HEADER_HTML": "file://{{templates}}/test_mpdf_header.tmpl",
            "PDF-FOOTER_HTML": "file://{{templates}}/test_mpdf_footer.tmpl",
          },
          "variables":{
              "Version" : "c.0.1", # wird von variables überschrieben
              "templates": test_resources, # wird wie resources gesetzt
          }
        } ) )
              
        if kwargs["name"] == "test-info":
            
            # Erstellung nur mit config Angaben prüfen
            pdf = PdfGenerator( )
            v1 = pdf._variables.get("Version")
       
            # Erstellung mit variables dies lädt config intern  
            pdf = PdfGenerator( filename=pdfFile, variables=variables )
            v2 = pdf._variables.get("Version")
            
            # variables überschreibt den variables Bereich aus config 
            pdf = PdfGenerator( variables=variables, filename=pdfFile, config=config )
            v3 = pdf._variables.get("Version")

            return cls._int_json_response( { "data": {
                "varianten":{
                    "v1": v1,
                    "v2": v2,
                    "v3": v3,
                },
                "_variables": pdf._variables,
                "pdf": pdf._config.get( "pdf" ),
                "style": pdf.style,
                "PAGE_STYLE": pdf.PAGE_STYLE,
                "OVERLAY_STYLE": pdf.OVERLAY_STYLE,
                "header_html": pdf.header_html,
                "footer_html": pdf.footer_html,
                "title": pdf.title
            } } )  
        
        # variables überschreibt den variables Bereich aus config 
        pdf = PdfGenerator( variables=variables, filename=pdfFile, config=config )
        
        if kwargs["name"] == "test-1":
            # leeres pdf erstellen
            # nur update metadata für coverage prüfen
            #pdf.updateMetadata( ) 
            pass
        elif kwargs["name"] == "test-2":
            
            # einfachen Text darstellen
            pdf.textFile( test_files["text"], { "width": 80 })
            
            # Markdown darstellen
            pdf.textFile( test_files["markdown"], { "width": 80 })

            # testet die HTML Ausgabe
            pdf.html( '<b>HTML Test</b>', attrs={ "font-size":"9px" } )
            
        elif kwargs["name"] == "test-2a":
            # wie test 2 aber zuerst markdown und dann text 
             
            # Markdown darstellen
            pdf.textFile( test_files["markdown"], { "width": 80 } )  
            
            # einfachen Text darstellen
            pdf.textFile( test_files["text"], { "width": 80 })
            
            # testet die HTML Ausgabe
            pdf.html( '<b>HTML Test</b>', attrs={"font-size":"9px" } )
                        
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
            pdf.image( test_files["logo"] , { "width": 30, "top":55, "left":95 }, attrs={"border":"1px solid #FF0000"}  )
            
            # fehlendes Bild
            pdf.image( "", { "width": 30, "top":55, "left":125 }, attrs={"border":"1px solid #FF0000"}  )
            
            
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
                .highlight_max(subset=["D"], color='yellow', axis=0)
                .to_html( sparse_index=False )
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
            # showPlot nur für coverage durchführen
            plot.showPlot()
        elif kwargs["name"] == "test-5":
            # Inhalte über template File einfügen
            pdf.textFile( "test_template.jinja" )
            # debug seite ausgeben
            pdf.printDebugPage()
            
        if kwargs["name"] == "test-1":
            #
            # finish durchführen (coverage test)
            #        
            
            # 1. nur pdf erzeugen
            result = pdf.finish( )    
            pdf._variables["unittest"] = True
            # 2. als unittest pdf und png erzeugen (wie render_pdf_and_png)
            result = pdf.finish( )
        elif  kwargs["format"] == "html":
            output = pdf.onTheFly( )
            # result is html
            return Response( output, mimetype='text/html')
        elif  kwargs["format"] == "pdf":
            # result is pdf
            output = pdf.onTheFly( )
            return Response( output, mimetype='application/pdf')
            
        #
        # pdf und png Datei erstellen
        #        
        #result = pdf.render_pdf_and_png( )
        result = pdf.render_pdf( )
        
        # add _variables to result
        result[ "_variables" ] = pdf._variables
        return cls._int_json_response( { "data": result } )  
        
    
    @classmethod
    #@jsonapi_rpc( http_methods=['GET'] )
    def norpc( cls, **kwargs ):
        '''
        '''
        return ""
    
