# -*- coding: utf-8 -*-

__author__ = "R. Bauer"
__copyright__ = "MedPhyDO - Machbarkeitsstudien des Instituts für Medizinische Strahlenphysik und Strahlenschutz am Klinikum Dortmund im Rahmen von Bachelor und Masterarbeiten an der TU-Dortmund / FH-Dortmund"
__credits__ = ["R.Bauer", "K.Loot"]
__license__ = "MIT"
__version__ = "0.2.0"
__status__ = "Prototype"

import matplotlib.pyplot as plt

from app.image import DicomImage

from isp.plot import plotClass

import logging
logger = logging.getLogger( "MQTT" )

class ispCheckClass(  ):
    """ Hilfsfunktionen für alle check Module
    
    Attributes
    ----------
    image : instance of DicomImage
        
    baseImage : instance of DicomImage
        das zum normalisieren zu verwendende Bild    
    
    infos : dict
        die infos aus self.image.infos
        
    checkField : dict
        die für die Tests zu verwendende Bildinformatioen
        
    baseField : dict
        die für das normalisieren zu verwendende Bildinformatioen
                
    """

    def __init__( self, image:DicomImage=None, baseImage:DicomImage=None, normalize="none" ):
        """Check Klasse initialisieren
        """
        #self.checkField = None
    
        self.image = image
    
        self.baseImage = baseImage
    
        #self.baseField = None
    
        self.infos = {}
        
        # ist auch das baseImage da dann ggf normalisieren
        if not self.baseImage == None:
            self.normalize( normalize )
        
        # infos auch über die eigene Klasse erreichbar machen
        if not self.image == None:
            self.infos = self.image.infos
            

    def normalize( self, normalize: str="diff" ):
        '''Normalisiert checkField mit baseField
           in self.image.array liegen anschließend die normalisierten Daten 
        

        Parameters
        ----------
        normalize : str, optional
            Art der Normalisierung. The default is "diff".
            - none: keine Normalisierung durchführen
            - diff: test / open
            - prozent: (test - open) / open
            
        Returns
        -------
        None.

        '''
                
        # image.array als image.arrayOriginal merken
        self.image.arrayOriginal = self.image.array.copy()
        
        #print("### ispCheckClass.normalize", self.image, self.baseImage, normalize)
        
        """
        if basefilename:

            if self.debug: 
                print("---------------------------")
                print("OpenImage: %s, min: %1.3f, max: %1.3f, DPMM: %1.3f, DPI: %1.3f, CAX-x: %1.3f CAX-y:%1.3f" 
                      % (self.openfilename, np.amin(openImg.array), np.amax(openImg.array), 
                         openImg.dpmm, openImg.dpi, openImg.cax.x, openImg.cax.y ) )
                self.printMetaInfo( openImg.metadata )
   

        if self.debug: 
            print("---------------------------")
            print("CheckImage: %s, min: %1.3f, max: %1.3f, DPMM: %1.3f, DPI: %1.3f, CAX-x: %1.3f CAX-y:%1.3f"  
                  % (testfilename, np.amin(checkImage.array), np.amax(checkImage.array), 
                     checkImage.dpmm, checkImage.dpi, checkImage.cax.x, checkImage.cax.y ) )
            self.printMetaInfo( checkImage.metadata )
        

        """  
        base = self.baseImage.array.copy()
        check = self.image.array.copy()
        
        if normalize == "diff":
            # Beide Arrays um 0.000001 erhöhen und geschlossenes durch offene teilen
            self.image.array = (check + 0.000001) / (base + 0.000001)
        elif normalize == "prozent":
            self.image.array = ( (check + 0.000001) - (base + 0.000001) ) / (base + 0.000001)

    def getMeanDose( self, field=None ):
        """Die mittlere Dosis eines Angegebenen Bereichs ermitteln
        
        """
        if not field:  # pragma: no cover
            field =  { "X1":-2, "X2": 2, "Y1": -2, "Y2":2 }
        # holt den angegebenen Bereich um dort die Dosis zu bestimmen
        roi = self.image.getRoi( field ).copy()
        #print( roi.mean() )
        return roi.mean()
        #print( self.metadata )

    