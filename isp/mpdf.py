# -*- coding: utf-8 -*-
"""

mpdf
====

Die mpdf Klasse ermöglicht das Erstellen von pdf Dateien wie die entsprechende PHP Version.

Sie verwendet als Grundlage weasyprint und html5lib

* autom. header und footer
* Grafiken über Pfadangabe mit Positions und Größen
* svg Dateien
* Generierte Grafiken 
* Lange texte 
* Tabellen aus panda
* CSS Unterstützung bei HTML Einbindung
* Verwendung von materialdesignicons-webfont.svg für icon

resources
---------
Angaben in config.json 

- variables : dict    

Abschnitt pdf:
    
- styles : str 
    Wird von resources geladen. Default: mpdf_styles.css
- overlay : str
    Wird von resources geladen. Default: mpdf_overlay.css
- logo : str 
    Wird von resources geladen. Default: logo.png
 
"""

__author__ = "R. Bauer"
__copyright__ = "MedPhyDO - Machbarkeitsstudien des Instituts für Medizinische Strahlenphysik und Strahlenschutz am Klinikum Dortmund im Rahmen von Bachelor und Masterarbeiten an der TU-Dortmund / FH-Dortmund"
__credits__ = ["R. Bauer", "K.Loot"]
__license__ = "MIT"
__version__ = "0.1.0"
__status__ = "Prototype"

from weasyprint import HTML, CSS

import pandas as pd

# markdown support
import markdown

# LaTeX support
import io
import matplotlib.pyplot as plt

import os
import os.path as osp
import base64
import string
from datetime import date, datetime

from isp.config import ispConfig, dict_merge
from isp.plot import rcParams

import logging
logger = logging.getLogger( "MQTT" )

ABSPATH = osp.dirname( osp.abspath( __file__) )
# weasyprint warnings abschalten
wp_logger = logging.getLogger('weasyprint')

# logger.addHandler( logging.FileHandler( osp.join( ABSPATH, '..', 'weasyprint.log') ) )
wp_logger.setLevel( logging.CRITICAL )


DEFAULT_TEMPLATES = {
    "PAGE_STYLE":"""
        @page {
            size: {{ page.size }}; 
            margin: {{page.header_height}}mm {{page.right}}mm {{page.footer_height}}mm {{page.left}}mm;
        }
    """,
    "OVERLAY_STYLE":"""
        @page {
            size: {{ page.size }}; 
            margin: {{page.top}}mm {{page.right}}mm {{page.bottom}}mm {{page.left}}mm;
        }
        .isp-header {
            height: {{page.header}}mm;
        }
        .isp-header .logo{
            height: {{page.header}}mm;
        }
    """,
    "header_html":"""<header>
        <table class="isp-header" ><tr>
            <td class="header_1 logo" rowspan="3"><img class="logo" src="file://{{resources}}/{{logo}}"></img></td>
            <td class="header_2 text">{{Klinik}}</td>
        </tr><tr>
            <td class="header_2 text">{{Abteilung}}</td>
        </tr><tr>
            <td class="header_2 text">{{Titel}} - {{Betreff}}</td>
        </tr></table>
        </header>
    """,
    "footer_html": """<footer>
        <table class="isp-footer" ><tr>
        	<td class="footer_1 name" rowspan="2">{{filename}}</td>
        	<td class="footer_2 text">Erstelldatum: {{Erstelldatum}} ({{Erstellt_von}})</td>
        	<td class="footer_3 text" colspan="2">Freigabe: {{Freigegeben_von}} ({{Gültig_ab}}) V.{{Version}}</td>
        </tr><tr>
            <td class="footer_2 text">geprüft: {{Geprüft_von}}</td>
            <td class="footer_3 text">Datenausgabe: {{Datenausgabe}}</td>
            <td class="footer_4 text">Seite <pagenum>{{pagenum}}</pagenum> von <pages>{{pages}}</pages></td>
        </tr></table></footer>
    """,
    "_PAGE_STYLE": "{% include \"mpdf_page_style.tmpl\" %}",
    "_OVERLAY_STYLE": "{% include \"mpdf_overlay_style.tmpl\" %}",
    "_header_html": "{% include \"mpdf_header.tmpl\" %}",
    "_footer_html": "{% include \"mpdf_footer.tmpl\" %}"
}


class PdfGenerator:
    """Generate a PDF out of a rendered template.
    
    With the possibility to integrate nicely a header and a footer if provided.
    
    .. note::
    
        - When Weasyprint renders an html into a PDF, it goes though several intermediate steps.
          Here, in this class, we deal mostly with a box representation: 1 `Document` have 1 `Page`
          or more, each `Page` 1 `Box` or more. Each box can contain other box. Hence the recursive
          method `get_element` for example.
          For more, see:
          https://weasyprint.readthedocs.io/en/stable/hacking.html#dive-into-the-source
          https://weasyprint.readthedocs.io/en/stable/hacking.html#formatting-structure
        - Warning: the logic of this class relies heavily on the internal Weasyprint API. This
          snippet was written at the time of the release 47, it might break in the future.
        - This generator draws its inspiration and, also a bit of its implementation, from this
          discussion in the library github issues: https://github.com/Kozea/WeasyPrint/issues/92
         
    Parameters
    ---------- 
    _variables: dict
        Default ist: {}
    title : str
        Dokumententitel Default ist ""
    meta : str
        PDF Dokument Metaangaben Default ist ""
    style : str
        Dokumentenstyle Default ist "body{ padding:5mm 0 5mm 0; }"
    head : str
        Dokumenteninhalt für Head Default ist ""
    body : str
        Dokumenteninhalt für Body Default ist ""
    header_html : str
        Dokumenteninhalt für Header Default ist ""        
    body_html : str
        Dokumenteninhalt für Body Default ist "" 
    footer_html : str
        Dokumenteninhalt für Footer Default ist ""
    pageContent: dict
        Inhalte wenn mehrere Seiten (mit unterseiten) verwendet werden sollen.  Default ist {}
    contentName: str
        Name des aktuellen contentBereichs. Default ist "_"
    pandas_table_id: int
        Die fortlaufende id für eine tabellen. Default ist 0
    autoRender:bool
        Automatisch rendern oder nur den Inhalt zurückgeben. Default ist True  
    
    """

    def __init__(self, variables:dict={}, autoRender:bool=True, config=None, filename: str=None ):
        """PDF vorbereiten.
        
        Parameters
        ----------
        variables: dict
            zum ergänzen oder ändern von config.variables
            _variables wird zum ersetzen von Schlüsselwörtern verwendet
                
        autoRender: bool - True
             Elemente sofort rendern oder nur zurückgeben
             
        config: dict oder isp config
            verwendet wird variables, templates und pdf
            
        filename:
            Den angegebenen Dateinamen verwenden und nicht aus den variables erzeugen
            
        """

        # Konfiguration
        if not config:
            self._config = ispConfig( mqttlevel=logging.WARNING )
        else:
            self._config = config
 
        # Defaultwerte der Klassse setzen
        self.set_class_defaults()    
        
        # default _variables Angaben mit config.variables ergänzen
        self._variables = dict_merge( self._variables, self._config.get( "variables", {} ) )
        # zusätzliche angegebene variables ergänzen
        self._variables = dict_merge( self._variables, variables ) 
        
        # Dateiname ggf. aus den metadaten aufbereiten
        if filename:
            self._variables["filename"] = filename
         
        self.autoRender = autoRender
       
        # overlay und page layout setzen
        self.set_page_defaults()
        
        # plot defaults setzen
        plt.rcParams.update( rcParams )
        

    def set_class_defaults(self):
        """Setzt default Werte für die Klasse.
                
        alle _variables Angaben können in config.json im Abschnitt variables überschrieben werden
        """
        self.OVERLAY_STYLE = ''
        self.PAGE_STYLE = ''

        self.template = """
            <!doctype html>
            <html>
              <head>
                <title>{title}</title>
                <meta charset="utf-8">
                {meta}
                <style>{style}</style>
                {head}
              </head>
              <body>
              {body}
              </body>
            </html>
        """
                
        self.title = '{{Titel}} - {{Betreff}}'
        self.meta = '' 
        self.style = 'body{ padding:5mm 0 5mm 0; }'
        self.head = ''
        
        self.header_html = ''
        self.footer_html = ''
    
        self._variables = {
            "page" : {
                "size" : "A4 portrait",  # a4 = 210x297 width=172.5 (soll 180)
                "left" : 20,  # LibreOffice Vorlage ISP 22.5,
                "right" : 9, # LibreOffice Vorlage ISP 15.0,
                "top" : 7.5,
                "bottom" : 6.0,
                "header" : 12,
                "footer": 5,
                "header-margin": 4,
                "footer-margin": 2
            },
            "resources": "{{BASE_DIR}}/resources", # Pfad zu den resources mit CSS und Fonts Angaben MPDF verwendet font format("svg")
            "logo": "logo.png",
            "path" : "{{BASE_DIR}}/files", 
            "filename": "noname.pdf",
            "Klinik" : "",
            "Abteilung" : "",
            "Titel" : "",  
            "Betreff" : "",  
            "Schlüsselwörter" : "",
            "Kommentare" : "",
            "Datenausgabe" : "{{ now.strftime('%d.%m.%Y') }}",
            "Erstelldatum" :"",
            "Erstellt_von" : "",
            "Geprüft_von" : "",
            "Gültig_ab" : "",
            "Version" : "",
            "Freigegeben_von" : ""
        } 
                    
        # defaults setzen
        self.pageContent = {}
        self.contentName = "_"
        self.overlayContent = {}
        self.autoRender = True
        self.pandas_table_id = 0
        self.isRendered = False
        
    def set_page_defaults(self):
        """Setzt die default Einstellungen für die Seiten.
        
        * ersetzt variables in resources, filename, path
        * Berechnet page Angaben header_height und footer_height
        * füllt OVERLAY_STYLE, PAGE_STYLE, header_html und footer_html
        
        """
        
        # resources render_template für wichtige _variables durchführen 
        self._variables["resources"] = self._config.render_template( self._variables["resources"], self._variables)
        self._variables["filename"] = self._config.render_template( self._variables["filename"], self._variables )
        self._variables["path"] = self._config.render_template( self._variables["path"], self._variables )
        
        # title Ersetzung durchführen 
        self.title = self._config.render_template( self.title, self._variables, deep_replace=True )
        
        # ränder für die Seiteninhalte berechnen - PAGE_STYLE
        page = self._variables["page"]
        self._variables["page"]["header_height"] = page["top"] + page["header"] + page["header-margin"] 
        self._variables["page"]["footer_height"] = page["bottom"] + page["footer"] + page["footer-margin"] 
        
        # styles bereitstellen
        self.PAGE_STYLE = self._config.get("templates.PDF-PAGE_STYLE", DEFAULT_TEMPLATES["PAGE_STYLE"])
        self.OVERLAY_STYLE = self._config.get("templates.PDF-OVERLAY_STYLE", DEFAULT_TEMPLATES["OVERLAY_STYLE"])
 
        # html Gerüst bereitstellen
        self.header_html = self._config.get("templates.PDF-HEADER", DEFAULT_TEMPLATES["header_html"])
        self.footer_html = self._config.get("templates.PDF-FOOTER", DEFAULT_TEMPLATES["footer_html"])
        
 
    def _getFilePath( self, ext:str="pdf" ):
        """Ensure the presence of _variables.path and gives filename and filepath.
        
        Parameters
        ----------
        ext: str
            File extension: pdf or png

        Returns
        -------
        filepath : str
            Name and path for the new file
        filename : str
            Name only for the new file
        """
        # ensure the presence of path
        if not os.path.isdir( self._variables["path"] ):
            logger.info('ispPdfClass.__init__: erzeuge path={}'.format(self._variables["path"]) )
            os.makedirs( self._variables["path"] )
            
        filename = osp.splitext(self._variables["filename"])[0] + '.' + ext
        filepath = osp.join( self._variables["path"], filename )
        return filepath, filename
        
    def render_pdf(self):
        """Generate PDF with all Pages.

        Returns
        -------
        result: dict
            - body
                html content of generated pages
            - overlays
                html content of generated overlay
            - content
                dict mit gerendertern html content 
            - pages
                Number of pages in generated file
            - pdf_filename: str
                 Name of the generated file
            - pdf_filepath: str
                 Name and path of the generated file
                
        """
        pdf_filepath, pdf_filename = self._getFilePath( "pdf" )
        main_doc, overlay_html, body_html = self.render( )
        
        main_doc.write_pdf( pdf_filepath )
        
        # Seiteninhalt zurückgeben
        return {
            "body": body_html, 
            "overlays": overlay_html, 
            "content": self.pageContent, 
            "pages" : len(main_doc.pages),
            "pdf_filename": pdf_filename,
            "pdf_filepath": pdf_filepath,
        }
    
    def render_png(self):
        """Generate PNG with all Pages.
        
        Returns
        -------
        result: dict
            - body
                html content of generated pages
            - overlays
                html content of generated overlay
            - content
                dict mit gerendertern html content 
            - pages
                Number of pages in generated file
            - png_filename: str
                Name of the generated file
            - png_filepath: str
                 Name and path of the generated file

        """
        png_filepath, png_filename = self._getFilePath( "png" )
        main_doc, overlay_html, body_html = self.render()
        
        main_doc.write_png( png_filepath )
        
        # Seiteninhalt zurückgeben
        return {
            "body": body_html, 
            "overlays": overlay_html, 
            "content": self.pageContent, 
            "pages" : len(main_doc.pages),
            "png_filename": png_filename,
            "png_filepath": png_filepath,
        }

    def render_pdf_and_png(self):
        """Generate PDF and PNG with all Pages in one step.

        Returns
        -------
        result: dict
            - body
                html content of generated pages
            - overlays
                html content of generated overlay
            - content
                dict mit gerendertern html content 
            - pages
                Number of pages in generated file
            - pdf_filename: str
                Name of the generated pdf file
            - pdf_filepath: str
                Name and path of the generated pdf file
            - png_filename: str
                Name of the generated png file
            - png_filepath: str       
                Name and path of the generated png file
            
        """
        pdf_result = self.render_pdf()
        png_result = self.render_png()
        
        result = pdf_result
        result[ "png_filename" ] = png_result[ "png_filename" ] 
        result[ "png_filepath" ] = png_result[ "png_filepath" ] 
       
        # Seiteninhalt zurückgeben
        return result

    
    def render(self):
        """Generate document.
        
        thereby summarizing all page content areas 
        
        * if individual pages were specified, generate a hidden h1
        * replace all jinja information {{}} with content from self._variables
        
        Returns
        -------
        main_doc: 
            gerenderte Dokument
        overlay_html: str
             html des gerenderten Overlays
        body_html: str
             html des gerenderten body

        """
        if not self.isRendered:
            self.isRendered = False
            
        # code für page break
        pageBreak = self.newPage( render=False )
                
        # alle Page content Bereiche zusammenfassen
        # wenn einzelne Seiten angegeben wurden ein hidden h1 erzeugen 
        pagenames = {}
        pagenum = 0
        for pageName in self.pageContent.keys():
            # Die Seitennummern beginnen bei 1
            pagenum += 1
            pagenames[ pagenum ] = pageName
            
            # pageContent nur beim ersten Funktionsaufruf ändern 
            if self.isRendered == False:
                if pageName[0] == "_":
                    h1 = ''
                else:
                    # Versteckter Name für einen Verzeichniseintrag
                    h1 = '<h1 style="visibility: hidden;position:absolute;height:0px">{}</h1>'.format( pageName )
            
                # Der eigentliche Seiteninhalt
                # der erste Seitenbereich muss mit einer Seite anfangen, deshalb pageBreak
                self.pageContent[ pageName ] = '<div class="pageContent">' + pageBreak + h1 + self.pageContent[pageName] + "</div>"
           
                # eingefügte autoNumber wieder entfernen 
                name = pageName
                cm = name.split(") - ")
                if len(cm) > 1:
                    name = cm[1]   
                    
                # Seite einfügen aktuellen contentName setzen und alle variablen ersetzen
                self._variables["contentName"] = name
                self.pageContent[ pageName ] = self._config.render_template( self.pageContent[ pageName ], self._variables, deep_replace=True )
                
        if self.meta == "":
            # datum aus Datenausgabe verwenden, sonst now()
            try:
                datum = datetime.strptime( self._variables["Datenausgabe"] , "%d.%m.%Y")
            except: # pragma: no cover 
                datum = datetime.now()
            
            self.meta += '<meta name="dcterms.created" content="{}" >'.format( datum.strftime("%Y-%m-%d") )
            self.meta += '<meta name="generator" content="MedPhyDO" >'
            self.meta += '<meta name="keywords" content="{}" >'.format( self._variables["Schlüsselwörter"] )
            
            # weitere meta möglichkeiten
            #
            '''
            <meta name=author>
            <meta name=description>
            <meta name=dcterms.created>
            <meta name=dcterms.modified>
            <link rel=attachment>
            '''
        
        
        # mit pagebreak zusammensetzen pageBreak
        body_html = pageBreak.join( self.pageContent.values() )
                    
        # template zusammensetzten
        main_html = self.template.format(
            title = self.title, meta = self.meta, style = self.style,
            head = self.head, body = body_html
        )

        html = HTML( string=main_html )
        
        # zusätzliche css file einbinden   
        stylesheets = []
        css_file = osp.join( 
            self._variables["resources"], 
            self._config.get( "pdf.page-style", "mpdf_page.css" )
        )
        # add additional CSS from css_file
        if os.path.isfile(css_file):
            stylesheets.append( CSS(filename=css_file) )
            
        # css aus PAGE_STYLE zusätzlich verwenden
        style_string = self._config.render_template(self.PAGE_STYLE, self._variables, deep_replace=True )
        stylesheets.append(CSS(string=style_string))
        
        # html mit stylesheets rendern
        main_doc = html.render(stylesheets=stylesheets)
        
        attrs = self._variables.copy()
        attrs["pages"] = len(main_doc.pages)
        
        #
        # Overlays
        #
        overlays = {}
        # style einmal rendern und immer verwenden
        self.OVERLAY_STYLE = self._config.render_template(self.OVERLAY_STYLE, self._variables, deep_replace=True )
        # alle seiten durchgehen und overlays einfügen
        pagenum = 0
        for page in main_doc.pages:
            
            # Die Seitennummern beginnen bei 1
            pagenum += 1
            # gibt es einen pagename, dann verwenden
            if pagenum in pagenames:
                pagename = pagenames[ pagenum ]
            else:
                pagename = pagenum
            # body der aktuellen Seite bestimmen
            page_body = PdfGenerator.get_element(page._page_box.all_children(), 'body')
            # header und/oder footer element erstellen
            # dabei variables erweitern
            attrs["pagenum"] = pagenum
            overlay, overlay_html = self._page_overlays( attrs )
            
            overlays[ pagename ] = overlay_html
            
            # header einfügen
            page_body.children += overlay.all_children()
           
        self.isRendered = True
        return main_doc, overlay_html, body_html
        
    
    def finish(self):
        """Complete document and return content.
        
        If unittest=True create additional png
        
        Returns
        -------
        pdf_data: dict
            information about the created pdf
        """
        if "unittest" in self._variables and self._variables[ "unittest" ] == True:
            pdf_data = self.render_pdf_and_png()
        else:
            pdf_data = self.render_pdf()
        
        return pdf_data
    
    def _page_overlays(self, attrs:dict={}):
        """Create page overlays header, footer and exchange attr.
        
        Parameters
        ----------
        attrs : dict
            
        Returns
        -------
        element_body:
            rendered overlay body Element
        overlay_html: str
            HTML Code from header_html and footer_html
        """
        # create an overlay and replace attrs 
        overlay_html = self._config.render_template( self.header_html + self.footer_html, attrs, deep_replace=True )
        
        # Create HTML Object from overlay_html
        html = HTML(
            string = overlay_html
        )
        
        # Include additional css file, overwrite the default with the config information
        #
        css_file = osp.join( 
            self._variables["resources"], 
            self._config.get( "pdf.overlay-style", "mpdf_overlay.css" )
        )
        
        stylesheets = []
        # add additional CSS from css_file
        if os.path.isfile(css_file):
            stylesheets.append( CSS(filename=css_file) )
       
        # add additional CSS from OVERLAY_STYLE
        stylesheets.append( CSS(string=self.OVERLAY_STYLE) )

        # create overlay with stylesheets
        element_doc = html.render( stylesheets=stylesheets )
        
        element_page = element_doc.pages[0]
        element_body = PdfGenerator.get_element(element_page._page_box.all_children(), 'body')
        element_body = element_body.copy_with_children(element_body.all_children())
        
        return element_body, overlay_html

    @staticmethod
    def get_element(boxes:list=[], element:str=""):
        """Bestimmt in boxes das passende Element.

        Given a set of boxes representing the elements of a PDF page in a DOM-like way, find the
        box which is named `element`.

        Look at the notes of the class for more details on Weasyprint insides.
        
        Parameters
        ----------
        boxes : list
            Liste mit Boxen.
        element : str
            zu suchende Box.

        Returns
        -------
        box
            Die gefundene Box.

        """
        for box in boxes:
            if box.element_tag == element:
                return box
            return PdfGenerator.get_element(box.all_children(), element)

       
    def _get_area_style(self, area:dict={}):
        """Generate a style string in mm from area with {left, top, with, height}.
        
        Parameters
        ----------
        area : dict, optional
            {left, top, with, height}. The default is {}.

        Returns
        -------
        style : str
            generated style string.

        """
        style = ""
        has_position = False
        for attr_name in [ 'left', 'top', 'width', 'height', 'bottom', 'right']:
           # attr_value = getattr(area, attr_name, None)
           # print( attr_name, attr_value )
            if attr_name in area:
                style += "{attr}:{value}mm;".format( attr=attr_name, value=area[attr_name] )
                if attr_name in ['left','top', 'bottom', 'right']:
                    has_position = True
          
        if has_position:
            style += "position:absolute;"

        return style
    
    def _get_attrs(self, attrs:dict={}):
        """Erzeugt aus einem attrs Element id, class und style Angaben.
        
        Bei Angabe von class und id wird zugeordnet.  
        Alles andere wird als style verwendet
        
        Parameters
        ----------
        attrs : dict, optional
            dict mit Attributen. The default is {}.

        Returns
        -------
        _id : str
            Die *id* Angabe aus attrs
        _class : str
            Die *class* Angabe aus attrs.
        _style : str
            Die *style* Angabe aus attrs.
        """
        _id = ""
        _class = ""
        _style = ""
        for key, value in attrs.items():
            if key == "id":
                _id = value
            elif key == "class":
                _class = value   
            else:
                _style += str(key) + ":" + str(value) + ";"
                 
        return _id, _class, _style
    
    def setContentName( self, name:str="_", autoNumber=True ):  
        """Bestimmt den Namen eines zusammenhängenden Seitenbereichs.
        
        Um auf einen vorhandenen umzuschalten muss autoNumber auf False gesetzt werden
        
        Parameters
        ----------
        name : str - default = _
            Name des zusammengehörigen Contentbereichts
        autoNumber:
            Nummer des Bereichs
            
        Returns
        -------
        name : str
            Der aktuelle contentName
        """
        if autoNumber:
            n = len(self.pageContent) + 1
            #self.contentNumber += 1 
            name = "({}) - {}".format(n, name)
 
        self.contentName = name
        
        return self.contentName

    def newPage( self, render=None ):
        """Einen Seitenumbruch einfügen.
        
        Parameters
        ----------
        render : bool
            sofort rendern oder nur zurückgeben ohne Angabe wird self.autoRender verwendet
        
        Returns
        -------    
        element_html : str
            HTML für den erzeugten Seitenumbruch
        """
        if render == None:
            render = self.autoRender
        element_html = '<p class="page_break" style="page-break-after: always;"></p>'
        
        if render:
            self._html(element_html) 
            
        return element_html
        
    
    def _html( self, html:str="" ):    
        """Internes anfügen von html im aktuellem pageContent.
        
        Parameters
        ----------
        html : str, optional
            Anzufügender Inhalt. The default is "".

        Returns
        -------
        None.

        """
        if not self.contentName in self.pageContent:
            self.pageContent[ self.contentName ] = ""
            
        self.pageContent[ self.contentName ] += html
        
    def html( self, html="", area:dict={}, attrs:dict={}, render=None ):    
        """HTML einfügen.
        
        Parameters
        ----------
        html : str
        
        area : Area {left,top,with,height}
            die Größe der Ausgabe       
        attrs : dict
            zu ändernde id class oder Style Angaben
        render : bool
            sofort rendern oder nur zurückgeben ohne Angabe wird self.autoRender verwendet
        
        Returns
        -------
        element_html: str
            HTML des erzeugten Elements
        """
        if render == None:
            render = self.autoRender
            
        # Eigenschaften des Elements
        _id, _class, _style = self._get_attrs( attrs )
        
        _area = self._get_area_style( area )

        element_html = '\n\t<div class="html {_class}" style="{_style} {_area}" >{content}</div>'.format(
                _class  = _class, 
                _style  = _style, 
                _area   = _area,
                content = html
        )
       
        if render:
            self._html( element_html )
        return element_html
        
    def _text( self, text="", area:dict={}, attrs:dict={}, render=None, replaceNewLine=False  ):
        r"""Einen Textabsatz einfügen.
        
        Dabei je nach replaceNewLine ``\n`` bzw. ``\n\n`` durch ``<br>`` ersetzen
        
        Parameters
        ----------
        text : str
            Der einzufügende Text
        area : Area {left,top,with,height}
            die Größe der Ausgabe       
        attrs : dict
            zu ändernde id class oder Style Angaben
        render : bool
            sofort rendern oder nur zurückgeben ohne Angabe wird self.autoRender verwendet
        replaceNewLine : bool - false
             nur doppelte ``\n\n`` durch ``<br>`` ersetzten oder alle newLine ``\n`` ersetzen
        
        Returns
        -------
        element_html: str
            HTML des erzeugten Elements
        """
        if render == None:
            render = self.autoRender
            
        if not text:
            text = ''
        if not isinstance(text, str):
            text = str(text)
            
        text = text.strip(string.whitespace)
        if replaceNewLine:
            text = text.replace('\n', "<br/>")
        else:
            text = text.replace('\n\n', "<br/>")
        # Eigenschaften des Elements
        if not "font-size" in attrs:
            attrs["font-size"] = "8pt"
        _id, _class, _style = self._get_attrs( attrs )
        _area = self._get_area_style( area )
        
        element_html = '\n\t<div class="text {_class}" style="{_style} {_area}" >{content}</div>'.format(
                _class = _class, 
                _style = _style, _area=_area,
                content=text
        )
        
        if render:
            self._html( element_html )
        return element_html
 
    def markdown( self, text="", area:dict={}, attrs:dict={}, render=None ):
        """Einen Markdowntext einfügen.
        
        Parameters
        ----------
        text : str
            Der einzufügende Text
        area : Area {left,top,with,height}
            die Größe der Ausgabe       
        attrs : dict
            zu ändernde id class oder Style Angaben
        render : bool
            sofort rendern oder nur zurückgeben ohne Angabe wird self.autoRender verwendet
             
        Returns
        -------
        element_html: str
            HTML des erzeugten Elements
        """
        if render == None:
            render = self.autoRender
            
        html = markdown.markdown( text, extensions=['extra', 'codehilite'] )
        
        # Eigenschaften des Elements
        if not "font-size" in attrs:
            attrs["font-size"] = "8pt"
        _id, _class, _style = self._get_attrs( attrs )
        _area = self._get_area_style( area )
        
        element_html = '\n\t<div class="text markdown {_class}" style="{_style} {_area}" >{content}</div>'.format(
                _class  = _class, 
                _style  = _style, 
                _area   = _area,
                content = html
        )
        
        if render:
            self._html( element_html )     
        return element_html
                
    def text( self, text="", area:dict={}, attrs:dict={}, render=None, replaceNewLine=True, mode:str="text" ):
        r"""Einen Textabsatz einfügen dabei ``\n`` durch ``<br>`` ersetzen.
        
        Parameters
        ----------
        text : str
            Der einzufügende Text
        area : Area {left,top,with,height}
            die Größe der Ausgabe       
        attrs : dict
            zu ändernde id class oder Style Angaben
        render : bool
            sofort rendern oder nur zurückgeben ohne Angabe wird self.autoRender verwendet
        replaceNewLine : bool - True
             nur doppelte ``\n\n`` durch ``<br>`` ersetzten oder alle newLine ``\n`` ersetzen
        mode :  str - text
            Bei angabe von `markdown` als nicht als einfachen text sondern als markdown rendern 
        
        Returns
        -------
        element_html: str
            HTML des erzeugten Elements
        """
        if mode == "markdown":
            return self.markdown( text, area, attrs, render )
        else:
            return self._text( text, area, attrs, render, replaceNewLine )
     
    def textFile( self, filename:str=None, area:dict={}, attrs:dict={}, render=None, replaceNewLine=False ):
        r"""Lädt aus self._data["resources"] eine Datei und zeigt sie wie bei add_text an.
        
        Bei der Dateiendung .txt wird eine Ersetztung von ``\n`` zu ``<br>`` vorgenommen
        
        Parameters
        ----------
        filename : str
            Der zu ladende Dateiname
        area : Area {left,top,with,height}
            die Größe der Ausgabe          
        attrs : dict
            zu ändernde id class oder Style Angaben
        render : bool
            sofort rendern oder nur zurückgeben ohne Angabe wird self.autoRender verwendet
        replaceNewLine : bool
            nur doppelte ``\n\n`` durch ``<br>`` ersetzten oder alle newLine ``\n`` ersetzen
                         
        Returns
        -------
        element_html: str
            HTML des erzeugten Elements
        """
        
        if not filename:
            return
        
        text = None
        filepath = osp.join( self._variables["resources"], filename )
        if osp.exists( filepath ):
            with open( filepath, 'r', encoding="utf-8") as myfile:
                text = myfile.read()
        
        if text:
            root, ext = osp.splitext( filename )
            if ext.lower() == ".txt":
                replaceNewLine = True
            elif ext.lower() == ".md":
                return self.markdown( text, area, attrs, render )
                
            return self._text( text, area, attrs, render, replaceNewLine )

    def mathtext(self, text, area:dict={}, attrs:dict={}, render=None, fontsize=12, dpi=300):
        r"""Rendert Text und TeX Formel nach SVG mit mathtext.
        
        https://matplotlib.org/3.1.1/tutorials/text/mathtext.html
        
        Die Formel muss mit $ anfangen und enden und der string als raw r"" angegeben werden
        
        Beispiel: r"$a/b$"
        
        Parameters
        ----------
        text : str
            Der einzufügende Text
        area : Area {left,top,with,height}
            die Größe der Ausgabe          
        attrs : dict
            zu ändernde id class oder Style Angaben
        render : bool
            sofort rendern oder nur zurückgeben ohne Angabe wird self.autoRender verwendet
            
        fontsize (int, optional): Font size.
        
        dpi (int, optional): DPI.
        
        Returns
        -------
        element_html: str
            HTML des erzeugten Elements 
        """
        fig = plt.figure(figsize=(0.01, 0.01))
        fig.text(0, 0, text, fontsize=fontsize)
    
        output = io.BytesIO()
        fig.savefig(output, dpi=dpi, transparent=True, format='svg',
                    bbox_inches='tight', pad_inches=0.0, frameon=False)
        plt.close(fig)
        
        return self.image( output, area, attrs, render, 'svg+xml' )
        
         
    def image(self, image: [str, io.BytesIO], area:dict={}, attrs:dict={}, render=None, imageType="png"):
        """Bild an der aktuellen Cursor Position oder wenn angegeben bei x, y einfügen.
        
        Internen Cursor auf die neuen x,y Positionen setzen
        
        Das Image wird wenn möglich rechts eingefügt. 
        
        Parameters
        ----------
        image : str|io.BytesIO
            Das eigentliche Bild
        area : Area {left,top,with,height}
            die Größe der Ausgabe       
        attrs : dict
            zu ändernde id class oder Style Angaben
        render : bool
            sofort rendern oder nur zurückgeben ohne Angabe wird self.autoRender verwendet
        imageType : str
            png
            svg+xml
            
        Returns
        -------
        element_html: str
            HTML des erzeugten Elements
            
            .. code::
                
                <img src="data:image/png;base64,{{image}}" />
                oder 
                <img src="file://{{image}}" />

        """
        if render == None:
            render = self.autoRender
            
        element_html = ""
        # Eigenschaften des Elements
        if not "font-size" in attrs:
            attrs["font-size"] = "8pt"
            
        _id, _class, _style = self._get_attrs( attrs )
        _area = self._get_area_style( area )
        
        if isinstance(image, io.BytesIO):
            # Bild steckt in image
            image.seek(0)
            context = base64.b64encode( image.getvalue() ).decode("ascii")
            element_html = '\n\t<img class="image {_class}" style="{_style} {_area}" src="data:image/{_type};base64,{content}" />'.format( 
                _class = _class, 
                _style = _style, 
                _area=_area,
                content=context,
                _type=imageType
            )
            
            
        elif type(image) is str:
            # Image liegt als Datei vor
            if image[0] == "/":
                # absolute Angabe verwenden
                filepath = image
            else:
                # aus resources
                filepath = osp.join(self._variables["resources"], image )
            
            # gibt es die Datei dann einbinden
            if osp.exists( filepath ):
                
                element_html = '\n\t<img class="image {_class}" style="{_style} {_area}" src="file://{filepath}"></>'.format( 
                        _class = _class, 
                        _style = _style, 
                        _area=_area,
                        filepath=filepath
                )
                
        if render:    
            self._html(element_html)           
        return element_html
 
    def _getPandasFields(self, df=None, fields:list=[]):
        """Parameter für Pandas Felder zusammenstellen.
        
        Parameters
        ----------
        df : pandas.DataFrame, optional
            zu untersuchendes Dataframe. The default is None.
        fields : list, optional
            Liste von Feldern die verwendet werden sollen. The default is [].

        Returns
        -------
        result : dict|None
            Aufbau::
                
                {
                    "names" : [],
                    "columns" : {},
                    "field_format" : {},
                    "table_styles" : []
                }

        """
        result = {
            "names" : [],
            "columns" : {},
            "field_format" : {},
            "table_styles" : []
        }
        
        i = -1
        for f in fields:
            # nur wenn field angegeben wurde 
            if "field" in f and f["field"] in df.columns:
                i += 1
                result["names"].append( f["field"] )
                if "label" in f:
                    result["columns"][ f["field"] ] = f["label"]
                else:
                    result["columns"][ f["field"] ]  = f["field"]
                  
                if "format" in f:
                    result["field_format"][ result["columns"][ f["field"] ] ] = f["format"]
                  
                if "style" in f:
                    result["table_styles"].append( {
                         'selector': '.col{:d}'.format(i),
                         'props' : f["style"]
                    } )
            
        if i > 0:
            return result
        else:
            return None
        
    def pandas(self, df=None, area:dict={}, attrs:dict={}, fields:list=[], render=None ):
        """Ein Pandas Dataframe einfügen.
        
        Parameters
        ----------
        df: pandas.DataFrame
            
        area : Area {left,top,with,height}
            die Größe der Ausgabe       
        attrs : dict
            zu ändernde id class oder Style Angaben
        fields : list
            Liste von dict mit Angaben zu den auszugebenden Feldern::
                
            {"field": "", "label":"", "format":"", "style": [('text-align', 'left')] }
        render : bool
            sofort rendern oder nur zurückgeben ohne Angabe wird self.autoRender verwendet
        
        Returns
        -------
        html: str
            HTML des erzeugten Elements 
        """
        if not isinstance(df, pd.DataFrame) or df.empty:
            return ""
        
        # uuid festlegen
        if "id" in attrs:
            uuid = "{}_".format( attrs["id"] )
        else:
            self.pandas_table_id = self.pandas_table_id + 1
            uuid = "{}_".format( self.pandas_table_id ) 
            
        # Felder holen
        pf = self._getPandasFields( df, fields )
        
        if pf:
            html = self.html( df[ pf["names"] ].rename(columns=pf["columns"]).style
                .set_table_attributes('class="layout-fill-width"') 
                .format( pf["field_format"] ) 
                .set_table_styles( pf["table_styles"] )
                .hide_index()
                .set_uuid( uuid )
                .render().replace('nan','')
               
            , area=area
            , attrs=attrs
            , render=render
            )
        else:
            html = self.html( df.style
                .set_table_attributes('class="layout-fill-width"') 
                .hide_index()
                .set_uuid( uuid )
                .render().replace('nan','')
            , area=area
            , attrs=attrs, 
            render=render
            )

        return html
        
    def pandasPlot(self, df=None, area:dict={}, attrs:dict={}, render=None, **kwargs ):
        """Ein Pandas Dataframe plotten.
        
        Parameters
        ----------
        df: pandas.DataFrame
            
        area : Area {left,top,with,height}
            die Größe der Ausgabe       
        attrs : dict
            zu ändernde id class oder Style Angaben
        render : bool
            sofort rendern oder nur zurückgeben ohne Angabe wird self.autoRender verwendet
        **kwargs : 
            weitere Parameter für plot
            
        Returns
        -------
        self.image: str
            HTML des erzeugten Elements             
        """
        if not isinstance(df, pd.DataFrame) or df.empty:
            return ""
        
        # plt defaults setzen
        plt.rcParams.update( rcParams )
        
        if not "figsize" in kwargs:
            # mit festgelegter figsize=(16, 10) plotten
            kwargs["figsize"] = (16, 10)
       
        # The size in figsize=() is given in inches per (width, height) 6.4, 4.8
        df.plot( **kwargs)
        
        # layout opimieren
        plt.tight_layout(pad=0.4, w_pad=0.5, h_pad=1.0)
        
        image_data = io.BytesIO()
        plt.savefig( image_data, format='png' )

        plt.close('all')
        
        return self.image( image_data, area=area, attrs=attrs )
        
            
    def icon(self, name="", options="", area:dict={}, attrs:dict={}, render=None):
        """Ein Material Design Icon einfügen.
        
        Beispiel::
            
            icon( "mdi-check-outline", "x4")
            
        Parameters
        ----------
        name : str
            Name des Icons
        options: str
            Zusätzliche class Eigenschaften
        area : Area {left,top,with,height}
            die Größe der Ausgabe       
        attrs : dict
            zu ändernde id class oder Style Angaben
        render : bool
            sofort rendern oder nur zurückgeben ohne Angabe wird self.autoRender verwendet
            
        Returns
        -------     
        str : html
            Der html Code für das erzeugte Icon
        """
        text = '<i class="mdi {} {}"></i>'.format( name, options )
        return self._text( text, area, attrs, render )
  
    def resultIcon(self, acceptance=None, area:dict=None, render=None, iconOnly=False, size="x4", addClass=""):
        """Erzeugt ein acceptance Icon und verwendet die IBA Notation.
        
        Zusätzlich kann noch True statt 5 bzw. False für 1 verwendet werden.
        
        Wird area nicht angegeben so wird das Icon wird in der rechten unteren Ecke erzeugt  
        
        Parameters
        ----------
        acceptance : int
            5 - green - very Good (True)
            4 - green - Good
            3 - yellow - Sufficient
            2 - orange - Insufficient
            1 - red - Fail (False)
            alles andere - (n.a.) Not applicable
        area : Area {left,top,with,height}
            die Größe der Ausgabe       
        attrs : dict
            zu ändernde id class oder Style Angaben   
        render : bool
            sofort rendern oder nur zurückgeben ohne Angabe wird self.autoRender verwendet
        iconOnly : bool
            nur das icon zurückgeben
        size : str
            icon größe x1 bis x6 default: x4
            
        Returns
        -------   
        str : html
        
        """
        if not area:
            area = { "bottom":0, "right":0 }
        
        if type(acceptance) == bool:
            if acceptance:
                acceptance = 5
            else:
                acceptance = 1
        try:
            acceptance = int(acceptance)
        except:
            acceptance = None
            
        if acceptance==5:
            options="mdi-check-outline green-text"
        elif acceptance==4:
            options="mdi-check-outline lime-text"
        elif acceptance==3:
            options="mdi-alert-circle-outline amber-text"
        elif acceptance==2:
            options="mdi-alert-circle-outline orange-text"            
        elif acceptance==1:
            options="mdi-close-outline red-text"    
        else:
            options="mdi-block-helper"
          
        text = '<i class="mdi {} {} resultIcon {}"></i>'.format( options, size, addClass )
        if iconOnly:
            return text
        else:
            return self._text( text, area=area, render=render )
 