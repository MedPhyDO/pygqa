# -*- coding: utf-8 -*-
'''

plot
====
'''

__author__ = "R. Bauer"
__copyright__ = "MedPhyDO - Machbarkeitsstudien des Instituts für Medizinische Strahlenphysik und Strahlenschutz am Klinikum Dortmund im Rahmen von Bachelor und Masterarbeiten an der TU-Dortmund / FH-Dortmund"
__credits__ = ["R. Bauer", "K.Loot"]
__license__ = "MIT"
__version__ = "0.1.0"
__status__ = "Prototype"

import matplotlib.pyplot as plt
import io

import logging
logger = logging.getLogger( "MQTT" )

# Units
inch = 72.0
cm = inch / 2.54
mm = cm * 0.1
pica = 12.0

# default für die Erstellung von plots - plt.rcParams.update( rcParams )
rcParams =  {
    'figure.max_open_warning': 0, # Warnung unterdrücken: RuntimeWarning: More than 20 figures have been opened.
    'font.size': 20,
    'legend.fontsize': 'medium',
    'figure.titlesize': 'large',
    'interactive': False,
    'figure.figsize': (6.4, 4.8)
}

class plotClass():
    """Erweiterung für pyplot.
    
    Attributes
    ----------   
    _plotPosition: list
        Aktuelle PlotPosition. Default ist [0,0]
    fig:
        plt.subplots fig.  Default ist None
    ax:
        plt.subplots ax. Default ist None
    """
    
    def __init__( self ):
        self._plotPosition = [0 , 0]
    
        self.fig = None
        self.ax = None
 
    
    def initPlot(self, imgSize=None, getPlot=True, **args ):
        """Figure und axis initialisieren.
        
        Parameters
        ----------
        imgSize: dict
            größe des Plotbereichs - default: ``{"width": 90, "height": 90 }``
        getPlot: boolean
            bei true plt.ioff aufrufen
        args:
            zusätzliche Angaben für plt.subplots
            
        """

        # defaults für plt setzen
        plt.rcParams.update( rcParams )
      
        
        # soll der plot zurückgegeben werden ioff setzen
        if getPlot:
            plt.ioff()
               
        # figsize immer angeben
        if not "figsize" in args:
            # scalierung für die figure größe
            figscale = 0.4 # 0.2

            if not imgSize: 
                imgSize = {"width": 90, "height": 90 }
            args["figsize"] = ( imgSize["width"] / mm * figscale, imgSize["height"] / mm * figscale )
        
        # plotbereiche erstellen 
        self.fig, self.ax = plt.subplots( **args )

        return self.fig, self.ax

        
    def getPlot(self):
        """Plot als Bytecode zurückgeben.
        
        Returns
        -------
        data : BytesIO
            Bytecode des Plots

        """
        data = io.BytesIO()
        plt.savefig( data )

        return data
    
    def showPlot(self):
        """Zeigt den erstellt Plot an.
        
        """
        plt.show()
        plt.ion()
        
        
