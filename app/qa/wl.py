# -*- coding: utf-8 -*-

__author__ = "R. Bauer"
__copyright__ = "MedPhyDO - Machbarkeitsstudien des Instituts für Medizinische Strahlenphysik und Strahlenschutz am Klinikum Dortmund im Rahmen von Bachelor und Masterarbeiten an der TU-Dortmund / FH-Dortmund"
__credits__ = ["R.Bauer", "K.Loot"]
__license__ = "MIT"
__version__ = "0.1.0"
__status__ = "Prototype"

from sortedcontainers import SortedDict
from itertools import zip_longest
import re

import numpy as np
from math import pi

import pandas as pd

# WL suche mit skimage
from skimage import filters
from skimage import measure

# mathplotlib
import matplotlib.pyplot as plt
import matplotlib.lines as lines
import matplotlib.ticker as ticker


#from pylinac import WinstonLutz
#from pylinac.winston_lutz import WLImage
# pylinac
from pylinac.core.geometry import Point
from pylinac.core.image import ArrayImage

# app
from app.check import ispCheckClass
from app.base import ispBase

from app.qa.field import qa_field

# logging
import logging
logger = logging.getLogger( "MQTT" )

class qa_wl( ispCheckClass ):
    """
    
    Attributes
    ----------
    
    debug : bool
        Default ist False
        
    centers : dict
        - G : SortedDict
        - C : SortedDict
        - T : SortedDict
        - all : SortedDict
    mergeArray: dict
        - G : List
        - C : List
        - T : List
        - all : List  
    data : List
        Default ist []
        
    roi: dict
    
    fields: SortedDict
        Default ist None
        
    colFields: SortedDict
        Default ist SortedDict()
        
    virtualCenter: point
        Default ist None
    
    virtualCenterDots: point
        Default ist None
    

    """
    
    def __init__( self, data=None, roi=None, metadata:dict={} ):
        self.debug = False
        
        self.centers = {
            "G":SortedDict(),
            "C":SortedDict(),
            "T":SortedDict(),
            "all":SortedDict()
        }
        
        self.mergeArray = {
            "G":[],
            "C":[],
            "T":[],
            "all":[],
        }
                 
        if roi:
            self.roi = roi
        else:
            self.roi={ "X1":-10, "X2": 10, "Y1": -10, "Y2": 10 }
        
        self.data = []
        self.fields = None
        self.colFields = SortedDict()
        if data:
            self.data = data
            self.fields = SortedDict()
            
            # fields und zusätzlich colFields bestimmen
            # bei doppelten Winkeln nur den neusten verwenden
            for f in self.data.values(): 
                key = "%3i:%3i:%3i:%s" % ( f["gantry"] , f["collimator"], f["table"], f["GantryRtnExt"] )
                self.fields[ key ] = f
                if f["gantry"] == 0 and f["table"] == 0:
                    self.colFields[key] = f
                    
        self.virtualCenter = None
        self.virtualCenterDots = None
        
    def _getThresholdMask(self, img, proz ):
        """ Eine Bildmaske erstellen
        
        img : image.array
        proz : [ min, max]
        """
      
        min_value, max_value = np.percentile(img, proz)
        threshold_value = (max_value - min_value)/2 + min_value
        array = np.where(img >= threshold_value, 1, 0)
        threshold_img = ArrayImage(array)
        return threshold_img           
       
    def findColliCenter( self ):
        """Das Drehzentrum der IsoCalPlate bestimmen
        Nur bei Feldern mit Gantry und Table 0°
        Die Endwinkel 175 und 185 werden dabei zu einem Punkt zusammengefasst 
        
        
        """
        # ohne colField aufgerufen wird Point(0,0,0) zurückgegeben
        self.virtualCenter = Point( 0, 0)
        self.virtualCenterDots = Point( 0, 0)
         
        if len( self.colFields ) == 0:
            return self.virtualCenter
        
        endPoints = []
        points = []
        pointsDot = []
        endPointsDot = []
        sumArray = []
        
        pointsDotPos = {}
        pointsPos = {}
                
        # nur die colFields verwenden 
        for key, f in self.colFields.items(): 
            # isoCal Kugelpositionen bestimmen
            wlField = qa_field( f )
            imageArray = wlField.image.cropField( self.roi ) 
            isoCal, isoCalDot = self._findIsoCalCenter( wlField, True )
            
            # summenfeld erstellen um dies evt. zu verwenden
            # FIXME: fehler bei unterschiedlichen imgae sizes : warum gibt es die überhaupt?
            if len( sumArray ) == 0:
               sumArray = imageArray
            else:
               try:
                   sumArray = np.add( sumArray, imageArray )
               except:
                   logger.error("qa_wl.findColliCenter np.add shape size ungleich")
                   pass
                   
               
            if  f["collimator"] == 175 or f["collimator"] == 185:
                endPointsDot.append( (isoCalDot.x, isoCalDot.y) )
                endPoints.append( (isoCal.x, isoCal.y) )
            else: 
                pointsDot.append( (isoCalDot.x, isoCalDot.y) )
                pointsDotPos[ f["collimator"] ] = isoCalDot
                points.append( (isoCal.x, isoCal.y) )
                pointsPos[ f["collimator"] ] = isoCal
        
        # wurde ein summenfeld erstellt 
        if len( sumArray ) > 0:
            isoCalDots = self._findArrayIsoCalCenter( sumArray, True )  
            isoCal = wlField.image.dots2mm(isoCalDots)
        
        # kollimator 175 und 185 merken um sie zu einem Punkt zusammenzufassen
        
        # virtuellen punkte der endPoints 175 und 185 berechnen und als 180° verwenden
        # zuerst die dots
        earr = np.asarray(endPointsDot)
        eMean = earr.mean(axis=0)
        pointsDot.append( ( eMean[0], eMean[1] ) )
        # die dots als 180° ablegen
        pointsDotPos[ 180.0 ] = Point( eMean[0], eMean[1] )
        # dann die koordinaten
        earr = np.asarray(endPoints)
        eMean = earr.mean(axis=0)
        points.append( ( eMean[0], eMean[1] ) )
        pointsPos[ 180.0 ] = Point( eMean[0], eMean[1] )
        # np array verwenden
        arr = np.asarray(points)
        
        # zentrum der punkte
        arrDots = np.asarray(pointsDot)
        vCenterDots = arrDots.mean(axis=0)
        self.virtualCenterDots = Point( vCenterDots[0], vCenterDots[1] )
        # dann die koordinaten
        vCenter = arr.mean(axis=0)
        self.virtualCenter = Point( vCenter[0], vCenter[1] )
        
        #
        # debug
        #
        if self.debug:
            if isoCalDots:
                print("findColliCenter summfield", isoCalDots, isoCal)
                
            print("pointsDotPos", pointsDotPos)
            
            cmap=plt.cm.gray
            ax = plt.subplot(111)
            ax.imshow(sumArray, cmap=cmap)
            ax.axis('off')
            #ax.set_title(title)
            ax.plot( isoCalDots.x, isoCalDots.y, 'r+', ms=80, markeredgewidth=1 ) 
            ax.plot( self.virtualCenterDots.x, self.virtualCenterDots.y, 'b+', ms=80, markeredgewidth=1 ) 
            
            for p in pointsDot:
                ax.plot( p[0], p[1], 'g+', ms=20, markeredgewidth=1 ) 
                
            ax.plot( len(sumArray)/2, len(sumArray)/2, 'y+', ms=100, markeredgewidth=1 ) 
            
            # kontroll linien
          
            lineA = lines.Line2D(
                    [ pointsDotPos[ 0 ].x, pointsDotPos[ 180 ].x ],
                    [ pointsDotPos[ 0 ].y, pointsDotPos[ 180 ].y ],
                    lw=1, color='green', axes=ax)
            ax.add_line(lineA)
            lineB = lines.Line2D(
                    [ pointsDotPos[ 90 ].x, pointsDotPos[ 270 ].x ],
                    [ pointsDotPos[ 90 ].y, pointsDotPos[ 270 ].y ],
                    lw=1, color='green', axes=ax)
            ax.add_line(lineB)
            
            plt.show(ax)
        
            print("isoCal=rot,  virtualCenter=blau,  nulllinie=gelb")
            print("WL_findColliCenter", self.virtualCenter, pointsPos )
            
        
        return self.virtualCenter
 
    def _findArrayIsoCalCenter( self, imageArray, debug=False):
        """ Zentrum des ISO Cal (Einschub) Phantom im array bestimmen 
        
        Parameters
        ----------
        imageArray : array
            array der Bilddaten
        debug : boolean
            debug Bilder augeben
            
        Returns
        -------
        Point
            gefundenes Zentrum in pixel
        """
        # imageArray invertieren
        img_inv = -imageArray + imageArray.max() + imageArray.min()
                
        # eine Bildmaske des großen kreises erstellen
        labeled_foreground = (img_inv > filters.threshold_otsu( img_inv ) ).astype(int)
        # eine Auswertung der Bildmaske vornehmen
        properties = measure.regionprops( labeled_foreground )
        # es könnten mehrere objekte vorhanden sein
        # in unseren Bildern ist aber nur eins deshalb das erste verwenden
        
        # das gefundene Zentrum des ISO Cal Phantomstiftes in dots
        isoCalDot = Point( properties[0].centroid[1], properties[0].centroid[0] )
        
        if self.debug:
            # plot images zum debuggen
            plots = {
                    'Original': imageArray,  
                    'Labels': labeled_foreground 
                }
            fig, ax = plt.subplots(1, len(plots))
            for n, (title, img) in enumerate(plots.items()):
                cmap = plt.cm.gnuplot if n == len(plots) - 1 else plt.cm.gray
                ax[n].imshow(img, cmap=cmap)
                ax[n].axis('off')
                ax[n].set_title(title)
                ax[n].plot( isoCalDot.x, isoCalDot.y, 'r+', ms=80, markeredgewidth=1 ) 
                ax[n].plot( len(img)/2, len(img)/2, 'y+', ms=100, markeredgewidth=1 ) 
            plt.show(fig)
            #print("isoCalCenter", isoCalDot )
    
        return isoCalDot
        
    def _findIsoCalCenter(self, field, debug=False):
        """ Zentrum des ISO Cal (Einschub) Phantom bestimmen 
        ruft findArrayIsoCalCenter auf
            
        Parameters
        ----------
        field : qa_field
            qa_field mit Bilddaten
        debug : boolean
            debug Bilder augeben
            
        Returns
        -------
        Point
            gefundenes Zentrum in mm
        Point
            gefundenes Zentrum in pixel
        """

        # das image auf den wichtigen Bereich beschneiden
        imageArray = field.image.cropField( self.roi ) 
        
        # das gefundene Zentrum des ISO Cal Phantomstiftes in dots
        isoCalDot = self._findArrayIsoCalCenter( imageArray, debug )
        # das gefundene Zentrum des ISO Cal Phantomstiftes in mm
        isoCal = field.image.dots2mm( isoCalDot )
        if self.debug:
            print("findIsoCalCenter", field.checkField["collimator"], isoCalDot, isoCal )
        
        return isoCal, isoCalDot
    
    def _mergeArray(self, art="all", imageArray=[] ):
        """ image array der jeweiligen Achse (G,C,T) addieren
        FIXME: was ist bei unterschiedlichen array größen
        """
        if len( self.mergeArray[art] ) == 0:
            self.mergeArray[art] = imageArray
        else:
            try:
                self.mergeArray[art] = np.add( self.mergeArray[art], imageArray )
            except:
                logger.error("qa_wl.findColliCenter np.add shape size ungleich")
                pass
            
        pass
        
    def findCenterBall(self, key):
        """ Zentrum der Kugel im Isozentrum bestimmen
        Die gefundene Position wird in self.fields eingefügt
        Zusätzlich wird die Position im centers abgelegt
        
        """
        
        if not key in self.fields:
            return None
        
       
        info = self.fields[ key ] 
        
        
        field = qa_field( info )
        # das image auf den wichtigen Bereich beschneiden
        imageArray = field.image.cropField( self.roi ) 
        
        # imageArray invertieren
        img_inv = -imageArray + imageArray.max() + imageArray.min()
        
        # centerBall
        #
        labeled_foreground = self._getThresholdMask( img_inv, [99, 99.9] )
        properties = measure.regionprops( labeled_foreground )
        # das gefundene Zentrum der Kugel in dots
        # es könnten mehrere objekte vorhanden sein
        # in unseren Bildern ist aber nur eins deshalb das erste verwenden
        centerBallDots = Point( properties[0].centroid[1], properties[0].centroid[0] )
        
        centerBallPositon = field.image.dots2mm( centerBallDots )
        
        # FIXME: ist center abziehen OK?
        # da Point kein + kann x und y seperat 
        self.fields[ key ]["centerBall"] = Point(centerBallPositon.x - self.virtualCenter.x, centerBallPositon.y - self.virtualCenter.y )
       
        # gefundene Position im centers ablegen
        centerBall = self.fields[ key ]["centerBall"]
        self.centers["all"][key] = centerBall
        
        #print( info["gantry"], info["collimator"], info["table"] )
        g = float(info["gantry"])
        c = float(info["collimator"])
        t = float(info["table"])
        if g == 0 and c == 0 and t == 0:
            self.centers["G"][0.0] = centerBall
            self._mergeArray("G", imageArray )
            self.centers["C"][0.0] = centerBall
            self._mergeArray("C", imageArray )
            self.centers["T"][0.0] = centerBall
            self._mergeArray("T", imageArray )
        elif c == 0.0 and t == 0:
            if g > 180 or info["GantryRtnExt"]=="EN":
                self.centers["G"][ g - 360 ] = centerBall
            else:
                self.centers["G"][ g ] = centerBall
            self._mergeArray("G", imageArray )

        elif g == 0 and t == 0:
            if c > 180:       
                self.centers["C"][ c - 360 ] = centerBall
            else:
                self.centers["C"][ c ] = centerBall
            self._mergeArray("C", imageArray )

        elif g == 0 and c == 0:
            if t > 180:
                self.centers["T"][ t - 360 ] = centerBall
            else:
                self.centers["T"][ t ] = centerBall
            self._mergeArray("T", imageArray )
            
            
        if self.debug:
            print("findCenterBall", self.virtualCenter, centerBallPositon, centerBall)
            # plot images zum debuggen
            plots = {
                    'Original': imageArray,  
                    'Labels': labeled_foreground 
                }
            fig, ax = plt.subplots(1, len(plots))
            for n, (title, img) in enumerate(plots.items()):
                cmap = plt.cm.gnuplot if n == len(plots) - 1 else plt.cm.gray
                ax[n].imshow(img, cmap=cmap)
                ax[n].axis('off')
                ax[n].set_title(title)
                ax[n].plot( centerBallDots.x, centerBallDots.y, 'r+', ms=80, markeredgewidth=1 ) 
                ax[n].plot( len(img)/2, len(img)/2, 'y+', ms=100, markeredgewidth=1 ) 
            plt.show(fig)
            
            pass
       
      
        return self.fields[ key ]["centerBall"]
    
    def _axisChart(self, ax=None, axisId="", title="", rmsColor="g" ):
        """
        """
        if not axisId in self.centers:
            return None
        
        def update_ticks(x, pos=None):
            if x == 0:
                return 0
            elif x < 0:
                return x + 360
            else:
                return x
            
        angles = [ ]

        xCenterBall = []
        yCenterBall = []
        rms = []
        rmsAngles = []
        #print("axisChart", self.centers[ axisId ] )
         
        for k, p in self.centers[ axisId ].items():
            angles.append( k )
            xCenterBall.append( p.x )
            yCenterBall.append( p.y )
            rmsAngles.append( update_ticks( k ) / 360 * 2 * pi )
            rms.append( np.sqrt(p.x**2+p.y**2) )
            

        #ax = plt.subplot(111)
        ax.set_title( title )
        ax.plot( angles, xCenterBall, "bs", ls='-.', label='x', markersize=5 )
        ax.plot( angles, yCenterBall, "r^", ls='-.', label='y', markersize=5 )
        ax.plot( angles, rms, rmsColor + '+', ls='-', label='RMS', markersize=8 )

        ax.xaxis.set_major_formatter( ticker.FuncFormatter(update_ticks))
        
        if axisId == "T":
            ax.set_xlim([-90, 90])
            ax.set_xticks(np.arange(-90, 95, 45))
        
        else:
            ax.set_xlim([-180, 180])
            ax.set_xticks(np.arange(-180, 185, 45))          
            
        # wenn die maximalen y Werte kleiner 1 sind immer limit +-1 verwenden 
        #print("ylimit", ax.get_ylim(), max(ax.set_ylim()) )
        if max(ax.set_ylim()) < 1:
            ax.set_ylim([-1, 1])
               
        ax.set_ylabel('mm')
        ax.set_xlabel('Winkel')
        
        ax.grid(True)
        ax.legend(numpoints=1)
        
        return { "angles": rmsAngles, "rms":rms }
    
        #plt.show()
        
    def plotChart(self, chartSize={}, text=""):
        """Alle Achsen charts ausgeben
        """
        
        fig, ax = self.initPlot( chartSize, True, nrows=2, ncols=2 )
          
        #print( self.centers )
        rms = {}
        for mpl_axis, wl_axis, title, color in zip_longest(
                ax.flatten(), ["G", "C", "T"], ["Gantry", "Kollimator", "Tisch"], ["g", "m", "c"]
                ):
            #print( mpl_axis, wl_axis)
            if wl_axis in ["G", "C", "T"]:
                try:
                    rms[ wl_axis ] = self._axisChart( mpl_axis, wl_axis, title, color )
                except:
                    # print( "plotChart", mpl_axis, wl_axis, title, color )
                    pass
            else:
                # jetzt sind in rms alle achsen
                # Initialise the spider plot

                mpl_axis.axis('off') 
                gs = fig.add_gridspec( 2, 4)
                
                ax = fig.add_subplot( gs[1, 2 ], polar=True )
                
                #ax = plt.subplot(2,2,4, polar=True, )
               
                #print("WL.plotChart", gs )
                ax.set_title( "RMS", position=(0.5, 1.1) )
                # If you want the first axis to be on top:
                ax.set_theta_offset(pi / 2)
                ax.set_theta_direction(-1)

                ax.plot( rms[ "G" ]["angles"], rms[ "G" ]["rms"], 'go', ls='-', label='Gantry', alpha=1, markersize=4 )
                #ax.fill( rms[ "G" ]["angles"], rms[ "G" ]["rms"], color="green", alpha=0.4 )
                ax.plot( rms[ "C" ]["angles"], rms[ "C" ]["rms"], 'm^', ls='-', label='Kollimator',alpha=1, markersize=4 )
                #ax.fill( rms[ "C" ]["angles"], rms[ "C" ]["rms"], color="blue", alpha=0.4 )
                ax.plot( rms[ "T" ]["angles"], rms[ "T" ]["rms"], 'cs', ls='-', label='Tisch', alpha=1, markersize=4 )
                # Draw ylabels
                ax.set_rlabel_position(0)
                
                # Achsenlimit
                # wenn die maximalen y Werte kleiner 1 sind immer limit 0/1 verwenden 
                ylimit = ax.get_ylim()
                #print("ylimit-RMS", ax.get_ylim() )
                if max(ax.get_ylim()) < 1:
                    ylimit =  [0, 1]
                    ax.set_ylim( ylimit )
                
                # skalierung der Achse
                ax.yaxis.set_major_formatter(ticker.FormatStrFormatter('%0.2f'))
                plt.yticks(np.arange( ylimit[0], ylimit[1] , 0.25 ), color="grey", size=9)
                
                # legende
                ax.legend(numpoints=1, loc=(0.9, .9) )
                
                # text
                ax = fig.add_subplot( gs[1, -1 ] )
                ax.axis('off')
                
                # np.max gibt einen fehler bei leerem Array deshalb abfangen
                gmax = 0
                cmax = 0
                tmax = 0
                if len( rms[ "G" ]["rms"] ) > 1:
                    gmax = np.max( rms[ "G" ]["rms"] )
                if len( rms[ "C" ]["rms"] ) > 1:
                    cmax = np.max( rms[ "C" ]["rms"] )  
                if len( rms[ "T" ]["rms"] ) > 1:
                    tmax = np.max( rms[ "T" ]["rms"] )  
                        
                ft = """
                    Virt. ISO (x/y): {:1.3f} / {:1.3f}\n
                    Max. Gantry Abweichung: {:1.3f}\n
                    Max. Kollimator Abweichung: {:1.3f}\n
                    Max. Tisch Abweichung: {:1.3f}\n
                    {}
                """.format(self.virtualCenter.x , self.virtualCenter.y,
                         gmax,
                         cmax,
                         tmax,
                         text
                        )
                
                ft = re.sub('[ \t]+' , ' ', ft)
                #print( ft.splitlines() )
                #t = ""
                #for line in ft.splitlines():
                    #print("line", line.trim() )
                    #t += line.trim()
                ax.text(0, 0, ft, fontsize=20, bbox=dict(facecolor='yellow', alpha=0.3))
            
        plt.tight_layout(pad=0.4, w_pad=0.1, h_pad=1.0)
        plt.subplots_adjust( hspace=0.4, wspace=0.2)
        return self.getPlot()
    
    def _axisImage(self, ax=None, axisId="", title="" ):
        """Ein Achsen Bild mit markern ausgeben
        
        
        """
        import matplotlib.patches as patches
        cmap=plt.cm.gray
        ax.imshow( self.mergeArray[axisId], cmap=cmap )
        
        # ein Kreis für das erwartete Zentrum der Kugel
        circ = patches.Circle((self.virtualCenterDots.x, self.virtualCenterDots.y,), 6, alpha=1, ec='yellow', fill=False)
        ax.add_patch(circ)

        ax.set_title( title )
        ax.axis('off')
        
        #print(self.roi )
        
        # Achsenbeschriftung in mm
        # x-Achse
        #xlim = ax.get_xlim()
        
        #width = xlim[0] + xlim[1] 
        #print(width)
        #x = np.arange(0, len( transmission["profile"] ), width / 4 )
        #ax.get_xaxis().set_ticklabels([ -20, -10, 0, 10, 20])
        #ax.get_xaxis().set_ticks( x )
        
        #ax.set_xlim( [ self.roi["X1"], self.roi["X2"] ] )
        #ax.set_ylim( [ self.roi["Y1"], self.roi["Y2"] ] )
        #ax.plot( len(self.mergeArray[axisId])/2, len(self.mergeArray[axisId])/2, 'y+', ms=100, markeredgewidth=1 ) 
        ax.plot( self.virtualCenterDots.x, self.virtualCenterDots.y, 'y+', ms=200, markeredgewidth=1 ) 
        
           
    def plotMergeImage(self, imageSize={} ):
        """Alle Achsen Bilder ausgeben
        
        """
        # plotbereiche festlegen
        fig, ax = self.initPlot( imageSize, nrows=1, ncols=3)
        
        for mpl_axis, wl_axis, title in zip_longest(
                ax.flatten(), ["G", "C", "T"], ["Gantry", "Kollimator", "Tisch"]
                ):
            try:
                self._axisImage( mpl_axis, wl_axis, title )
            except:
                #print( "plotMergeImage", mpl_axis, wl_axis, title )
                pass
            
        plt.tight_layout(pad=0.4, w_pad=0.5, h_pad=1.0)
        return self.getPlot()
        
    
class checkWL( ispBase ):
        
    def doMT_WL(self, fileData ):  
        """
                    
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
        
        result = [] 
                
        # wird für progress verwendet
        filesMax=len( fileData )
        self.fileCount = 0
        
        # metadata vorbereiten
        md = self.metadata
        #print( fileData['SeriesUID'] )
        md.update( {
           # "Titel": "Auswertung",
           # "Betreff": "Monatstest WL",

            "imageSize" : {"width" : 181, "height" : 45},
            "chartSize" : {"width" : 181, "height" : 95},
            
            "fieldSize" : { "X1":-10, "X2": 10, "Y1": -10, "Y2": 10, "xStep":10, "yStep":10 },
            
            "_image" : { "height": "45mm"  },
            "_chart": { "height" : "90mm" },
            
            "table_fields" : [
                {'field': 'Kennung', 'label':'Kennung', 'format':'{0}', 'style': [('text-align', 'left')] },
                {'field': 'gantry', 'label':'Gantry', 'format':'{0:1.1f}'},
                {'field': 'collimator', 'label':'Kollimator', 'format':'{0:1.1f}'},
                {'field': 'table', 'label':'Tisch', 'format':'{0:1.1f}'},
                {'field': 'centerBall_X', 'label':'X-Abweichung', 'format':'{0:1.3f}'},
                {'field': 'centerBall_Y', 'label':'Y-Abweichung', 'format':'{0:1.3f}'},
                {'field': 'maxCenter_passed', 'label':'Passed' }
            ]
        } )
                       
        def groupBySeries( df_group ):
            """Serienweise Auswertung und PDF Ausgabe 
            
            """
            
            # das Datum vom ersten Datensatz verwenden
            checkDate = df_group['AcquisitionDateTime'].iloc[0].strftime("%d.%m.%Y")
            self.pdf.setContentName( checkDate )
            
            #               
            # Anleitung
            #
            self.pdf.textFile( md["anleitung"], attrs={"class":"layout-fill-width"} )  
            
            wl = qa_wl( df_group.to_dict('index') , md["fieldSize"] )
            # als erstes das virtuelle Zentrum über die Kollimator Rotation festlegen
            wl.findColliCenter()
             
            data = {}
            cb_result = []
            # in jedem Feld die Kugel bestimmen
            for key, info in wl.fields.items():
                #print( key )
                centerBall = wl.findCenterBall( key )
                if centerBall:
                    
                    # daten für die Tabelle zusammenstellen 
                    data[ info["Kennung"] ] = { 
                       "Kennung": info["Kennung"],
                       "gantry":  info["gantry"], 
                       "collimator": info["collimator"], 
                       "table": info["table"],
                       "Abweichung (x/y) [mm]": "{:1.3f} / {:1.3f}".format( centerBall.x , centerBall.y),      
                    }  
                    cb_result.append({
                        "Kennung": info["Kennung"],
                        "gantry":  info["gantry"], 
                        "collimator":  info["collimator"], 
                        "table": info["table"],
                        "centerBall_X" : centerBall.x,
                        "centerBall_Y" : centerBall.y,
                        "Passed": None,
                        "acceptance": None
                    })
                    
                # progress pro file stimmt nicht immer genau (baseimage)
                # 40% für die dicom daten 40% für die Auswertung 20 % für das pdf
                self.fileCount += 1
                if hasattr( logger, "progress"):
                    logger.progress( md["testId"],  40 + ( 40 / filesMax * self.fileCount ) )
            
            # DataFrame erstellen
            data_frame = pd.DataFrame( data )
            # zeilen und spalten tauschen, und nach Art, Doserate, Speed sortieren
            data_frame = data_frame.transpose().sort_values(by=[ "table", "collimator", "gantry" ], ascending=True)
            
            # Anzahl der Bilder pro Achse ohne 0,0,0
            #len_T = len( data_frame[ data_frame["Tisch"] > 0 ] )
            #print(len_T)
                        
            # die achsen Bilder ausgeben
            g = wl.plotMergeImage( md["imageSize"] )
            self.pdf.image( g, attrs=md["_image"] )
              
            text_values = {
                "f_warning": md.tolerance[ md["energy"] ].default.warning.get("f",""),
                "f_error": md.tolerance[ md["energy"] ].default.error.get("f","")
            }

            text = "Warnung bei: {f_warning}\n Fehler bei: {f_error}".format( **text_values ).replace("{value}", "Abw. (x|Y)")
            # das chart ausgeben
            g = wl.plotChart( md["chartSize"], text )
            self.pdf.image( g, attrs=md["_chart"] )
           
            # ausgabe tabellen daten
            df = pd.DataFrame( cb_result )
            df.sort_values(by=[ "table", "collimator", "gantry" ], ascending=True, inplace=True)
            
            # max absolute Abweichung maxCenter ablegen
            df["maxCenter"] = df[["centerBall_X", "centerBall_Y"]].abs().max(axis=1)
               
            #
            # Abweichung ausrechnen und Passed setzen
            #
            check = [
                { "field": 'maxCenter', 'tolerance':'default' }   
            ]
            acceptance = self.check_acceptance( df, md, check )
            
            if len(df_group) < 19:
                # zu wenig Felder ist hier nicht OK -> warning
                acceptance = 3
            
            # print( df[ ["table", "collimator", "gantry"] ] )
            #
            # Ergebnis in result merken
            #
            result.append( self.createResult( df, md, check, 
                df_group['AcquisitionDateTime'].iloc[0].strftime("%Y%m%d"), 
                len( result ), # bisherige Ergebnisse in result
                acceptance
            ) )
            
            
            #
            # Tabelle erzeugen
            #
            self.pdf.pandas( df, 
               # attrs={"class":"layout-fill-width", "margin-right": "15mm" },
                attrs={"margin-right": "15mm" },
                fields=md["table_fields"]
            )
            
            # sonst das schlechteste aus der Tabelle
            self.pdf.resultIcon( acceptance )
            
        #
        # Gruppiert nach Tag und SeriesNumber abarbeiten
        #
        fileData.groupby( [ 'day', 'SeriesNumber' ] ).apply( groupBySeries ) 
        
        # abschließen pdfdaten und result zurückgeben
        return self.pdf.finish(), result 
    
    