# -*- coding: utf-8 -*-

"""

MT_VMAT_0.1
MT_VMAT_0.2 PicketFence statisch
MT_VMAT_1.1 PicketFence mit rot
MT_VMAT_1.2:error PicketFence mit rot und absichtlichen Fehler
MT_VMAT_2 Variationen von DoseRate und Gantry Speed
MT_VMAT_3 MLC Speed

"""

__author__ = "R. Bauer"
__copyright__ = "MedPhyDO - Machbarkeitsstudien des Instituts für Medizinische Strahlenphysik und Strahlenschutz am Klinikum Dortmund im Rahmen von Bachelor und Masterarbeiten an der TU-Dortmund / FH-Dortmund"
__credits__ = ["R.Bauer", "K.Loot"]
__license__ = "MIT"
__version__ = "0.1.0"
__status__ = "Prototype"

from pylinac.vmat import VMATBase

import numpy as np
import pandas as pd

# app
from app.check import ispCheckClass
from app.base import ispBase
from app.image import DicomImage


import matplotlib.pyplot as plt


# logging
import logging
logger = logging.getLogger( "MQTT" )

class FSImage( DicomImage ):
    '''Erweitert PFDicomImage um die eigene DicomImage Klasse
    
    FIXME: ist dies noch notwendig?
    
    Attributes
    ----------
    base_path : str
        
    '''
    
    base_path = ""
    
    def __init__(self, pathOrData=None, **kwargs ):
        """ Erweitert PFDicomImage um die eigene DicomImage Klasse
        
        """
        #print("PFImage.__init__", path, kwargs)
        
        # das pylinacpicketfence Image
        #FlatSym.__init__( self, path, **kwargs )
        
        # die eigene Erweiterung
        DicomImage.__init__( self, pathOrData )
        
class qa_vmat( VMATBase, ispCheckClass ):
    '''
    
    Attributes
    ----------
    debug : bool
    
    analysed : bool
    
    metadata : dict
           
    '''
    

    
    def __init__( self, df:None, vmat_type:str="DRGS", tolerance:[float, int]=1, metadata:dict={} ):
        """
    
        Parameters
        ----------
        df : None
            Pandas dataframe mit den Bildern.
        vmat_type : TYPE, optional
            DRGS oder DRMLC. The default is "DRGS".
        tolerance : [float, int], optional
            DESCRIPTION. The default is 1.
        metadata : dict, optional
            - result_header:str
            The default is {}.

        Returns
        -------
        None.

        """
        self.debug=False
    
        self.analysed = False
        
        self.metadata = metadata

        # parameter je nach vmat_type verändern
        if vmat_type=="DRGS":
            self._result_header = 'Dose Rate & Gantry Speed'
            self.SEGMENT_X_POSITIONS_MM = (-60, -40, -20, 0, 20, 40, 60)
        elif vmat_type=="DRMLC":
            self._result_header = 'Dose Rate & MLC Speed'
            self.SEGMENT_X_POSITIONS_MM = (-45, -15, 15, 45) 
        else:
            return 

        images = df.to_dict('records') 

        # DicomBild laden und prüfen
        self.image1, self.image2 = self._check_img_inversion(FSImage( images[0] ), FSImage( images[1] ))
        self._identify_images(self.image1, self.image2)
        self.segments = []
        
        # analyse mit default toleranz durchführen durchführen
        # Die toleranz prüfung wird in der Tabelle vorgenommen
        self._tolerance = 0
        self.analyze(  )
    
        self.analysed = True
        
        # Ergebnisse ablegen
        self.results = self.getResults()


    def getResults( self ):
        """Holt die Ergebnisse der Auswertung.
        und füllt die segmente mit jeweiligen Daten aus metadata

        Returns
        -------
        dict
            - open
            - vmat
            - header
            - SID
            - deviation
            - maximum_deviation
            - segments : list of dict
                - segment
                - center
                - r_corr
                - r_dev
                - draw_height
                - draw_width
                - draw_corner
                - segment_obj

        """
        if not self.analysed:
            return {}
        
        dmlc_prof, open_prof = self._median_profiles((self.dmlc_image, self.open_image))
        
        segments = []
        lfd = 0
        
        for segment in self.segments:
            #print( segment )
            lfd += 1
            # r_corr = Return the ratio of the mean pixel values of DMLC/OPEN images.
            # r_dev = The reading deviation (R_dev) from the average readings of all the segments
            # passed = self.r_dev < self._tolerance * 100
            _segment = {
                "segment": lfd,
                "center" : self.SEGMENT_X_POSITIONS_MM[lfd-1], 
                "r_corr" : segment.r_corr,
                "r_dev" : segment.r_dev,
                "draw_height": segment.height,
                "draw_width": segment.width,
                "draw_corner": segment.bl_corner,
                "segment_obj": segment
            #    "passed" : segment.passed
            }
            _segment.update( self.metadata["segments"][ str(lfd) ] )

            segments.append( _segment )
        
        
        data = {
            "open" : open_prof,
            "vmat": dmlc_prof, 
            "header" : self._result_header,
            "SID" : self.open_image.sid,
            "deviation": self.avg_abs_r_deviation,
            "maximum_deviation": self.max_r_deviation,
            "segments": segments
        }

        return data
        

    def plotChart( self, chartSize={} ):
        """Median profiles plotten
        
        """
        # plotbereiche festlegen
        fig, ax = self.initPlot( chartSize )
      
        # Daten holen (nur zentrums profil)
        dmlc_prof, open_prof = self._median_profiles((self.dmlc_image.getFieldRoi(  ), self.open_image.getFieldRoi(  )))
                 
        # Kurven plotten
        ax.plot(dmlc_prof.values, label='DMLC')
        #ax.plot(roi, label='ROI')
        ax.plot(open_prof.values, label='Open')
        
        # Achsenbeschriftung in mm
        # x-Achse
        xlim = ax.get_xlim()  
        width = xlim[0] + xlim[1] 
        x = np.arange(0, len( dmlc_prof.values ), width / 4 )
        ax.get_xaxis().set_ticklabels([ -200, -100, 0, 100, 200])
        ax.get_xaxis().set_ticks( x )

        ax.legend(loc=8, fontsize='large')
        ax.grid()
        
        # layout opimieren
        plt.tight_layout(pad=0.4, w_pad=0.5, h_pad=1.0)
        
        # data der Grafik zurückgeben
        return self.getPlot()
    
    def draw_segments(self, axis: plt.Axes, df:None):
        """Draw the segments onto a plot.

        Parameters
        ----------
        axis : matplotlib.axes.Axes
            The plot to draw the objects on.
        """
        for segment in df.itertuples():
            if segment.r_dev_acceptance == 5:
               color = 'green'
            elif segment.r_dev_acceptance == 3:
               color = '#ffc107'
            else:
                color = 'red'
                
            segment.segment_obj.plot2axes(axis, edgecolor=color)

            
class checkVMAT( ispBase ):
    
     
    def doMT_VMAT( self, fileData ):
        """Variationen von DoseRate und Gantry Speed
            
        Parameters
        ----------
        fileData : pandas.DataFrame
        
            
        Returns
        -------
        pdfFilename : str
            Name der erzeugten Pdfdatei
        result : list
            list mit dicts der Testergebnisse 
            
        See Also
        --------
        isp.results : Aufbau von result
        """
        
        result=[]

        # wird für progress verwendet
        filesMax=len( fileData )
        self.fileCount = 0
        
        # metadata ergänzen und lokal als md bereitstellen
        md = self.metadata
        md.update( {
            "_imgSize" : {"width" : 90, "height" : 85},
            "_imgField": {"border": 20 },
            "_chart": { "width" : 180, "height" : 60},
        } )
 

        def groupBySeries( df_group ):
            """Datumsweise Auswertung und PDF Ausgabe 
            
            """
            # das Datum vom ersten Datensatz verwenden
            checkDate = df_group['AcquisitionDateTime'].iloc[0].strftime("%d.%m.%Y")
            self.pdf.setContentName( checkDate )
            
            #               
            # Anleitung
            #
            self.pdf.textFile( md["anleitung"], attrs={"class":"layout-fill-width", "margin-bottom": "5mm"} )  
            
            # auf genau 2 felder prüfen (open, DMLC)
            if not self.checkFields( md, fields=df_group, fieldLen=2 ):
                result.append( 
                    self.pdf_error_result( 
                        md, group_len=len( result ),
                        date=checkDate,
                        msg="Die Feldanzahl ist nicht 2"
                    )
                )
                return
            
           
            # Analyse durchführen
            drgs = qa_vmat( df_group, str( md["vmat_type"]), metadata=md )
              
            if drgs.analysed == False:
                logger.error( self.getMetaErrorString( md ) + ": Analyse nicht möglich" )
                result.append( 
                    self.pdf_error_result( 
                        md, date=checkDate, group_len=len( result ),
                        msg="Analyse nicht möglich"
                    )
                )
                return
            
            #
            # Auswertung holen und Dataframe erstellen
            #    
            df = pd.DataFrame( drgs.results["segments"] )
           
            #
            # Abweichung ausrechnen und Passed setzen
            #
            check = [
                { "field": 'r_dev', 'tolerance':'default' }   
            ]
            acceptance = self.check_acceptance( df, md, check )
            
            #
            # Ergebnis in result merken
            #
            result.append( self.createResult( df, md, check, 
                checkDate, 
                len( result ), # bisherige Ergebnisse in result
                acceptance
            ) )
            
            
            #
            # das offene Feld
            #
            img_cls, fig, ax = drgs.open_image.plotImage( original=False
                    , field = md["_imgField"]                             
                    , metadata = md
                    , plotTitle = "{Kennung}"
                    , invert=False, plotCax=False, plotField=True, getPlot=False )
            # segmente einzeichnen
            drgs.draw_segments( ax, df )
            # Bild anzeigen
            self.pdf.image( img_cls.getPlot(), md["_imgSize"] )
            
            #
            # das vmat Feld
            #
            img_cls, fig, ax = drgs.dmlc_image.plotImage( original=False
                    , field = md["_imgField"]                        
                    , metadata = md
                    , plotTitle="{Kennung}"
                    , invert=False, plotCax=False, plotField=True, getPlot=False )
            # segmente einzeichnen
            drgs.draw_segments(ax, df)
            
            # Bild anzeigen
            self.pdf.image(img_cls.getPlot(), md["_imgSize"] )
            
            #
            # das chart
            #
            self.pdf.image( drgs.plotChart( md["_chart"] ), md["_chart"], attrs={"margin-top": "5mm"} )
            
            #
            # Tabelle anzeigen
            #
            self.pdf.pandas( df, 
                attrs={"class":"layout-fill-width", "margin-top": "5mm"},
                fields=md["table_fields"]
            )
            
            #
            # Auswertungs text anzeigen
            #
            drgs.results["f_warning"] = md.tolerance[ md["energy"] ].default.warning.get("f","")
            drgs.results["f_error"] = md.tolerance[ md["energy"] ].default.error.get("f","")
            # <h3>{header} VMAT results:</h3>
            text = """<br>
                Source-to-Image Distance: <b style="position:absolute;left:45mm;">{SID:2.0f} mm</b>
                Absolute mean deviation: <b style="position:absolute;left:45mm;">{deviation:2.2f} %</b>
                Maximum deviation: <b style="position:absolute;left:45mm;">{maximum_deviation:2.2f} %</b><br>
                Warnung bei: <b style="position:absolute;left:45mm;">{f_warning}</b><br>
                Fehler bei: <b style="position:absolute;left:45mm;">{f_error}</b>
                """.format( **drgs.results ).replace("{value}", "M<sub>dev</sub>")
            self.pdf.text( text )

            # Gesamt check - das schlechteste aus der tabelle
            self.pdf.resultIcon( acceptance )
            
            # progress pro file stimmt nicht immer genau (baseimage)
            # 40% für die dicom daten 40% für die Auswertung 20 % für das pdf
            self.fileCount += 2
            if hasattr( logger, "progress"):
                logger.progress( md["testId"],  40 + ( 40 / filesMax * self.fileCount ) )
            
        #
        # Gruppiert nach SeriesNumber abarbeiten
        # 
        fileData.groupby( [ 'day', 'SeriesNumber' ] ).apply( groupBySeries )      
        # abschließen pdfdaten und result zurückgeben
        return self.pdf.finish(), result  

    
    def doMT_VMAT_2( self, fileData ):
        """DRGS - Variationen von DoseRate und Gantry Speed
        """
        # metadata vorbereiten

        # Beschriftung für die Bild Achsen
        step = { "-100":"-100", "-50":"-50", "0":"0",  "50":"50", "100":"100"  }
        self.metadata.update( {
            "vmat_type": "DRGS",
            "segments": {
                "1" : { "DoseRate": 111, "GantrySpeed": 6},
                "2" : { "DoseRate": 222, "GantrySpeed": 6},
                "3" : { "DoseRate": 332, "GantrySpeed": 6},
                "4" : { "DoseRate": 443, "GantrySpeed": 6},
                "5" : { "DoseRate": 554, "GantrySpeed": 6},
                "6" : { "DoseRate": 600, "GantrySpeed": 5},
                "7" : { "DoseRate": 600, "GantrySpeed": 4.3}
            },
            "_imgField": { "X1":-100, "X2":100, "Y1": -110, "Y2": 110, "xStep":step , "yStep":step },
            "table_fields" : [
                {'field': 'segment', 'label':'Segment', 'format':'{0}' },
                {'field': 'DoseRate', 'label':'DoseRate', 'format':'{0:d}'},
                {'field': 'GantrySpeed', 'label':'GantrySpeed [°/s]', 'format':'{0:1.1f}'},
                {'field': 'center', 'label':'Segment Zentrum', 'format':'{0:1.1f}' },
                {'field': 'r_corr', 'label':'M<sub>corr</sub>', 'format':'{0:2.3f}' },
                {'field': 'r_dev', 'label':'M<sub>dev</sub> [%]', 'format':'{0:2.3f}' },
                {'field': 'r_dev_passed', 'label':'Passed' }
            ]
        } )
        return self.doMT_VMAT( fileData )
        
    def doMT_VMAT_3( self, fileData ):
        """DRMLC - MLC Speed
        """
        # metadata vorbereiten
        # Beschriftung für die Bild Achsen
        step = { "-100":"-100", "-50":"-50", "0":"0",  "50":"50", "100":"100"  }
        self.metadata.update( {
            "vmat_type": "DRMLC",
            "segments": {
                "1" : { "LeafSpeed":1.7, "DoseRate": 514, "GantrySpeed": 6},
                "2" : { "LeafSpeed":2.0, "DoseRate": 600, "GantrySpeed": 4},
                "3" : { "LeafSpeed":1.0, "DoseRate": 300, "GantrySpeed": 6},
                "4" : { "LeafSpeed":0.5, "DoseRate": 150, "GantrySpeed": 6}
                
            },
            "_imgField": { "X1":-100, "X2":100, "Y1": -110, "Y2": 110, "xStep":step , "yStep":step },
            "table_fields" : [
                {'field': 'segment', 'label':'Segment', 'format':'{0}' },
                {'field': 'LeafSpeed', 'label':'LeafSpeed [cm/s]', 'format':'{0:1.1f}'},
                {'field': 'DoseRate', 'label':'DoseRate', 'format':'{0:d}'},
                {'field': 'GantrySpeed', 'label':'GantrySpeed [°/s]', 'format':'{0:1.1f}'},
                {'field': 'center', 'label':'Segment Zentrum', 'format':'{0:1.1f}' },
                {'field': 'r_corr', 'label':'M<sub>corr</sub>', 'format':'{0:2.3f}' },
                {'field': 'r_dev', 'label':'M<sub>dev</sub> [%]', 'format':'{0:2.3f}' },
                {'field': 'r_dev_passed', 'label':'Passed' }
            ]   
        } )
        return self.doMT_VMAT( fileData )
        
