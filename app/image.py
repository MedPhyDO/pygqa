# -*- coding: utf-8 -*-
"""

"""

__author__ = "R. Bauer"
__copyright__ = "MedPhyDO - Machbarkeitsstudien des Instituts für Medizinische Strahlenphysik und Strahlenschutz am Klinikum Dortmund im Rahmen von Bachelor und Masterarbeiten an der TU-Dortmund / FH-Dortmund"
__credits__ = ["R.Bauer", "K.Loot"]
__license__ = "MIT"
__version__ = "0.2.1"
__status__ = "Prototype"

from pylinac.core.image import DicomImage as pyDicomImage
from pylinac.core.image import BaseImage

import copy

import matplotlib.pyplot as plt
import matplotlib

import numpy as np
from pylinac.settings import get_dicom_cmap

from app.config import infoFields
from isp.plot import plotClass

from pylinac.core.geometry import Point

import logging
logger = logging.getLogger( "ISP" )

class plotImage( pyDicomImage, plotClass ):
    """Erweiterung für plotClass (pyplot).
    
    Attributes
    ----------   
    _plotPosition: list
        Aktuelle PlotPosition. Default ist [0,0]
    fig:
        plt.subplots fig.  Default ist None
    ax:
        plt.subplots ax. Default ist None
    """
    
    def mm2dots_X( self, position ):
        """Wandelt eine X mm Angabe in die Pixel Positionen des image um.
        
        Parameters
        ----------
        position : int, float
            Position in mm.

        Returns
        -------
        int
            Umgewandelte Position immer größer gleich 0

        """
        x = int(round( self.dpmm * position + self.cax.x ))
        if x < 0:
            x = 0
        return x
    
    def mm2dots_Y( self, position ):
        """Wandelt eine Y mm Angabe in die Pixel Positionen des image um.
        
        Parameters
        ----------
        position : int, float
            Position in mm.

        Returns
        -------
        int
            Umgewandelte Position immer größer gleich 0

        """
        y = int(round( self.dpmm * position + self.cax.y ))
        if y < 0:
            y = 0
        return y

        
    def dots2mm_X( self, dots ):
        """Wandelt eine X dot Angabe im mm Position des Image um.
        
        Parameters
        ----------
        dots : int
            Position in mm.

        Returns
        -------
        float
            Umgewandelte Position

        """
        return ( dots - self.cax.x ) / self.dpmm 
    
    def dots2mm_Y( self, dots ):
        """Wandelt eine Y dot Angabe im mm Position des Image um.
        
        Parameters
        ----------
        dots : int
            Position in mm.

        Returns
        -------
        float
            Umgewandelte Position

        """
        return ( dots - self.cax.y ) / self.dpmm
    
    def mm2dots( self, point ):
        """Wandelt Point Angaben von mm nach dot.
        
        Parameters
        ----------
        point : Point
        
        """
        return Point( self.mm2dots_X(point.x), self.mm2dots_Y(point.y) )
    
    def dots2mm( self, point ):
        """Wandelt Point Angaben von dot nach mm
        
        Parameters
        ----------
        point : Point
        
        """
        return Point( self.dots2mm_X(point.x), self.dots2mm_Y(point.y) )  
    
    def axLimit(self, ax, limits:dict={}):
        """Achsen Limits ändern wird border angegeben zusätzlichen Rand hinzufügen.
        
        Parameters
        ----------
        ax: axis
            das axis element auf das die Änderungen angewandt werden sollen
        limits: dict
            Elemente: X1, X2, Y1, Y2, border
        """
        border = 0
        if "border" in limits:
            border = limits["border"]
            
        if "X1" in limits and "X2" in limits:
            px_min = self.mm2dots_X( limits["X1"] - border )
            px_max = self.mm2dots_X( limits["X2"] + border )
            # neues limit setzen
            ax.set_xlim( (px_min, px_max) ) 
            
        if "Y1" in limits and "Y2" in limits :            
            py_min = self.mm2dots_Y( limits["Y1"] - border)
            py_max = self.mm2dots_Y( limits["Y2"] + border)
            # neues limit setzen
            ax.set_ylim( (py_min, py_max) ) 
            
        
    def axTicks(self, ax, limits:dict={}):
        """Achsen Beschriftung und Limits ändern.
        
        wenn xStep kein dict ist 
        wird der Type der Achsenbeschriftung durch den Type der limits bestimmt 
        
        Parameters
        ----------
        ax: axis
            das axis element auf das die Änderungen angewandt werden sollen
        limits: dict
            Elemente: X1, X2, Y1, Y2, xStep, yStep, X, Y
            - X1, X2, Y1, Y2, 
            - xStep, yStep : dict - mit pos:label werden diese gesetzt
            - xStep, yStep : int,float - wird der Abstand aus breite/step gebildet
            - X, Y - ohne andere limits Angaben und nicht auto als Angabe wird die Achse entfernt  
         
        """
        # gibt es Angaben für x
        if "X1" in limits and "X2" in limits and "xStep" in limits:
            l_min = limits["X1"]
            l_max = limits["X2"]
            l_step = limits["xStep"]
            
            px_min = self.mm2dots_X( l_min )
            px_max = self.mm2dots_X( l_max )
            
            if type(l_step) is dict:
                # ticklabels bestimmen
                labels = l_step.values()
                # ticks bestimmen
                ticks = []
                for t in l_step.keys():
                    ticks.append( self.mm2dots_X( float(t) ) )
            else:
                is_type = np.result_type( l_min, l_max, l_step)
                # ticklabels bestimmen
                l_width = abs(l_min) + abs(l_max)
                step = (l_width / l_step)
                labels = np.arange(l_min, l_max + l_width / step, l_width / step, dtype=is_type ) 
                # ticks bestimmen
                t_width = abs(px_max - px_min)   
                ticks = np.arange(px_min, px_max + t_width / step , t_width / step )

            # ticks setzen
            ax.xaxis.set_ticks( ticks )
            # label setzen
            ax.xaxis.set_ticklabels( labels )

        elif not "X" in limits or limits["X"] != "auto":
            # x-Achse entfernen
            ax.get_xaxis().set_ticklabels([])
            ax.get_xaxis().set_ticks( [] )

        # gibt es Angaben für y
        if "Y1" in limits and "Y2" in limits and "yStep" in limits: 
            l_min = limits["Y1"]
            l_max = limits["Y2"]
            l_step = limits["yStep"]
            
            px_min = self.mm2dots_Y( l_min )
            px_max = self.mm2dots_Y( l_max )
            
            if type(l_step) is dict:
                # ticklabels bestimmen
                labels = l_step.values()
                # ticks bestimmen
                ticks = []
                for t in l_step.keys():
                    ticks.append( self.mm2dots_Y( float(t) ) )
            else:
                is_type = np.result_type( l_min, l_max, l_step)
                # ticklabels bestimmen
                l_width = abs(l_min) + abs(l_max)
                step = (l_width / l_step)
                labels = np.arange(l_min, l_max + l_width / step, l_width / step, dtype=is_type) 
                # ticks bestimmen
                t_width = abs(px_max - px_min) 
                ticks = np.arange(px_min, px_max + t_width / step , t_width / step )
            
            # ticks setzen
            ax.get_yaxis().set_ticks( ticks )
            # label setzen
            ax.get_yaxis().set_ticklabels( labels )

        elif not "Y" in limits or limits["Y"] != "auto":
            # y-Achse entfernen
            ax.get_yaxis().set_ticklabels([])
            ax.get_yaxis().set_ticks( [] )    

class DicomImage( plotImage ):
    """An image from a DICOM RTImage file.

    Attributes
    ----------
    infoFields: dict
        siehe: app.config.infoFields
        
    infos : dict
        eine Zusammenstellung der wichtigsten metadata 
        enthält auch den type für den Auswertung
        
    arrayOriginal : np.array
        Original array Informationen wenn eine normalisierung vorgenommen wurde 
        
    isRescaled : boolean
        Gibt an ob schon ein rescale durchgeführt wurde
    """
    
    def __init__(self, path: type[str|dict|tuple]=None, infoOnly: bool=False ):
        """ Klasse initialisieren
        wird path angegeben aus dem Pfad das DicomBild einlesen
        
        Parameters
        ----------
        path : str
            Pfad zum Dicom Bild
          : dict
            dict mit AriaDicom Daten oder { "info": , "dicom":dicom Daten }
          : tuple
            Pandas tuple 
        infoOnly : bool
            Nur infos holen oder auch schon RescaleSlope durchführen
                     
        """
        
        self.infos = {}
        
        # siehe: isp.config.infoFields
        self.infoFields = infoFields

        self.arrayOriginal = None
    
        self.isRescaled = False
                
        if not path: 
            # es wurde nichts übergeben
            initOK = False
                    
        elif isinstance(path, dict) and "dicom" in path:
            initOK = self.initMemoryDicom( path )
        else:
            initOK = True
            
        if not initOK:
            return
                    
        # rescale durchführen oder nur info erzeugen
        if not infoOnly:
            self.doRescaleSlope()       
        
    
    def initMemoryDicom(self, data:dict={}):
        """ Lädt Dicom daten die schon im Speicher sind
        
        Parameters
        ----------
        data : dict
            - dicom : pydicom.FileDataset <class 'pydicom.dataset.FileDataset'> 
            - dicom : pydicom.Dataset <class 'pydicom.dataset.Dataset'> 
                Dicomdaten Dataset oder FileDataset
            - info: dict
                Info der Dicomdaten

        Returns
        -------
        boolean
            true wenn ok 
        """
       
        if "info" in  data:
            self.infos = data["info"]
        else:
            self.infos = data

        # definition der Übergabe variablen
        dtype=None
        self._sid = None
        self._dpi = None
        
        # auf Dataset oder FileDataset <class 'pydicom.dataset.FileDataset'> abfragen
        if not data["dicom"].__class__.__name__ in [ "Dataset",  "FileDataset"]:
            return False
                       
        self.metadata = data["dicom"] # pydicom.FileDataset <class 'pydicom.dataset.FileDataset'>
       
        # dtype=uint16; SOPClassUID=RT Image Storage
        self._original_dtype = self.metadata.pixel_array.dtype
        if dtype is not None:
            self.array = self.metadata.pixel_array.astype(dtype)
        else:
            self.array = self.metadata.pixel_array
            
        # convert values to proper HU: real_values = slope * raw + intercept
        if self.metadata.SOPClassUID.name == 'CT Image Storage':
            self.array = int(self.metadata.RescaleSlope)*self.array + int(self.metadata.RescaleIntercept)
        
        return True
    
    def doRescaleSlope( self ):
        """ RescaleSlope anwenden wenn es ein RT Image Storage ist
        Wird nur durchgeführt wenn self.isRescaled false ist und setzt isRescaled
        
        """
        if not self.isRescaled and self.infos["SOPClassUID"] == 'RT Image Storage':
            #print("doRescaleSlope", self.base_path, self.metadata.RescaleSlope )
            self.array = self.array * self.metadata.RescaleSlope
            self.isRescaled = True
    
    def getFieldDots( self, field=None ):
        """ gibt die pixelangaben für die Feldgröße 
            berücksichtigt dabei die Kollimator Rotation
            
            FIXME: alle Angaben auf das ISO Zentrum beziehen (auch bei crop Angaben)
            
            Parameters
            ----------
            field : dict
        """
        if field:
            d = { 
                "X1" : self.mm2dots_X( field["X1"] ),
                "X2" : self.mm2dots_X( field["X2"] ),
                "Y1" : self.mm2dots_Y( field["Y1"] ),
                "Y2" : self.mm2dots_Y( field["Y2"] ),
                "X" : self.mm2dots_X( field["X2"] ) - self.mm2dots_X( field["X1"] ),
                "Y" : self.mm2dots_Y( field["Y2"] ) - self.mm2dots_Y( field["Y1"] ),
            }
        else:
            d = { 
                "X1" : self.mm2dots_X( self.infos["X1"] ),
                "X2" : self.mm2dots_X( self.infos["X2"] ),
                "Y1" : self.mm2dots_Y( self.infos["Y1"] ),
                "Y2" : self.mm2dots_Y( self.infos["Y2"] ),
                "X" : self.mm2dots_X( self.infos["X2"] ) - self.mm2dots_X( self.infos["X1"] ),
                "Y" : self.mm2dots_Y( self.infos["Y2"] ) - self.mm2dots_Y( self.infos["Y1"] ),
            }
            
        dots = copy.deepcopy( d )
        if self.infos["collimator"] == 90:
            dots["X1"] = d["Y1"]
            dots["X2"] = d["Y2"]
            dots["Y1"] = d["X1"]
            dots["Y2"] = d["X2"]   
            dots["X"] = d["Y"]  
            dots["Y"] = d["X"]  
        elif self.infos["collimator"] == 180:
            dots["X1"] = d["X2"]
            dots["X2"] = d["X1"]
            dots["Y1"] = d["Y2"]
            dots["Y2"] = d["Y1"]              
        elif self.infos["collimator"] == 270:
            dots["X1"] = d["Y1"]
            dots["X2"] = d["Y2"]
            dots["Y1"] = d["X1"]
            dots["Y2"] = d["X2"]         
            dots["X"] = d["Y"]  
            dots["Y"] = d["X"] 
            
        #print(d, dots)
        return dots
   
    def getFieldSize( self ):
        """Holt die echten Feldmaße aus self.infos 

        Returns
        -------
        d : dict
            die Feldmaße::
                
                - X1
                - X2
                - Y1
                - Y2
                - X
                - Y
        """
        d = { 
            "X1" : self.infos["X1"],
            "X2" : self.infos["X2"],
            "Y1" : self.infos["Y1"],
            "Y2" : self.infos["Y2"],
            "X" : self.infos["X2"] - self.infos["X1"],
            "Y" : self.infos["Y2"] - self.infos["Y1"],
        }
        return d
        
        
    def plotImage(self, original=True, plotTitle=True,
                  plotCax = False, plotField = False,
                  plotTicks = True,
                  invert=True, field=None, metadata={},
                  getPlot=True, cmap=None,
                  arg_function=None, arg_dict={}, **args 
                  ):
                
        """
            Bild mit Dicominformationen und Messpositionen anzeigen  
            Standarmäßig wird zum plotten das Original und nicht das Normalisierte verwendet
            
            Parameters
            ----------
            original : boolean, instance of BaseImage
                Original oder Normaliesiertes Image verwenden
            plotTitle : bool|str
                Titel über dem Bild ausgeben
            plotCax : boolean
                Zentrumskreuz einzeichnen
            plotField : boolean, dict 
                Feld einzeichnen, wenn als dict dann dieses Feld verwenden 
            plotTicks : boolean
                Achsenschriftung einzeichnen
            invert: boolean
                zum anzeigen invertieren
            field : None, dict, int float 
                wenn angegeben nur diesen Bildbereich anzeigen 
                Elemente: X1, X2, Y1, Y2, xStep, yStep, border
                # bei Angabe von xStep, yStep auch als Beschriftung setzen
                # bei Angabe von border autom. Beschriftung mit zusätzlichem rand
                # als int oder float auf feldgröße setzen und angabe als rand verwenden
            metadata: dict
                wenn angegeben imgSize verwenden default imgSize {"width": 90, "height": 90 }
            cmap: str 
                default: cm.gray
                vorhandene: cm.cmaps_listed.keys()
                ['magma', 'magma_r', 'inferno', 'inferno_r', 'plasma', 'plasma_r', 'viridis', 'viridis_r', 'cividis', 'cividis_r', 'twilight', 'twilight_r', 'twilight_shifted', 'twilight_shifted_r']
            getPlot: boolean
                True: die Funktion getPlot aufrufen und das image zurückgeben 
                False: 
            arg_function: None
                diese Funktion aufrufen mit dem parametern
                    self
                    ax 
                    plt
                    viewfield
                    metadata
            arg_dict: dict 
                zusätzliche Funktionsparameter für arg_function
                
            args:
                zusätzliche Angaben für initPlot -> plt.subplots 
            
            Returns
            -------
            wenn getPlot=True
                image
            sonst 
                self, fig, ax
        """
        
        def autoFieldStep( border ):
            # field auf die Feldgröße setzen
            field = self.getFieldSize()
            # rand merken
            field["border"] = border
            # auto. stepweite eintragen
            field["xStep"] = field["X"] / 4
            field["yStep"] = field["Y"] / 4 
            
            return field
        
        
        if isinstance( field, dict):
            if len(field) == 1 and "border" in field:
                # field auf die Feldgröße setzen
                field = autoFieldStep( field["border"] )   
             
            fieldTicks = field
        elif isinstance( field, (int, float) ):
            field = autoFieldStep( field )
            fieldTicks = field
           
        else:
            # komplett anzeigen
            fieldTicks = { "X1":-200, "X2": 200, "Y1": -200, "Y2":200, "xStep":100, "yStep":100 }
            
            
        if not "imgSize" in metadata:
            metadata["imgSize"] = {"width": 90, "height": 90 }
            
            
        # plot anlegen
        plot = plotClass( )
        fig, ax = plot.initPlot( metadata["imgSize"], getPlot=getPlot, **args )
         
        # wurde in original eine instance von BaseImage angegeben dann diese verwenden
        imageArray = None
        
        if isinstance( original, BaseImage ):
            imageArray = original.array.copy() 
        else:
            if original and isinstance( self.arrayOriginal, np.ndarray ):
                imageArray = self.arrayOriginal.copy()
            else:
                imageArray = self.array.copy()
     
        # colormap wenn nicht angegeben dicom verwenden
        if not cmap:
            cmap=get_dicom_cmap()
            
        # invertieren durch drehen der cmap 
        if invert:
            if isinstance( cmap, matplotlib.colors.Colormap ):               
                cmap = cmap.reversed()
            else:
                if cmap[-2:] == "_r":
                    cmap = cmap[:-2]
                else:
                    cmap += "_r" 
                    
        
        # das eigentliche anzeigen des Bildes
        ax.imshow( imageArray, cmap=cmap )
        
        # Achsen beschneiden
        self.axLimit( ax, fieldTicks )
        
        # Achsenbeschriftung setzen oder entfernen
        if plotTicks:
            self.axTicks( ax, fieldTicks )
        else:
            self.axTicks( ax )
                
        # Bild Titel
        title = "{Kennung} - Energie:{energy} G:{gantry:01.1f} K:{collimator:01.1f}"
        # als string dann diesen verwenden    
        if isinstance( plotTitle, str ):
            title = plotTitle
            plotTitle = True
            
        if plotTitle:
            # zuerst in sich um in Kennung befindliche Angaben bereitzustellen
            #title = title.format( **self.infos )
            
            try:
                if metadata["imgSize"]["width"] < 90:
                    plt.title( title.format( **self.infos ), size='smaller' )
                else:
                    plt.title( title.format( **self.infos ) )
            except Exception as e:
                print( "Exception - image.plotImage", title, self.infos, e )
                pass
            
        # plot CAX (image.center)
        if plotCax:
            ax.plot( self.center.x, self.center.y, 'b+', ms=8, markeredgewidth=1 ) 
   
        # plot Field
        if plotField:
            if isinstance( plotField, dict ):
                da = self.getFieldDots( plotField )
            else:
                da = self.getFieldDots( )
            
            ax.add_patch(matplotlib.patches.Rectangle((da["X1"], da["Y1"]), da["X"], da["Y"], color="blue", fill=False ))
            #ax.Rectangle( [self.infos["X1"], self.infos["Y1"] ], self.infos["X2"], self.infos["Y2"]  )
        
        # wurde eine Funktion angeben dann aufrufen
        if arg_function:
            arg_dict = dict( arg_dict )
            arg_dict["self"] = self
            arg_dict["plt"] = plt
            arg_dict["ax"] = ax
            arg_dict["viewfield"] = field
            arg_dict["metadata"] = metadata
            arg_function( **arg_dict )
        
        # layout optimieren
        plt.tight_layout(pad=0.4, w_pad=0.5, h_pad=1.0)
         
        if getPlot==True:
            # data der Grafik zurückgeben
            data = self.getPlot()
            plt.close("all")
            return data
        else:
            return self, fig, ax
            
    def getRoi( self, field:dict=None ):
        """ holt region of interest des angegebenen Bereichs aus image.array
        
        """
        da = self.getFieldDots( field )
        return self.array[ da["Y1"]:da["Y2"], da["X1"]:da["X2"] ]
        
    def getFieldRoi( self ):
        """ holt region of interest der Feldgröße aus image.array
        
        """
        da = self.getFieldDots( )
        return self.array[ da["Y1"]:da["Y2"], da["X1"]:da["X2"] ]     
    
    def getLine( self, field=None ):
        """ holt eine pixel Reihe 
        """
        line = None
        if "x" in field:
            line = self.array[:, self.mm2dots_X(field["x"]) ]
        elif "y" in field:
            line = self.array[ self.mm2dots_Y(field["y"]) ]
        return line
        
    def cropField( self, field:dict=None ):
        """ Das image auf die angegebene Größe beschneiden
            Dabei wird image.cax auf das neue Zentrum gesetzt
            { "X1":-200, "X2": 200, "Y1": -200, "Y2":200 }
        """
        da = self.getFieldDots( field )
        self.array = self.array[ 
            da["Y1"]:da["Y2"], da["X1"]:da["X2"]
       ]
        #print( self.image.array.shape,  self.image.array )
        self.center.x = self.array.shape[0] / 2
        self.center.y = self.array.shape[1] / 2
        
        return self
