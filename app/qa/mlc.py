# -*- coding: utf-8 -*-

__author__ = "R. Bauer"
__copyright__ = "MedPhyDO - Machbarkeitsstudien des Instituts für Medizinische Strahlenphysik und Strahlenschutz am Klinikum Dortmund im Rahmen von Bachelor und Masterarbeiten an der TU-Dortmund / FH-Dortmund"
__credits__ = ["R.Bauer", "K.Loot", "J.Wüller"]
__license__ = "MIT"
__version__ = "0.2.1"
__status__ = "Prototype"

from pylinac.picketfence import PicketFence, Orientation, MLC, MLCArrangement
from pylinac.core.profile import FWXMProfilePhysical, MultiProfile

from mpl_toolkits.axes_grid1 import make_axes_locatable

from app.base import ispBase
from app.image import DicomImage
from app.check import ispCheckClass

from isp.config import dict_merge

from dotmap import DotMap
import numpy as np
import pandas as pd

import matplotlib.pyplot as plt

import logging
logger = logging.getLogger( "ISP" )

from isp.plot import plotClass

class qa_mlc( PicketFence, ispCheckClass ):
    """Erweitert die Klasse PicketFence, um eine eigene DicomImage Erweiterung zu verwenden

    """
    _log_fits = None

    _kennung = "{Kennung}"

    setting = dict()

    def __init__( 
        self, 
        checkField=None, 
        baseField=None, 
        normalize: str="diff", 
        kennung:str="{Kennung}",
        mlc: MLC | MLCArrangement | str = MLC.MILLENNIUM
    ):
        """
        Attributes
        ----------
        checkField:

        baseField:

        normalize:

        kennung : format string
            Welche Felder aus infos sollen für das Feld Kennung verwendet werden.
            default: {Kennung}
        """

        self._is_analyzed = False

        self._kennung = kennung
        self.checkField = checkField
        self.baseField = baseField

        # ispCheckClass initialisieren ruft ggf normalize auf
        if self.checkField and self.baseField:
            # checkField und baseField wurden angegeben, normalize möglich
            # self.image und self.baseImage initialisieren und ggf normalisieren
            ispCheckClass.__init__( self,
                image=DicomImage( self.checkField ),
                baseImage=DicomImage( self.baseField ),
                normalize=normalize
            )
        elif self.checkField:
            # nur checkfield wurde angegeben
            # self.image initialisieren
            ispCheckClass.__init__( self,
                image=DicomImage( self.checkField )
            )

        # default Settings einstellen
        self._orientation = None

        tolerance = 0.5
        action_tolerance = None

        self.mlc = self._get_mlc_arrangement(mlc)
        
        self.settings = {
            "orientation": self._orientation,
            "tolerance": tolerance,
            "action_tolerance": action_tolerance,
            "_log_fits": self._log_fits
        }

    def getLeafCenterPositions( self ):
        """Gibt die Positionen der Leaf Mitte aller Leafs

        """
        # Auswertepositionen (Mitte der Leafs)
        fl1 = np.arange(-195, -100, 10 )    # Leafbreite 10mm
        hl =  np.arange(-97.5, 100, 5 )     # Leafbreite 5mm
        fl2 = np.arange(105, 200, 10 )      # Leafbreite 10mm
        return np.concatenate( ( fl1, hl, fl2) )

    def isoTransmissions( self, positions ):
        """leaf und interleaf an den angegebenen Positionen ermitteln

        Attributes
        ----------
        positions : Positionen an denen ermittelt werden soll

        Returns
        -------
        dict - mit positions

        """
        transmissions = {}
        for idx in positions:
            transmissions[idx] = self.findTransmissions( idx )
        return transmissions

    def findTransmissions( self, position ):
        """Die transmissions bestimmen und mean über alle ermitteln.
        Diese Auswertung wird quer über alle Leafs verwendet

            leaf ( min )
            interleaf (max)

        Attributes
        ----------
        position :

        """
        if position < -200 or position > 200 :
            return {}

        # PixelPosition ermitteln
        pxPosition = self.image.mm2dots_X( position )

        """ Analysis """
        if self.infos["collimator"] == 90:
            self.image.rot90( n=3 )
        elif self.infos["collimator"] == 180:
            self.image.rot90( n=2 )
        elif self.infos["collimator"] == 270:
            self.image.rot90( n=1 )

        profile = MultiProfile( self.image.array[:, pxPosition] )

        """ max Peaks (interleaf) suchen """
        # max peaks für innere leafs bei 10 für äußere bei 20
        maxPeaks = []
        # FIXED: manchmal werden als peak_idx floats mit .0 von find_peaks ermittelt deshalb nach int wandeln
        peak_idxs, peak_heights = profile.find_peaks( min_distance=10, threshold=0.1 )
 
        for peak_idx in peak_idxs:
            maxPeaks.append( int( peak_idx ) )

        # mittelwert von maxPeaks
        meanMaxPeaks = np.mean( profile[maxPeaks] )

        """ min Peaks (leaf) suchen """
        minPeaks = []
        profile.invert()
        # FIXED: manchmal werden als peak_idx floats mit .0 von find_peaks ermittelt deshalb nach int wandeln
        peak_idxs, peak_heights = profile.find_peaks( min_distance=10, threshold=0.1 )
        for peak_idx in peak_idxs:
            minPeaks.append( int( peak_idx ) )
        profile.invert()
        # mittelwert von minPeaks
        meanMinPeaks = np.mean( profile[minPeaks] )

        # rotation wieder zurücknehmen
        if self.infos["collimator"] == 90:
            self.image.rot90( n=3 )
        elif self.infos["collimator"] == 180:
            self.image.rot90( n=2 )
        elif self.infos["collimator"] == 270:
            self.image.rot90( n=1 )

        return {
                'filename': self.infos["filename"],
                'Kennung': self._kennung.format( **self.infos ),
                'check_subtag': self.infos["check_subtag"],
                'position': position,
                'pxPosition': pxPosition,
                'type': self.infos['testTags'],
                'profile': profile,
                'unit':  self.infos['unit'],
                'energy': self.infos['energy'],
                'gantry' : self.infos['gantry'],
                'collimator': self.infos['collimator'],
                'leaf.peaks' : minPeaks,
                'leaf.min' : np.min( profile[minPeaks] ),
                'leaf.mean' : meanMinPeaks,
                'leaf.max' : np.max( profile[minPeaks] ),
                'interleaf.peaks' : maxPeaks,
                'interleaf.min' : np.min( profile[maxPeaks] ),
                'interleaf.mean' : meanMaxPeaks,
                'interleaf.max' : np.max( profile[maxPeaks] )
            }

    def FWHM_findLeafs( self, leafs:list=None, lfd:int=0, variante:str="" ):
        """Öffungsbreite und Position aller Leafpaare bestimmen

        Sucht über die Mitte jedes Leafpaares die Öffnugsbreite
        und Positionsabweichung zum Zentrum bei 50% Halbschatten

        Gibt die Werte für jedes leafpaar und min,max,mean für alle zurück

        Parameters
        ----------
        leafs : list, optional
            Auszuwertende Leafnummern bei none werden 1-60 verwendet. The default is None.
        lfd : int, optional
            lfd Angabe in der Rückgabe. The default is 0.
        variante : str, optional
            durchzuführende testvariante. The default is "".

        Returns
        -------
        dict
            lfd: int - Angabe aus Parameters
            filename: str - filename aus infos
            Kennung:
            checkPositions: list - die geprüften Positionen
            Richtung: str ('klein > groß'|'groß > klein') - über infos variante bestimmt
            Datum
            unit
            energy
            gantry
            collimator
            fwxm.data
            fwxm.min
            fwxm.max
            fwxm.mean:
            shift.data:
            shift.min:
            shift.max:
            shift.mean.

        """
        
        # alle Leaf center Positionen bestimmen
        checkPositions = self.getLeafCenterPositions()

        if leafs is None:
            # Leafs 1 bis 60, bei arrange 61 damit 60 im Ergebnis ist
            leafs = np.arange( 1, 61, 1 )

        leafData = {
            "fwxm": {},
            "shift": {}
        }

        # je nach subTag Richtung angeben
        richtung = ""
        if self.infos["varianten"][ variante ] == "vonklein":
            richtung = "klein > groß"
        elif self.infos["varianten"][ variante ] == "vongross":
            richtung = "groß > klein"

        # Aufbereitung für dataframe
        #df_data = {}
        leaf = 0
        for p in checkPositions:
            leaf = leaf + 1
            # nur wenn die Leafnummer ausgewertet werden soll
            if leaf in leafs:
                # Abhängigkeit von der Kollimatorrotation
                if self.infos["collimator"] == 90 or self.infos["collimator"] == 270:
                    # umdrehen für 270 oder 90
                    profile = FWXMProfilePhysical( 
                        self.image.array[ : , self.image.mm2dots_X( p ) ],
                        fwxm_height=50,
                        dpmm=self.image.dpmm
                    )
                else:
                    profile = FWXMProfilePhysical( 
                        self.image.array[ self.image.mm2dots_Y( p ) ],
                        fwxm_height=50,
                        dpmm=self.image.dpmm
                    )

                # Abstand der Lamellen 
                fwxm = profile.field_width_px
                leafData["fwxm"][p] = fwxm / self.image.dpmm
                # Zentrumsversatz bestimmen
                center = profile.center_idx
                leafData["shift"][p] = ( (len(profile.values) / 2) - center ) / self.image.dpmm

        # die eigentlichen Werte in ein array übernehmen
        fwxm_array = np.array( list( leafData["fwxm"].values() ) )
        shift_array = np.array( list( leafData["shift"].values() ) )

        # Daten so zurückgeben das sofort ein dataframe möglich ist
        return {
            'lfd': lfd,
            'filename': self.infos["filename"],
            'Kennung': self._kennung.format( **self.infos ),
            'checkPositions': checkPositions,
            'Richtung' : richtung,
            'Datum': self.infos['AcquisitionDateTime'],
            'unit':  self.infos['unit'],
            'energy': self.infos['energy'],
            'gantry' : self.infos['gantry'],
            'collimator': self.infos['collimator'],
            "fwxm.data" : leafData["fwxm"],
            "fwxm.min" : np.min( fwxm_array ),
            "fwxm.max" : np.max( fwxm_array ),
            "fwxm.mean" : np.mean( fwxm_array ),
            "shift.data" : leafData["shift"],
            "shift.min" : np.min( shift_array ),
            "shift.max" : np.max( shift_array ),
            "shift.mean" : np.mean( shift_array )
        }

    def FWHM_plot_error(self, data, size:dict={}, plotTitle:str="", leaf_from:int=1 ):
        """Barchart mit allen Leafpaaren 0-60 anzeigen mit
        der Öffnungsbreite (fwxm) und der Verschiebung vom Zentrum (shift)

        Es werden zwei barPlots jeweils für x1 und x2 angelegt

        Attributes
        ----------
        data: dict
            fwxm.data : array
            shift.data : array
        size: dict, optional
            Größe des Chart. The default is {}.
        plotTitle:str, optional
            Titel des Plots. The default is "".
        leaf_from : int, optional
            Nummer des ersten auzuwertenden leaf. The default is 1.

        Returns
        -------
        Rückgabe von getPlot()

        """

        virtLeafSize = 2.5
        error = 1.5
        limit = 2 * (error + virtLeafSize)
        # Chart Titel wenn nicht angegeben
        if plotTitle == "":
            plotTitle = "lfd:{lfd:d} G:{gantry:.0f} K:{collimator:.0f}"

        plot = plotClass( )
        fig, ax = plot.initPlot( size, False, nrows=1, ncols=1 )
        ax.set_title( plotTitle.format( **data, position=(0.5, 1.05) ) )
        plot_data = {
            "num" : [],
            "x1": [],
            "x2": [],
        }
        positions = []

        leaf = leaf_from
        for k, v in data['fwxm.data'].items():
            shift = data['shift.data'][ k ]
            plot_data["num"].append( leaf )

            # position und shift
            positions.append(k)
            v = ( (v - 50) / 2 ) + virtLeafSize

            plot_data["x1"].append( v + shift  )
            plot_data["x2"].append( -1 * v + shift  )
            # nächster leaf
            leaf += 1

        # x1 und x2 plotten beide in blue
        ax.bar(plot_data["num"], plot_data["x1"], color="#0343dfCC", linewidth=1)
        ax.bar(plot_data["num"], plot_data["x2"], color="#0343dfCC", linewidth=1)

        ax.set_ylim( -1 * limit, limit )
        ax.axhline(0, color='k', linewidth = 0.5)
        ax.axhline(virtLeafSize, color='k', linewidth = 0.2)
        ax.axhline( -1 * virtLeafSize, color='k', linewidth = 0.2)

        ax.axhline( error + virtLeafSize, color='r', linewidth = 0.5)
        ax.axhline( -1 * (error + virtLeafSize), color='r', linewidth = 0.5)

        ax.set_xticks( [1,10,30,50,60] )

        ax.set_axisbelow(True)
        ax.grid( True )

        plt.tight_layout(pad=0.4, w_pad=0.5, h_pad=1.0)

        return plot.getPlot()


    def FWHM_plot_errorBox( self, data, size={} ):
        """FWHM errorBox plotten

        Attributes
        ----------
        data: dict
            fwxm.data : array
            shift.data : array

        size: dict

        """
        # plotbereiche festlegen
        plot = plotClass( )
        fig, ax = plot.initPlot( size, nrows=2, ncols=1 )

        #
        # chart Leafpaarabstand
        #
        if "fwxm.data" in data:
            df_fwxm = pd.DataFrame( data["fwxm.data"] )#.transpose()
            # matplotlib 3.4.0 - Passing "range" to the whis parameter to mean "the whole data range" is no longer supported. set it to 0, 100 instead.
            df_fwxm.boxplot(ax = ax[0], whis=[0,100])

            ax[0].set_title('Leafpaarabstand (fwxm)')
            ax[0].get_yaxis().set_ticks( [48.5, 49, 49.5, 50, 50.5, 51, 51.5] )
            ax[0].get_yaxis().set_ticklabels([48.5, 49, 49.5, 50, 50.5, 51, 51.5])
            ax[0].axhline(50, color='k', linewidth = 0.5)

        #
        # chart Zentrumsabweichung
        #
        if "shift.data" in data:
            df_shift = pd.DataFrame( data["shift.data"] )#.transpose()
            # matplotlib 3.4.0 - Passing "range" to the whis parameter to mean "the whole data range" is no longer supported. set it to 0, 100 instead.
            df_shift.boxplot(ax = ax[1], whis=[0,100])

            ax[1].set_title('Zentrumsabweichung (shift)')
            ax[1].get_yaxis().set_ticks( [1.5, 1, 0.5, 0, -0.5, -1, -1.5] )
            ax[1].get_yaxis().set_ticklabels([1.5, 1, 0.5, 0, -0.5, -1, -1.5])
            ax[1].axhline(0, color='k', linewidth = 0.5)

        plt.tight_layout(pad=0.4, w_pad=0.5, h_pad=1.0)

        return plot.getPlot()


    def plotTransmission( self, transmission, chartSize={}, showInterleafMean=False, showLeafMean=False, showInterleafPeaks=False, showLeafPeaks=False ):
        """
            profile mit Peaks anzeigen
        """

        # plotbereiche festlegen
        plot = plotClass( )
        fig, ax = plot.initPlot( chartSize )

        ax.set_xlabel('Position [mm]')

        plt.title('Transmission von %s an der Position: %i mm. Mean: Leaf=%1.3f Interleaf=%1.3f ' % (
                transmission["type"],
                transmission["position"],
                transmission["leaf.mean"],
                transmission["interleaf.mean"],
                ) )

        # kurve anzeigen
        plt.plot( transmission["profile"]  )

        # Achsenbeschriftung in mm
        # x-Achse
        xlim = ax.get_xlim()
        width = xlim[0] + xlim[1]
        x = np.arange(0, len( transmission["profile"] ), width / 4 )
        ax.get_xaxis().set_ticklabels([ -200, -100, 0, 100, 200])
        ax.get_xaxis().set_ticks( x )

        # maxPeaks (interleaf)
        if showInterleafPeaks:
            ax.plot( transmission["interleaf.peaks"], transmission["profile"][ transmission["interleaf.peaks"] ], "x", color="orange" )

        # Mittelwert der maxPeaks
        if showInterleafMean:
            ax.axhline( transmission["interleaf.mean"], linestyle="-", linewidth=1, color="orange" )

        # minPeaks (leaf)
        if showLeafPeaks:
            ax.plot( transmission["leaf.peaks"], transmission["profile"][ transmission["leaf.peaks"] ], "x", color="green" )

        # Mittelwert der minPeaks
        if showLeafMean:
            ax.axhline( transmission["leaf.mean"], linestyle="-", linewidth=1, color="green" )

        # layout opimieren
        plt.tight_layout(pad=0.4, w_pad=0.5, h_pad=1.0)
        # data der Grafik zurückgeben
        return plot.getPlot()

    def picketfence_results(self):
        """Gibt die Ergebnisse der Picketfence Auswertung als dict
        Verwendet dabei zusätzlich eine Auswertung über error_hist ( daten für subplot )
        - pickets
        - mlc_meas
        
        use results_data()
        """

        result = {
            'filename': self.infos["filename"],
            'Kennung': self._kennung.format( **self.infos ),    # FIXME: identify, sign, label
            'unit':  self.infos['unit'],
            'energy': self.infos['energy'],
            'gantry' : self.infos['gantry'],
            'collimator': self.infos['collimator'],
            'checkPositions': -1,
            "offsets" : -1,
            "pass_pct" : False,
            "abs_median_error": -1,
            "abs_mean_error": -1,
            
            "max_error": -1,
            "max_error_picket" : -1,
            "max_error_leaf" : -1,
            "passed": False,
        
            "passed_action" : False,
            "mean_spacing" : -1,
            "max_from_mean" : -1,
            "max_from_mean_leaf": -1

        }
        if not hasattr(self, "pickets"):
            return result
      
        rd = self.results_data()       
        offsets = " ".join(f"{pk.dist2cax:.1f}" for pk in self.pickets)
              
        '''

        # max von mean bestimmen
        error_plot_positions, error_means, error_stds, mlc_leaves = self.pickets.error_hist()

        # pandas serie max und position bestimmen
        pd_error_means = pd.Series( error_means )
        max_from_mean_error = pd_error_means.max()
        # FIXME: image muss up/down getauscht werden, deshalb auch die MLC Nummern ändern
        max_from_mean_leaf = mlc_leaves[ pd_error_means.idxmax() ][1] - 60
        '''
        # calculate the mean error and stdev values per MLC pair
        error_vals = []
        leaf_nums = [] # b)

        for leaf_num in {m.leaf_num for m in self.mlc_meas}:
            leaf_nums.append( leaf_num ) # b)
            mean = np.mean(
                [np.abs(m.error) for m in self.mlc_meas if m.leaf_num == leaf_num]
            )
            error_vals.append( mean )

        pd_error_means = pd.Series( error_vals )
        max_from_mean_error = pd_error_means.max()
        max_from_mean_leaf = leaf_nums[ pd_error_means.idxmax() ] # - 60

        result = {
            'filename': self.infos["filename"],
            'Kennung': self._kennung.format( **self.infos ),    # FIXME: identify, sign, label
            'unit':  self.infos['unit'],
            'energy': self.infos['energy'],
            'gantry' : self.infos['gantry'],
            'collimator': self.infos['collimator'],
            'checkPositions': self.pickets,
            "offsets" : offsets,
            "pass_pct" : self.percent_passing,
            "abs_median_error": self.abs_median_error,
            
            "max_error": self.max_error,
            "max_error_picket" : self.max_error_picket,
            "max_error_leaf" :self.max_error_leaf,
            "passed": self.passed,
        
            "passed_action" : False,
            "abs_mean_error": self.abs_mean_error,
            "mean_spacing" : rd.mean_picket_spacing_mm,
            "max_from_mean" : max_from_mean_error,
            "max_from_mean_leaf" : max_from_mean_leaf,
        }
        return result

    def picketfence_plotImage(self, guard_rails: bool=True, mlc_peaks: bool=True, overlay: bool=True,
                            leaf_error_subplot: bool=True, show: bool=False, metadata={} ):
        """Plot the analyzed image.

        Parameters
        ----------
        guard_rails : bool
            Do/don't plot the picket "guard rails" around the ideal picket
        mlc_peaks : bool
            Do/don't plot the MLC positions.
        overlay : bool
            Do/don't plot the alpha overlay of the leaf status.
        leaf_error_subplot : bool

            .. versionadded:: 1.0

            If True, plots a linked leaf error subplot adjacent to the PF image plotting the average and standard
            deviation of leaf error.
        """

        # figsize immer (24,14) passt für 'Left-Right' und 'Up-Down'
        figsize = (24,14)

        # plot the image
        plot = plotClass( )
        fig, ax = plot.initPlot(  )

        img, fig, ax = self.image.plotImage( 
            original=False, 
            getPlot=False,
            metadata=metadata,
            plotTitle="{Kennung} - G:{gantry:.0f} K:{collimator:.0f}",
            plotCax=False,
            plotField=True,
            figsize=figsize,
            field=metadata.field # { "X1":-100, "X2": 100, "Y1": -100, "Y2":100, "xStep":50, "yStep":50, "border": 10 }
        )

        # generate a leaf error subplot if desired
  
        if hasattr(self, "pickets") and leaf_error_subplot:
            self._add_leaf_error_subplot( ax )
            pass

        # plot guard rails and mlc peaks as desired
        
        for p_num, picket in enumerate(self.pickets):
            if guard_rails:
                picket.add_guards_to_axes(ax.axes)
            if mlc_peaks:
                for idx, mlc_meas in enumerate(picket.mlc_meas):
                    mlc_meas.plot2axes(ax.axes, width=1.5)


        # plot the overlay if desired.
        if overlay:
            for mlc_meas in self.mlc_meas:
                mlc_meas.plot_overlay2axes(ax.axes)

        # plot CAX
        ax.plot(self.image.center.x, self.image.center.y, 'r+', ms=12, markeredgewidth=3)

        # tighten up the plot view
        ax.set_xlim([0, self.image.shape[1]])
        ax.set_ylim([0, self.image.shape[0]])

        if show:
            plt.show()

        return plot.getPlot()

    def _add_leaf_error_subplot(self, ax: plt.Axes) -> None:
        """Add a bar subplot showing the leaf error.

        Args:
            ax (plt.Axes): _description_

        Modifications
           - a) use double width on UP_DOWN Chart 
           - b) draw Leafnumbers 
           - c) change action_tolerance color to y-
           - d) set gridlines only on position Axis
        """        
        
        # make the new axis
        divider = make_axes_locatable(ax)
        if self.orientation == Orientation.UP_DOWN:
            axtop = divider.append_axes("right", 8, pad=1, sharey=ax) # a)
        else:
            axtop = divider.append_axes("bottom", 2, pad=1, sharex=ax)

        # get leaf positions, errors, standard deviation, and leaf numbers
        if self.orientation == Orientation.UP_DOWN:
            pos = [
                position.marker_lines[0].center.y
                for position in self.pickets[0].mlc_meas
            ]
        else:
            pos = [
                position.marker_lines[0].center.x
                for position in self.pickets[0].mlc_meas
            ]

        # calculate the error and stdev values per MLC pair
        error_stdev = []
        error_vals = []
        leaf_nums = [] # b)
        for leaf_num in {m.leaf_num for m in self.mlc_meas}:
            leaf_nums.append( leaf_num ) # b)
            error_vals.append(
                np.mean(
                    [np.abs(m.error) for m in self.mlc_meas if m.leaf_num == leaf_num]
                )
            )
            error_stdev.append(
                np.std([m.error for m in self.mlc_meas if m.leaf_num == leaf_num])
            )

        # plot the leaf errors as a bar plot
        if self.orientation == Orientation.UP_DOWN:
            axtop.barh(
                pos,
                error_vals,
                xerr=error_stdev,
                height=self.leaf_analysis_width * 10, # FIXME breite des Leafs
                alpha=0.4,
                align="center",
                tick_label=leaf_nums, # b)
            #    color="#0343dfCC"
            )
            # plot the tolerance line(s)
            axtop.axvline(self.tolerance, color="r", linewidth=3)
            if self.action_tolerance is not None:
                axtop.axvline(self.action_tolerance, color="y", linewidth=3) # c)
            # reset xlims to comfortably include the max error or tolerance value
            axtop.set_xlim(
                [0, max([max(error_vals) + max(error_stdev), self.tolerance]) + 0.1]
            )
            axtop.grid(True, axis="x") # d)
        else:
            axtop.bar(
                pos,
                error_vals,
                yerr=error_stdev,
                width=self.leaf_analysis_width * 2,
                alpha=0.4,
                align="center",
                tick_label=leaf_nums # b)
            )
            # plot the tolerance line(s)
            axtop.axhline(self.tolerance, color="r", linewidth=3)
            if self.action_tolerance is not None:
                axtop.axhline(self.action_tolerance, color="y", linewidth=3) # c)
            axtop.set_ylim(
                [0, max([max(error_vals) + max(error_stdev), self.tolerance]) + 0.1]
            )
            axtop.grid(True, axis="y") # d)

        axtop.set_title("Average Error (mm)")

    @property
    def abs_mean_error(self) -> float:
        """Return the maximum error found."""
        return float(np.mean(np.abs(self._flattened_errors())))

#
# -----------------------------------------------------------------------------
#
def transmissionsToPlot( **args ):
    """ Hilfsfunktion um Linien im Plot bei den Messorten zu plotten

    """
    self = args["self"]
    ax = args["ax"]

    transmissions = args["transmissions"]

    style = dict(linestyle="-", linewidth=1, color="green")
    # plot transmission positions
    for idx in transmissions:
        if self.infos["collimator"] == 0 or self.infos["collimator"] == 180:
            ax.axvline( transmissions[idx]["pxPosition"], **style )
        elif self.infos["collimator"] == 90:
            pxPosition = self.mm2dots_X(transmissions[idx]["position"] * -1 )
            ax.axhline( pxPosition, **style )
        else:
            pxPosition = self.mm2dots_X(transmissions[idx]["position"]  )
            ax.axhline( transmissions[idx]["pxPosition"] , **style )

#
# -----------------------------------------------------------------------------
#
class checkMlc( ispBase ):

    def doJT_4_2_2_1_A( self, fileData ):
        """ Test: 4.2.2.1 - A (leaf transmission)

        Es reicht das leaf-mean jeweils für x1 und x2 zu betrachten
        Verwendet: x2zu x1zu
        Messen: alle 10mm im Bereich von -70mm bis 70mm
        Positionen: Gantry=0° Colli=0°
        Energie: alle

        Anzeigen:
            Bilder mit Positionen
            Transmission an der Positon 0 ohne Kreuze
            Tabelle mit leaf-mean (spalten als positionen)

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

        # metadata vorbereiten
        md = dict_merge( DotMap( {
            "series_groupby": [ "day", "SeriesNumber" ],
            "series_sort_values" : ['check_subtag'],
            "field_count": 2,
            "manual": {
                "attrs": {"class":"layout-fill-width"},
            },
            "plotImage_pdf": {
                "area" : { "width": 80, "height": 80 },
                "attrs": {"class":"layout-50-width", "margin-right": "20px"},
            },

            "_chart": { "width": 180, "height": 45 },
            "_text" : { },
            "_text_attrs" : {"margin-left":"5mm"},
            # Messorte alle 10mm im Bereich von -70mm bis 70mm
            "checkPositions" : np.arange(-70, 80, 10),

            #"groupby": [ "day", "SeriesNumber" ], # groupby in der config angegeben werden sonst default (2019 nicht in der gleichen Serie)
            "table_fields" : [
                {'field': 'position', 'label':'Position', 'format':'{0:d}' },
                {'field': 'gantry', 'label':'Gantry', 'format':'{0:.0f}' },
                {'field': 'collimator', 'label':'Kollimator', 'format':'{0:.0f}' },
                {'field': 'leaf.mean_x', 'label':'X1-Leaf Mean', 'format':'{0:.3f}' },
                {'field': 'leaf.mean_x_passed', 'label':'X1-Passed'},
                {'field': 'leaf.mean_y', 'label':'X2-Leaf Mean', 'format':'{0:.3f}' },
                {'field': 'leaf.mean_y_passed', 'label':'X2-Passed'}
            ]
        } ), self.metadata )

        # Felder für die Tabelle
        def groupBySeries( df_group ):
            """gruppenweise Auswertung
            """

            # das Datum vom ersten Datensatz verwenden
            checkDate=df_group['AcquisitionDateTime'].iloc[0].strftime("%d.%m.%Y")
            self.pdf.setContentName( checkDate )

            #
            # Anleitung
            #
            self.pdf.textFile( **md.manual )

            # das offene Feld merken
            try:
                df_base = df_group.query("check_subtag.isnull()", engine='python')
            except:
                # ein leeres df damit in checkFields geprüft wird
                df_base = pd.DataFrame()

            # alle anderen filtern
            try:
                df_fields = df_group.query("check_subtag.notnull()", engine='python')
            except:
                # ein leeres df damit in checkFields geprüft wird
                df_fields = pd.DataFrame()


            # alles notwendige da? Ein base und 2 weitere Felder
            errors = self.checkFields( md, df_base, df_fields, md["field_count"])
            if len(errors) > 0:
                result.append( self.pdf_error_result(
                    md, date=checkDate, group_len=len( result ),
                    errors=errors
                ) )
                return

            # alle Felder durchgehen
            transmissionData = {}
            charts = ""

            # baseField bereitstellen
            baseField = self.getFullData( df_base.iloc[0] )
            self.fileCount += 1

            # alle anderen durchgehen (iterrows - <class 'pandas.core.series.Series'>)
            for (idx, info) in df_fields.iterrows():

                # Auswertung starten
                check = qa_mlc(
                        checkField=self.getFullData(info),
                        baseField=baseField,
                        normalize="diff"
                    )

                # Transmissionen suchen
                transmission = check.isoTransmissions( md["checkPositions"]  )

                #
                # Bild anzeigen
                #
                img = check.image.plotImage( plotTitle="{RadiationId} - {ImageId}"
                            , original=False, plotCax=False, plotField=False
                            , metadata=md
                            , arg_function=transmissionsToPlot, arg_dict={"transmissions": transmission}
                            )

                self.pdf.image( img, **md.plotImage_pdf )


                # Chart Transmission an der Positon 0 ohne Kreuze erzeugen
                imageData = check.plotTransmission( transmission[0]
                            #, metadata=metadata
                            , chartSize = md["_chart"]
                            , showLeafMean=True, showLeafPeaks=False )

                charts += self.pdf.image(imageData, md["_chart"], render=False  )

                transmissionData[ info['check_subtag'] ] = transmission.values()

                # progress pro file stimmt nicht immer genau (baseimage)
                # 40% für die dicom daten 40% für die Auswertung 20 % für das pdf
                self.fileCount += 1
                if hasattr( logger, "progress"):
                    logger.progress( md["testId"],  40 + ( 40 / filesMax * self.fileCount ) )

            #
            # charts anzeigen
            #
            self.pdf.html( charts )

            # daten neu zusammenstellen und x2 mean in die Liste einfügen
            # pandas verwenden
            x1 = pd.DataFrame( transmissionData["X1"] )# .rename( {"leaf.mean":"X1"} )

            x1.set_index("position")

            x2 = pd.DataFrame( transmissionData["X2"] )# .rename( {"leaf.mean":"X2"} )
            x2.set_index("position")

            # die beiden zusammenführen
            df = pd.merge( x1, x2, how='inner', on=['position', 'gantry', 'collimator'] )
            df.set_index( 'position' )

            #
            # Abweichung ausrechnen und Passed setzen
            #
            check = [
                { "field": 'leaf.mean_x', 'tolerance':'default' },
                { "field": 'leaf.mean_y', 'tolerance':'default' }
            ]
            acceptance = self.check_acceptance( df, md, check )

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
                attrs={ "class":"layout-50-width" },
                fields=md["table_fields"]
            )

            #
            # tolerance anzeigen
            #
            text_values = {
                "f_warning": md.current.tolerance.default.warning.get("f",""),
                "f_error": md.current.tolerance.default.error.get("f","")
            }
            text = """<br>
                Warnung bei: <b style="position:absolute;left:120mm;">{f_warning}</b><br>
                Fehler bei: <b style="position:absolute;left:120mm;">{f_error}</b>
            """.format( **text_values ).replace("{value}", "Leaf Mean")
            self.pdf.text( text, md["_text"], attrs=md["_text_attrs"] )

            # Gesamt check
            self.pdf.resultIcon( acceptance )

        #
        # Sortiert nach check_subtag
        # Gruppiert nach day und SeriesNumber abarbeiten
        # wenn angegeben die Gruppierung aus der config verwenden (2019 sind die Aufnahmen von unterschiedlichen Tagen)
        #
        ( fileData
             .sort_values( md["series_sort_values"] )
             .groupby( md["series_groupby"] )
             .apply( groupBySeries )
        )

        # abschließen pdfdaten und result zurückgeben
        return self.pdf.finish(), result

    def doJT_4_2_2_1_B( self, fileData ):
        """ Test: 4.2.2.1 - B (interleaf transmission)

        Verwendet: x2zu x1zu x6_kamm_0_0
        Messen: in 1cm Abständen
        Positionen: alle Kolli und Gantry Positionen
        Energie: x6
        Messorte: 0
        es gibt immer ein offenes feld für jede Gantry/Kollimator Variante

        Anzeigen:
            Bilder mit Positionen bei 0°
            Tabelle mit interleaf-mean und allen Datei Gantry/Kolli Positionen

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

        # metadata vorbereiten
        md = dict_merge( DotMap( {
            "series_groupby": [ "day", "SeriesNumber" ],
            "series_sort_values" : ['check_subtag', 'gantry', 'collimator'],
            "manual": {
                "attrs": {"class":"layout-fill-width"},
            },
            "field_count": 3,
            "plotImage_pdf":{
                "area": { "width": 58, "height": 58 },
                "attrs": {"class":"layout-50-width"}
            },
            "_text" : {},
            "_text_attrs" : {},
            "_table_attrs" : {"class":"layout-fill-width", "margin-top": "2mm"},
            # Messorte nur im zentrum
            "checkPositions" : [0] ,

            "table_fields" : [
                {'field': 'Kennung', 'label':'Kennung', 'format':'{0}', 'style': [('text-align', 'left')] },
                {'field': 'gantry', 'label':'Gantry', 'format':'{0:.0f}' },
                {'field': 'collimator', 'label':'Kollimator', 'format':'{0:.0f}' },
                {'field': 'interleaf.mean', 'label':'interleaf Mean', 'format':'{0:.3f}' },
                {'field': 'interleaf.mean_passed', 'label':'Passed'}
            ]
        } ), self.metadata )

        def groupBySeries( df_group ):
            """gruppenweise Auswertung
            """
            # das Datum vom ersten Datensatz verwenden
            checkDate = df_group['AcquisitionDateTime'].iloc[0].strftime("%d.%m.%Y")
            self.pdf.setContentName( checkDate )

            #
            # Anleitung
            #
            self.pdf.textFile( **md.manual )

            # alle Felder durchgehen
            data = []
            # gruppiert nach gantry und kollimator
            def groupByGantryKolli( df ):

                # das offene Feld merken
                try:
                    df_base = df.query("check_subtag.isnull()", engine='python')
                except:
                    # ein leeres df damit in checkFields geprüft wird
                    df_base = pd.DataFrame()

                # alle anderen filtern
                try:
                    df_fields = df.query("check_subtag.notnull()", engine='python')
                except:
                    # ein leeres df damit in checkFields geprüft wird
                    df_fields = pd.DataFrame()

                # alles notwendige da?
                errors = self.checkFields( md, df_base, df_fields, md["field_count"])
                if len(errors) > 0:
                    result.append( self.pdf_error_result(
                        md, date=checkDate, group_len=len( result ),
                        errors=errors
                    ) )
                    return

                # baseField bereitstellen
                baseField = self.getFullData( df_base.iloc[0] )
                self.fileCount += 1

                # alle anderen durchgehen (iterrows - <class 'pandas.core.series.Series'>)
                for (idx, info) in df_fields.iterrows():
                    # Auswertung starten
                    check = qa_mlc(
                             checkField=self.getFullData(info),
                             baseField=baseField,
                             normalize="diff",
                             kennung="{RadiationId} - {ImageId}"
                    )

                    # Transmissionen suchen (dict mit positionen als key)
                    transmissions = check.isoTransmissions( md["checkPositions"]  )

                    # data array um das transmissions array erweitern
                    data.extend( transmissions.values() )

                    if int(info["gantry"]) == 0 and int(info["collimator"] == 0):
                        #
                        # Bild anzeigen nur das 0° Feld
                        #
                        img = check.image.plotImage( plotTitle="{RadiationId} - {ImageId}"
                                    , original=False, plotCax=False, plotField=False
                                    , metadata=md
                                    , arg_function=transmissionsToPlot, arg_dict={"transmissions": transmissions}
                                    )

                        self.pdf.image( img, **md.plotImage_pdf )

                    # progress pro file stimmt nicht immer genau (baseimage)
                    # 40% für die dicom daten 40% für die Auswertung 20 % für das pdf
                    self.fileCount += 1
                    if hasattr( logger, "progress"):
                        logger.progress( md["testId"],  40 + ( 40 / filesMax * self.fileCount ) )


            # gruppierung durchführen
            #
            df_group.groupby( [ "gantry", "collimator" ] ).apply( groupByGantryKolli )

            # es wurden keine Felder gefunden (checkFields fehler)
            if len( data ) < 1:
                result.append( self.pdf_error_result(
                    md, date=checkDate, group_len=len( result ),
                    msg='<b>Datenfehler</b>: keine Felder gefunden oder das offene Feld fehlt.',
                    pos={ "top":150 }
                ) )
                return

            #
            # Tabelle erzeugen
            #

            # pandas dataframe erstellen
            df = pd.DataFrame( data )
            df.sort_values( ['check_subtag', 'gantry', 'collimator'], inplace=True )

            #
            # Abweichung ausrechnen und Passed setzen
            #
            check = [
                { "field": 'interleaf.mean', 'tolerance':'default' }
            ]
            acceptance = self.check_acceptance( df, md, check )

            #
            # Ergebnis in result merken
            #
            result.append( self.createResult( df, md, check,
                    df_group['AcquisitionDateTime'].iloc[0].strftime("%Y%m%d"),
                    len( result ), # bisherige Ergebnisse in result
                    acceptance
            ) )

            #
            # Tabelle anzeigen
            #
            self.pdf.pandas( df,
                attrs={"class":"layout-fill-width", "margin-top": "5mm"},
                fields=md["table_fields"]
            )

            #
            # tolerance anzeigen
            #
            text_values = {
                "f_warning": md.current.tolerance.default.warning.get("f",""),
                "f_error": md.current.tolerance.default.error.get("f","")
            }
            text = """<br>
                Warnung bei: <b style="position:absolute;left:45mm;">{f_warning}</b><br>
                Fehler bei: <b style="position:absolute;left:45mm;">{f_error}</b>
            """.format( **text_values ).replace("{value}", "interleaf Mean")
            self.pdf.text( text, md["_text"], attrs=md["_text_attrs"] )

            # Gesamt check
            self.pdf.resultIcon( acceptance )

        #
        # Sortiert nach check_subtag
        # Gruppiert nach day und SeriesNumber abarbeiten
        # wenn angegeben die Gruppierung aus der config verwenden (2019 sind die Aufnahmen von unterschiedlichen Tagen)
        #
        ( fileData
             .sort_values( md["series_sort_values"] )
             .groupby( md["series_groupby"] )
             .apply( groupBySeries )
        )

        # abschließen pdfdaten und result zurückgeben
        return self.pdf.finish(), result

    def doJT_4_2_2_1_C( self, fileData ):
        """ Test: 4.2.2.1 - C (interleaf Gap)

        Messorte: 0 / 40 / -40
        Verwendet: img_x6_tips_0_0 / img_x6_tipsX1_0_0 / img_x6_tipsX2_0_0
        Positionen: alle Kolli und Gantry Positionen
        Energie: x6

        es gibt immer ein offenes feld für jede Gantry/Kollimator Variante

        Anzeigen:
            Bilder mit Positionen
            Tabelle mit interleaf-mean und allen Datei Gantry/Kolli Positionen

            Nur Gantry Kolli 0 anzeigen

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

        # metadata vorbereiten
        md = dict_merge( DotMap( {

            "series_groupby": ["day", "SeriesNumber"],
            "field_count": 3, # drei Felder pro Auswertung
            "manual": {
                "attrs": {"class":"layout-fill-width", "margin-bottom": "5mm"},
            },
            "plotImage_pdf":{
                "area": { "width": 58, "height": 58 },
                "attrs": {"class":"layout-50-width"}
            },

            "_image_-40": { "width": 55, "height": 55, "left": 0, "top" : 15 },
            "_image_0": { "width": 55, "height": 55, "left": 60, "top" : 15 },
            "_image_40": { "width": 55, "height": 55, "left": 120, "top" : 15 },
            "_chart_-40": { "width": 58, "height": 50, "left": 0, "top" : 72 },
            "_chart_0": { "width": 58, "height": 50, "left": 60, "top" : 72 },
            "_chart_40": { "width": 58, "height": 50, "left": 120, "top" : 72 },
            "_text" : {"bottom" : 5},
            "_text_attrs" : {"class":"layout-fill-width"},
            "_table": { "top" : 125 },
            "_table_attrs" : {"class":"layout-fill-width", "margin-top": "0mm"},

            # Messorte nur im zentrum
            "checkPositions_tipsX1" : [40],
            "checkPositions_tips" : [0],
            "checkPositions_tipsX2" : [-40],
            "table_fields": [
                {'field': 'Kennung', 'label':'Kennung', 'format':'{0}', 'style': [('text-align', 'left')] },
                {'field': 'gantry', 'label':'Gantry °', 'format':'{0:.0f}' },
                {'field': 'collimator', 'label':'Kollimator °', 'format':'{0:.0f}' },
                {'field': 'position'},
                {'field': 'soll', 'label':'Mean soll', 'format':'{0:.3f}' },
                {'field': 'interleaf.mean', 'label':'interleaf Mean', 'format':'{0:.3f}' },
                {'field': 'diff', 'label':'Mean diff', 'format':'{0:.3f}' },
                {'field': 'diff_passed', 'label':'Passed'}
            ],
            "checkValues":{
                "-40" : None,
                "0" : None,
                "40" : None
            }
        } ), self.metadata )

        try:
            md["checkValues"]["-40"] = md.current.tolerance.get( "-40" ).soll.value
        except:
            pass
        try:
            md["checkValues"]["0"] = md.current.tolerance.get( "0" ).soll.value
        except:
            pass
        try:
            md["checkValues"]["40"] = md.current.tolerance.get( "40" ).soll.value
        except:
            pass

        def groupBySeries( df_group ):
            """gruppenweise Auswertung
            """

            # das Datum vom ersten Datensatz verwenden
            checkDate = df_group['AcquisitionDateTime'].iloc[0].strftime("%d.%m.%Y")
            self.pdf.setContentName( checkDate )

            #
            # Anleitung
            #
            self.pdf.textFile( **md.manual )

            # alle Felder durchgehen
            data = []

            # gruppiert nach gantry und kollimator
            def groupByGantryKolli( df ):
                #
                # das offene Feld merken
                try:
                    df_base = df.query("check_subtag.isnull()", engine='python')
                except:
                    # ein leeres df damit in checkFields geprüft wird
                    df_base = pd.DataFrame()

                # alle anderen filtern
                try:
                    df_fields = df.query("check_subtag.notnull()", engine='python')
                except:
                    # ein leeres df damit in checkFields geprüft wird
                    df_fields = pd.DataFrame()

                # logger.error( "Base: {}, Fields:{}".format( len(df_base.index), len(df_base.index) ) )
                # alles notwendige da? Ein base und 2 weitere Felder
                errors = self.checkFields( md, df_base, df_fields, md["field_count"])
                if len(errors) > 0:
                    result.append( self.pdf_error_result(
                        md, date=checkDate, group_len=len( result ),
                        errors=errors
                    ) )
                    return
                
                # baseField bereitstellen
                baseField = self.getFullData( df_base.iloc[0] )
                self.fileCount += 1

                # alle anderen durchgehen (iterrows - <class 'pandas.core.series.Series'>)
                for (idx, info) in df_fields.iterrows():
                    # Auswertung starten
                    check = qa_mlc(
                             checkField=self.getFullData(info),
                             baseField=baseField,
                             normalize="diff",
                             kennung="{RadiationId} - {ImageId}"
                    )

                    # Transmissionen suchen (dict mit positionen als key)
                    positions = md.get( "checkPositions_" + check.infos["check_subtag"] , [] )

                    transmissions = check.isoTransmissions( positions  )

                    # data array um das transmissions array erweitern
                    data.extend( transmissions.values() )

                    #
                    # Bild anzeigen nur das 0° Feld
                    #
                    if info["gantry"] == 0 and info["collimator"] == 0:

                        img = check.image.plotImage( plotTitle="{RadiationId} - {ImageId}"
                                    , original=True, plotCax=False, plotField=False
                                    , metadata=md
                                    , arg_function=transmissionsToPlot, arg_dict={"transmissions": transmissions}
                                    )
                        self.pdf.image( img, md[ "_image_{0:d}".format( positions[0] ) ], attrs=md["plotImage_pdf"]["attrs"] )

                    # progress pro file stimmt nicht immer genau (baseimage)
                    # 40% für die dicom daten 40% für die Auswertung 20 % für das pdf
                    self.fileCount += 1
                    if hasattr( logger, "progress"):
                        logger.progress( md["testId"],  40 + ( 40 / filesMax * self.fileCount ) )

            # gruppierung durchführen
            #
            ( df_group
                 .sort_values( [ 'gantry', 'collimator', 'check_subtag'] )
                 .groupby( [ "gantry", "collimator" ] ).apply( groupByGantryKolli )
            )

            #
            # Tabelle erzeugen
            #
            if len(data) < 1:
                result.append( self.pdf_error_result(
                    md, date=checkDate, group_len=len( result ),
                    msg='<b>Datenfehler</b>: keine Felder gefunden oder das offene Feld fehlt.'
                ) )
                return

            # pandas dataframe erstellen
            df = pd.DataFrame( data )
            df = df.sort_values( [ 'position', 'gantry', 'collimator'] )

            df["soll"] = df['position'].apply(lambda x: md["checkValues"][ str(x) ] if str(x) in md["checkValues"] else "" )
            df["diff"] = df['interleaf.mean'] - df["soll"]

            #
            # Abweichung ausrechnen und Passed setzen
            #
            check = [
                { "field": 'diff', 'tolerance':'diff' }
            ]
            acceptance = self.check_acceptance( df, md, check )

            #
            # Ergebnis in result merken
            #
            result.append( self.createResult( df, md, check,
                    df_group['AcquisitionDateTime'].iloc[0].strftime("%Y%m%d"),
                    len( result ), # bisherige Ergebnisse in result
                    acceptance
            ) )

            # zusätzliche Gantry/Kollimator spalte
            df["Gantry/Kollimator"] = df.apply(lambda x:'{0:.0f}/{1:.0f}'.format( x['gantry'], x['collimator']  ),axis=1)

            #
            # charts plotten
            #
            self.pdf.pandasPlot( df[df.position == -40], md["_chart_-40"],
                ylim=(0,0.5),
                grid=True,
                y='interleaf.mean',
                x='Gantry/Kollimator',
                label='position -40',
            )
            self.pdf.pandasPlot( df[df.position == 0], md["_chart_0"],
                grid=True,
                ylim=(0,0.5),
                y='interleaf.mean',
                x='Gantry/Kollimator',
                label='position 0',
            )
            self.pdf.pandasPlot( df[df.position == 40], md["_chart_40"],
                ylim=(0,0.5),
                grid=True,
                y='interleaf.mean',
                x='Gantry/Kollimator',
                label='position 40',
            )

            #
            # Tabelle anzeigen
            #
            self.pdf.pandas( df, md["_table"],
                attrs=md["_table_attrs"],
                fields=md["table_fields"]
            )

            #
            # tolerance anzeigen
            #
            text_values = {
                "f_warning": md.current.tolerance.diff.warning.get("f",""),
                "f_error": md.current.tolerance.diff.error.get("f","")
            }
            text = """<br>
                Warnung bei: <b style="position:absolute;left:25mm;">{f_warning}</b><br>
                Fehler bei: <b style="position:absolute;left:25mm;">{f_error}</b>
            """.format( **text_values ).replace("{value}", "Mean diff")
            self.pdf.text( text, md["_text"], attrs=md["_text_attrs"] )

            # Gesamt check
            self.pdf.resultIcon( acceptance )

        #
        # Sortiert nach check_subtag
        # Gruppiert nach day und SeriesNumber abarbeiten
        # wenn angegeben die Gruppierung aus der config verwenden (2019 sind die Aufnahmen von unterschiedlichen Tagen)
        #
        ( fileData
             .groupby( md["series_groupby"] )
             .apply( groupBySeries )
        )

        # abschließen pdfdaten und result zurückgeben
        return self.pdf.finish(), result

    def doJT_LeafSpeed( self, fileData ):
        """Jahrestest: (Lamellengeschwindigkeit)
        Messorte: Mean des kompletten Feldes (12x40)
        Verwendet/berechnet: (DR600 V1 - DR600 V1 OF) / DR600 V1 OF
        Geschwindigkeiten: V1, V2, V3

        Anzeigen:
            Tabelle mit Dosiswerten

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

        # metadata vorbereiten
        md = dict_merge( DotMap( {
            "manual": {
                "attrs": {"class":"layout-fill-width", "margin-bottom": "5mm"},
            },
            "field_count": 1,
            "_text": { "left":85, "top":220, "width" : 100 },
            "_table": { "left":0, "top":140, "width" : 80, "height" : 60},
            "_infobox" : { "left":40, "top":50, "width":100 },
            "_clip" : { "width":"80mm", "height":"30mm", "margin-left":"10mm", "margin-top":"5mm" },
            "_clipLegend" : { "margin-left":"10mm", "margin-top": "5mm" },
            "_chart": { "left":85, "top":140, "width" : 100, "height" : 60},
            "table_fields": [
                {'field': 'doserate', 'label':'Dosisleistung', 'format':'{0}'},
                {'field': 'gantry', 'label':'Gantry', 'format':'{0:.0f}' },
                {'field': 'collimator', 'label':'Kolli', 'format':'{0:.0f}' },
                {'field': 'speed', 'label':'Geschw.', 'format':'{0}'},
                {'field': 'delta', 'label':'Delta [%]', 'format':'{0:.1f}' },
                {'field': 'delta_passed', 'label':'Passed', 'style':  [('max-height', '10px'), ('vertical-align','top')] }
            ]
        } ), self.metadata )

        # gruppieren Doserate und Geschwindigkeit (V1, V2, V3)
        # Speed über doserate und MonitorEinheiten(MetersetExposure)
        # MLCPlanType=DynMLC Plan; IndexParameterType=MU
        # Radiation.TechniqueLabel = STATIC|SLIDING_WINDOW
        def groupBy( df_group ):
            """Datumsweise Auswertung
            """
            # das Datum vom ersten Datensatz verwenden
            checkDate = df_group['AcquisitionDateTime'].iloc[0].strftime("%d.%m.%Y")
            self.pdf.setContentName( checkDate )

            #
            # Anleitung
            #
            self.pdf.textFile( **md.manual )

            #
            # Infobox
            #   mit MLC Clip und Text
            #
            html = ''
            html += self.pdf.image( "qa/LeafSpeed.svg", attrs=md["_clip"], render=False)
            html += self.pdf.textFile("qa/LeafSpeed_Legend.md", attrs=md["_clipLegend"], render=False)

            self.pdf.html( html, md["_infobox"], { "class" : "infobox" })

            data = []
            # pro speed 
            # das offene Feld der jeweiligen Geschwindigkeit wird für alle Gantry- und Kolli-Winkel verwendet
            def groupBySpeed(df_speed):
                try:
                    # das offene Feld merken
                    df_base = df_speed.query("open == 'OF'").iloc[0]
                    self.fileCount += 1
                except:
                    # ein leeres df damit in checkFields geprüft wird
                    df_base = pd.DataFrame()
                    #logger.warning( "kein offenes Feld" )
 
                # alles notwendige da, erstmal nur df_base?
                errors = self.checkFields( md, df_base )
                if len(errors) > 0:
                    result.append( self.pdf_error_result(
                        md, date=checkDate, group_len=len( result ),
                        errors=errors
                    ) )
                    return

                # alle anderen durchgehen
                # alle Felder durchgehen
                for (idx, df_field) in df_speed.query("open != 'OF'").iterrows():


                    # alles notwendige da?
                    errors = self.checkFields( md, df_base, df_field, md["field_count"] )
                    if len(errors) > 0:
                        result.append( self.pdf_error_result(
                            md, date=checkDate, group_len=len( result ),
                            errors=errors
                        ) )
                        return

                    # die Bilder von den Felder mit gedrehtem Kollimator drehen
                    if df_field["collimator"] == 90:
                        dicomfile=df_field["dicom"]
                        arr=dicomfile.pixel_array
                        arr=np.rot90(arr, k=3)
                        dicomfile.PixelData=arr.tobytes()
                        df_field["dicom"]=dicomfile
                    if df_field["collimator"] == 270:
                        dicomfile=df_field["dicom"]
                        arr=dicomfile.pixel_array
                        arr=np.rot90(arr)
                        dicomfile.PixelData=arr.tobytes()
                        df_field["dicom"]=dicomfile

                    # es wurden keine Felder gefunden (checkFields fehler)
                    check = qa_mlc(
                        checkField=self.getFullData( df_field ),
                        baseField=self.getFullData( df_base ),
                        normalize="prozent"
                    )

                    if check.infos["collimator"] == 90:
                        check.image.rot90( n=3 )
                    elif check.infos["collimator"] == 270:
                        check.image.rot90( n=1 )

                    # Daten merken
                    data.append( {
                        "doserate" : check.infos["doserate"],
                        "speed" : check.infos["speed"],
                        "gantry" : check.infos["gantry"],
                        "collimator" : check.infos["collimator"],
                        "AcquisitionDateTime" : check.infos["AcquisitionDateTime"],
                        "delta" : check.image.getFieldRoi().mean() * 100
                    })

                    # progress pro file stimmt nicht immer genau (baseimage)
                    # 40% für die dicom daten 40% für die Auswertung 20 % für das pdf
                    self.fileCount += 1
                    if hasattr( logger, "progress"):
                        logger.progress( md["testId"],  40 + ( 40 / filesMax * self.fileCount ) )

            # alle doserate speed Arten durch gehen
            ( df_group
                 .sort_values(by=[ "gantry", "collimator", "doserate", "speed", "AcquisitionDateTime"])
                 .groupby( [ "speed" ] )
                 .apply( groupBySpeed )
            )

            if len( data ) < 1:
                result.append( self.pdf_error_result(
                    md, date=checkDate, group_len=len( result ),
                    msg='<b>Datenfehler</b>: keine Felder gefunden oder das offene Feld fehlt.',
                    pos={ "top":150 }
                ) )
                return

            # dataframe erstellen
            df = pd.DataFrame( data )
            df.sort_values(['doserate', 'gantry', 'collimator', 'speed'], inplace=True)

            #
            # Abweichung ausrechnen und Passed setzen
            #
            check = [
                { "field": 'delta', 'tolerance':'default' }
            ]
            acceptance = self.check_acceptance( df, md, check )

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
            self.pdf.pandas( df, md["_table"],
                #attrs={"class":"layout-40-width", "margin-top": "205mm"},
                fields=md["table_fields"]
            )

            #
            # chart
            #
            if len( data ) > 24:
                result.append( self.pdf_error_result(
                    md, date=checkDate, group_len=len( result ),
                    msg='<b>Datenfehler</b>: zu viele Felder pro Doserate, Art, Geschw. gefunden. Chart kann nicht angezeigt werden',
                    pos={ "top":150 }
                ) )
            else:
                # plot anlegen
                plot = plotClass( )
                fig, ax = plot.initPlot( md["_chart"] , True )

                # data frame gruppieren und mit neuem index versehen
                df_chart = df.set_index([ 'gantry', 'collimator', 'speed' ])['delta'].unstack()
                # als bar plot ausgeben
                df_chart.plot( ax=ax, kind='bar', rot=0)

                # limits legende und grid
                ax.set_ylim( [-2.0, 2.0] )
                ax.grid( )
                ax.legend( )

                plt.tight_layout(pad=0.4, w_pad=0.5, h_pad=1.0)

                # chart im PDF anzeigen
                self.pdf.image( plot.getPlot(), md["_chart"] )

            # toleranz anzeigen
            text_values = {
                "f_warning": md.current.tolerance.default.warning.get("f",""),
                "f_error": md.current.tolerance.default.error.get("f","")
            }
            text = """<br>
                Warnung bei: <b style="position:absolute;left:25mm;">{f_warning}</b><br>
                Fehler bei: <b style="position:absolute;left:25mm;">{f_error}</b>
            """.format( **text_values ).replace("{value}", "Delta")
            self.pdf.text( text, md["_text"] )


            # Gesamt check - das schlechteste aus der tabelle
            self.pdf.resultIcon( acceptance )

        # zusätzliche Felder für speed und open anlegen
        #
        def splitSpeed(value, **args):
            pos = args.get("pos", 1)
            s = value.split()
            if len(s) > pos:
                return s[pos]
            else:
                return ""

        # speed und open aus RadiationId erzeugen
        fileData["speed"] = fileData["RadiationId"].apply( splitSpeed, pos=1 )
        fileData["open"] = fileData["RadiationId"].apply( splitSpeed, pos=2 )

        #
        # Gruppiert nach day abarbeiten
        #
        (fileData
             .groupby( [ 'day' ] )
             .apply( groupBy )
        )
        # abschließen pdfdaten und result zurückgeben
        return self.pdf.finish(), result


    def doMT_LeafSpeed(self, fileData ):
        """Monatstest Leafspeed
        Wie JT_LeafSpeed aber nur bei Gantry 0 sowie mit und ohne Gating

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

        # metadata vorbereiten
        md = dict_merge( DotMap( {
            "manual": {
                "attrs": {"class":"layout-fill-width", "margin-bottom": "5mm"},
            },
            "field_count" : 1,
            "_infobox" : { "left":40, "top":50, "width":100 },
            "_clip" : { "width":"80mm", "height":"30mm", "margin-left":"10mm", "margin-top":"5mm" },
            "_clipLegend" : { "margin-left":"10mm", "margin-top": "5mm" },

            "_table": { "left":0, "top":140, "width" : 80, "height" : 60},
            "_chart": { "left":85, "top":140, "width" : 90, "height" : 60},
            "_text": { "left":0, "top":220, "width" : 100 },
            "table_fields" : [
                {'field': 'doserate', 'label':'Dosisleistung', 'format':'{0}'},
                {'field': 'collimator', 'label':'Kolli', 'format':'{0:.0f}' },
                {'field': 'gating', 'label':'Art', 'format':'{0}' },
                {'field': 'speed', 'label':'Geschw.', 'format':'{0}'},
                {'field': 'delta', 'label':'Delta [%]', 'format':'{0:.1f}' },
                {'field': 'delta_passed', 'label':'Passed' }
            ]
        } ), self.metadata )

        # gruppieren Doserate und Geschwindigkeit (V1, V2, V3)
        # Speed über doserate und MonitorEinheiten(MetersetExposure)
        # MLCPlanType=DynMLC Plan; IndexParameterType=MU
        # Radiation.TechniqueLabel = STATIC|SLIDING_WINDOW
        # subTags = |Gating

        def groupBySeries( df_group ):
            """Datumsweise Auswertung
            """
            # das Datum vom ersten Datensatz verwenden
            checkDate = df_group['AcquisitionDateTime'].iloc[0].strftime("%d.%m.%Y")
            self.pdf.setContentName( checkDate )

            #
            # Anleitung
            #
            self.pdf.textFile( **md.manual )

            #
            # Infobox
            #   mit MLC Clip und Text
            #
            html = ''
            html += self.pdf.image( "qa/LeafSpeed.svg", attrs=md["_clip"], render=False)
            html += self.pdf.textFile("qa/LeafSpeed_Legend.md", attrs=md["_clipLegend"], render=False)

            self.pdf.html( html, md["_infobox"], { "class" : "infobox" })

            data = []
            # pro speed und check_subtag
            # das offene Feld der jeweiligen Geschwindigkeit wird für Gating und MLC verwendet
            def groupBySpeed(df_speed):
                try:
                    # das offene Feld merken
                    df_base = df_speed.query("open == 'OF'").iloc[0]
                    self.fileCount += 1
                except:
                    # ein leeres df damit in checkFields geprüft wird
                    df_base = pd.DataFrame()
                    #logger.warning( "doMT_LeafSpeed: kein offenes Feld" )


                # alles notwendige da, erstmal nur df_base?
                errors = self.checkFields( md, df_base )
                if len(errors) > 0:
                    result.append( self.pdf_error_result(
                        md, date=checkDate, group_len=len( result ),
                        errors=errors
                    ) )
                    return
                '''
                if not self.checkFields( md, df_base ):
                    return
                    #return
                '''

                # alle anderen durchgehen
                # alle Felder durchgehen
                for (idx, df_field) in df_speed.query("open != 'OF'").iterrows():
                    gating=""

                    # alles notwendige da?
                    errors = self.checkFields( md, df_base, df_field, md["field_count"] )
                    if len(errors) > 0:
                        result.append( self.pdf_error_result(
                            md, date=checkDate, group_len=len( result ),
                            errors=errors
                        ) )
                        return
                    '''
                    # prüfung der benötigten Felder
                    if not self.checkFields( md, df_base, df_field, 1 ):
                        return
                    '''

                    check = qa_mlc(
                        checkField=self.getFullData( df_field ),
                        baseField=self.getFullData( df_base ),
                        normalize="prozent"
                    )

                    if check.infos["check_subtag"] == "gating":
                        gating = "gating"

                    # Daten merken
                    data.append( {
                        "doserate" : check.infos["doserate"],
                        "gating" : gating,
                        "speed" : check.infos["speed"],
                        "gantry" : check.infos["gantry"],
                        "collimator" : check.infos["collimator"],
                        "AcquisitionDateTime" : check.infos["AcquisitionDateTime"],
                        "delta" : check.image.getFieldRoi().mean() * 100
                    })

                    # progress pro file stimmt nicht immer genau (baseimage)
                    # 40% für die dicom daten 40% für die Auswertung 20 % für das pdf
                    self.fileCount += 1
                    if hasattr( logger, "progress"):
                        logger.progress( md["testId"],  40 + ( 40 / filesMax * self.fileCount ) )


            # alle doserate speed Arten durch gehen
            ( df_group
                 .sort_values(by=[ "gantry", "collimator", "doserate", "speed", "AcquisitionDateTime"])
                 .groupby( [ "gantry", "collimator", "doserate", "speed" ] )
                 .apply( groupBySpeed )
            )

            # es wurden keine Felder gefunden (checkFields fehler)
            if len( data ) < 1:
                result.append( self.pdf_error_result(
                    md, date=checkDate, group_len=len( result ),
                    msg='<b>Datenfehler</b>: keine Felder gefunden oder das offene Feld fehlt.',
                    area={ "top":130 }
                ) )
                return

            # dataframe erstellen
            df = pd.DataFrame( data )
            df.sort_values(['doserate', 'collimator', 'gating', 'speed'], inplace=True)

            #
            # Abweichung ausrechnen und Passed setzen
            #
            check = [
                { "field": 'delta', 'tolerance':'default' }
            ]
            acceptance = self.check_acceptance( df, md, check )

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
            self.pdf.pandas( df, md["_table"],
                #attrs={"class":"layout-40-width", "margin-top": "205mm"},
                fields=md["table_fields"]
            )


            #
            # chart
            #
            if len( data ) > 18:
                result.append( self.pdf_error_result(
                    md, date=checkDate, group_len=len( result ),
                    msg='<b>Datenfehler</b>:<br>Zu viele Felder pro Doserate, Art, Geschw. gefunden. Chart kann nicht angezeigt werden.',
                    area=md["_chart"] 
                ) )
                md["_text"]["left"] = md["_chart"]["left"]
            else:
                # plot anlegen
                plot = plotClass( )
                fig, ax = plot.initPlot( md["_chart"] , True )

                # data frame gruppieren und mit neuem index versehen
                df_chart = df.set_index([ 'doserate', 'gating', 'speed' ])['delta'].unstack()
                # als bar plot ausgeben
                df_chart.plot( ax=ax, kind='bar', rot=0)

                # limits legende und grid
                ax.set_ylim( [-2.0, 2.0] )
                ax.grid( )
                ax.legend( )

                plt.tight_layout(pad=0.4, w_pad=0.5, h_pad=1.0)

                # chart im PDF anzeigen
                self.pdf.image( plot.getPlot(), md["_chart"] )

            # toleranz anzeigen
            text_values = {
                "f_warning": md.current.tolerance.default.warning.get("f",""),
                "f_error": md.current.tolerance.default.error.get("f","")
            }
            text = """<br>
                Warnung bei: <b style="position:absolute;left:25mm;">{f_warning}</b><br>
                Fehler bei: <b style="position:absolute;left:25mm;">{f_error}</b>
            """.format( **text_values ).replace("{value}", "Delta")
            self.pdf.text( text, md["_text"] )


            # Gesamt check - das schlechteste aus der tabelle
            self.pdf.resultIcon( acceptance )

        # zusätzliche Felder für speed und open anlegen
        #
        def splitSpeed(value, **args):
            pos = args.get("pos", 1)
            s = value.split()
            if len(s) > pos:
                return s[pos]
            else:
                return ""

        # speed und open aus RadiationId erzeugen
        fileData["speed"] = fileData["RadiationId"].apply( splitSpeed, pos=1 )
        fileData["open"] = fileData["RadiationId"].apply( splitSpeed, pos=2 )

        #
        # Gruppiert nach day abarbeiten
        #
        (fileData
             .groupby( [ 'day' ] )
             .apply( groupBySeries )
        )
        # abschließen pdfdaten und result zurückgeben
        return self.pdf.finish(), result


    def _doLamellenpositioniergenauigkeit(self, fileData, md ):
        """Erstellen der Lamellenpositioniergenauigkeit für die Tests MT_8_02_1_2 und MT_8_02_3

        Parameters
        ----------
        fileData : pandas.DataFrame

        md: dotmap
            metadata
        
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
        # used on progress
        filesMax=len( fileData )
        self.fileCount = 0
        # holds evaluation results
        result=[]

        # Auszuwertende Leaf Nummern
        leaf_from = md.options.leafs.get("from", 1)
        leaf_to = md.options.leafs.get("to", 60)
        leafs = np.arange( leaf_from, leaf_to + 1, 1 )

        def evaluate( df_group ):
            """Evaluate grouped Fields.

            create PDF output and fills result

            Parameters
            ----------
            df_group : pandas Dataframe

            """
            # das Datum vom ersten Datensatz verwenden
            checkDate = df_group['AcquisitionDateTime'].iloc[0].strftime("%d.%m.%Y")
            self.pdf.setContentName( checkDate )

            #
            # Anleitung
            #
            self.pdf.textFile( **md.manual )

            # array für die chartdaten bereitstellen
            fwxm_plot = {}
            shift_plot = {}

            # für jeden Datensatz
            leafData = []

            i = 0
            for info in df_group.itertuples():
                i += 1
                # mlc Prüfung aktivieren
                check = qa_mlc( self.getFullData( info._asdict() ) )

                # leafPair Transmissionen suchen und merken
                data = check.FWHM_findLeafs( leafs=leafs, lfd=i, variante=md.current["testTag"] )
                # Daten für die Tabelle merken
                leafData.append( data )

                #Daten für den Boxplot merken
                fwxm_plot[i] = data["fwxm.data"]
                shift_plot[i] = data["shift.data"]

                # LeafError Chart erzeugen
                img = check.FWHM_plot_error( data, md["_leafPlot"], plotTitle=md["plotTitle"], leaf_from=leaf_from )
                self.pdf.image(img, md["_leafPlot"] )

                # progress pro file stimmt nicht immer genau (baseimage)
                # 40% für die dicom daten 40% für die Auswertung 20 % für das pdf
                self.fileCount += 1
                if hasattr( logger, "progress"):
                    logger.progress( md["testId"],  40 + ( 40 / filesMax * self.fileCount ) )

            #
            # chart leafError als BoxPlot
            #
            img = check.FWHM_plot_errorBox( {"fwxm.data": fwxm_plot, "shift.data":shift_plot }, md["_boxPlot"] )
            self.pdf.image(img, md["_boxPlot"] )

            if len(leafData) < 1:
                result.append( self.pdf_error_result(
                    md, date=checkDate, group_len=len( result ),
                    msg='<b>Datenfehler</b>: keine Felder gefunden.'
                ) )
                return

            # dataFrame erzeugen und passed spalten einfügen
            df = pd.DataFrame( leafData )

            #
            # Abweichung ausrechnen und Passed setzen
            #
            check = [
                { "field": 'fwxm.min', 'tolerance':'FWXMMean' },
                { "field": 'fwxm.mean', 'tolerance':'FWXMMean' },
                { "field": 'fwxm.max', 'tolerance':'FWXMMean' },
                { "field": 'shift.min', 'tolerance':'ShiftMean' },
                { "field": 'shift.mean', 'tolerance':'ShiftMean' },
                { "field": 'shift.max', 'tolerance':'ShiftMean' }
            ]
            acceptance = self.check_acceptance( df, md, check )

            # im Dataframe die Abweichungen nur in einer Spalte für FWXM und Shift anzeigen
            df["fwxm.passed"] = df["fwxm.min_passed"] + df["fwxm.mean_passed"] + df["fwxm.max_passed"]
            df["shift.passed"] = df["shift.min_passed"] + df["shift.mean_passed"] + df["shift.max_passed"]
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
                attrs={"class":"layout-fill-width", "margin-top": "5mm"},
                fields=md["table_fields"]
            )

            # Formeln anzeigen
            text_values = {
                "fwxm warning" : md.current.tolerance.FWXMMean.warning.get("f","").replace("{value}", "FWXM mean"),
                "fwxm_error": md.current.tolerance.FWXMMean.error.get("f","").replace("{value}", "FWXM mean"),
                "shift_warning" : md.current.tolerance.ShiftMean.warning.get("f","").replace("{value}", "Shift mean"),
                "shift_error": md.current.tolerance.ShiftMean.error.get("f","").replace("{value}", "Shift mean")
            }
            text = """
                Warnung bei: <b style="position:absolute;left:25mm;">{fwxm warning}</b>
                <b style="position:absolute;left:90mm;">{shift_warning}</b><br>
                Fehler bei: <b style="position:absolute;left:25mm;">{fwxm_error}</b>
                <b style="position:absolute;left:90mm;">{shift_error}</b>
            """.format( **text_values )
            self.pdf.text( text, replaceNewLine=False, attrs={ "margin-top": "5mm"} )

            # Gesamt check - das schlechteste aus beiden tabelle Spalten
            #minBoth = df[ [ "fwxm.acceptance", "shift.acceptance" ] ].min(axis=None)
            #self.pdf.resultIcon( minBoth.min() )
            self.pdf.resultIcon( acceptance )


        #
        # Gruppiert nach SeriesNumber abarbeiten
        #
        fileData.sort_values(md["series_sort_values"]).groupby( md["series_groupby"] ).apply( evaluate )
        # abschließen pdfdaten und result zurückgeben
        return self.pdf.finish(), result


    def doMT_8_02_1_2(self, fileData ):
        """Lamellenpositioniergenauigkeit
        FWHM sucht den Peak für alle Leaves,
        Position des Peaks entspricht Position der Leaves,

        Breite des Peaks gibt Abstand der gegenüberliegenden Leaf-Paare.

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

        # metadata defaults vorbereiten
        md = dict_merge( DotMap( {
            "series_sort_values" :  ["gantry", "collimator"],
            "series_groupby" :  ['day', 'SeriesNumber'],
            "manual": {
                "attrs": {"class":"layout-fill-width"},
            },
            "_leafPlot" : { "width" : 45, "height" : 45},
            "_boxPlot" : { "width" : 90, "height" : 45},
            "plotTitle" : "lfd:{lfd:d} G:{gantry:.0f} K:{collimator:.0f}",
            "table_fields" : [
                {'field': 'lfd', 'label':'lfd', 'format':'{0:d}' },
                {'field': 'gantry', 'label':'Gantry', 'format':'{0:.0f}' },
                {'field': 'collimator', 'label': 'Kollimator', 'format':'{0:.0f}' },
                {'field': 'fwxm.min', 'label':'FWXM<br>min<br>[mm]', 'format':'{0:.3f}' },
                {'field': 'fwxm.mean', 'label':'FWXM<br>mean<br>[mm]', 'format':'{0:.3f}' },
                {'field': 'fwxm.max', 'label':'FWXM<br>max<br>[mm]', 'format':'{0:.3f}' },
                {'field': 'fwxm.passed', 'label':'FWXM<br>passed' },
                {'field': 'shift.min', 'label':'Shift<br>min<br>[mm]', 'format':'{0:.3f}' },
                {'field': 'shift.mean', 'label':'Shift<br>mean<br>[mm]', 'format':'{0:.3f}' },
                {'field': 'shift.max', 'label':'Shift<br>max<br>[mm]', 'format':'{0:.3f}' },
                {'field': 'shift.passed', 'label':'Shift<br>passed' },
            ],
            "options":{
                "leafs" : {
                    "from": 1,
                    "to" : 60
                }
            }
        }), self.metadata )

        return self._doLamellenpositioniergenauigkeit(fileData, md)

    def doMT_8_02_3(self, fileData ):
        """Lamellenpositioniergenauigkeit
        Hysterese bei großem/kleinen Feld

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

        # metadata defaults vorbereiten
        # und mit den Angaben aus config (info) ergänzen / überschreiben
        md = dict_merge( DotMap( {
            "series_sort_values" : ['day'],
            "series_groupby": ["day", "SeriesNumber"],
            "manual": {
                "attrs": {"class":"layout-fill-width"},
            },
            "_leafPlot" : { "width" : 45, "height" : 45},
            "_boxPlot" : { "width" : 90, "height" : 45},
            "plotTitle" : "lfd:{lfd} - {Richtung}",
            "table_fields" : [
                {'field': 'lfd', 'label':'lfd', 'format':'{0:d}' },
                {'field': 'Richtung', 'label':'Richtung', 'format':'{0}' },
                {'field': 'Datum', 'label':'Datum', 'format':'{0:%d.%m.%Y %H:%M:%S}' },
                {'field': 'fwxm.min', 'label':'FWXM<br>min<br>[mm]', 'format':'{0:.3f}' },
                {'field': 'fwxm.mean', 'label':'FWXM<br>mean<br>[mm]', 'format':'{0:.3f}' },
                {'field': 'fwxm.max', 'label':'FWXM<br>max<br>[mm]', 'format':'{0:.3f}' },
                {'field': 'fwxm.passed', 'label':'FWXM<br>passed' },
                {'field': 'shift.min', 'label':'Shift<br>min<br>[mm]', 'format':'{0:.3f}' },
                {'field': 'shift.mean', 'label':'Shift<br>mean<br>[mm]', 'format':'{0:.3f}' },
                {'field': 'shift.max', 'label':'Shift<br>max<br>[mm]', 'format':'{0:.3f}' },
                {'field': 'shift.passed', 'label':'Shift<br>passed' },
            ],

            "options":{
                "leafs" : {
                    "from": 1,
                    "to" : 60
                }
            }
        }), self.metadata )
        return self._doLamellenpositioniergenauigkeit(fileData, md)

    def _doMLC_VMAT( self, fileData, overrideMD={}, passedOn=True, withOffsets=False ):
        """VMAT MLC-PicketFence Auswertung

        In tolerance value und nicht Formel angeben, da analyze die Angaben benötigt
    
        Parameters
        ----------
        fileData : pandas.DataFrame

        overrideMD: dict
            metadata 

        passedOn : bool
            wann ist der Test OK bei VMAT_1_2 ist er bei false OK

        withOffsets: bool
            offsets Tabelle drucken
        
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
        md = dict_merge( DotMap( {
            "manual": {
                "attrs": {"class":"layout-fill-width"},
            },
            "_chartSize" : { "width" : 180, "height" : 110},
            "_table" : { "top" : 165 },
            "table_fields_offsets" : [
                {'field': 'Kennung', 'label':'Kennung', 'format':'{0}', 'style': [('text-align', 'left')] },
                {'field': 'gantry', 'label':'Gantry', 'format':'{0:1.0f}' },
                {'field': 'offsets', 'label':'Picket offsets from CAX [mm]' }
            ],
            "table_fields" : [
                {'field': 'Kennung', 'label':'Kennung', 'format':'{0}', 'style': [('text-align', 'left')] },
                {'field': 'gantry', 'label':'Gantry', 'format':'{0:.0f}' },
                {'field': 'collimator', 'label':'Kollimator', 'format':'{0:.0f}' },
                {'field': 'pass_pct', 'label':'Passed %', 'format':'{0:2.1f}' },

                {'field': 'mean_spacing', 'label':'Mean spacing [mm]', 'format':'{0:2.1f}' },
                {'field': 'mean_spacing_passed', 'label':'Mean spacing Passed' },

                {'field': 'abs_mean_error', 'label':'Mean Error [mm]', 'format':'{0:2.3f}' },
                {'field': 'abs_mean_error_passed', 'label':'Mean Error Passed' },

                {'field': 'max_from_mean', 'label':'Max von Mean Error [mm]', 'format':'{0:2.3f}' },
                {'field': 'max_from_mean_passed', 'label':'Max von Mean Error Passed' },
                {'field': 'max_from_mean_leaf', 'label':'Max von Mean Error<br>bei Leaf', 'format':'{0:d}' },

            ],
            "field": { "X1":-100, "X2": 100, "Y1": -100, "Y2":100, "xStep":50, "yStep":50, "border": 10 },
            "mlc_type": "Millennium",
            "crop_field":  { "X1":-105, "X2": 105, "Y1": -105, "Y2":105 },
            "analyze": {
                "required_prominence" : 0.01
            }
            
        } ), self.metadata )
        md.update( overrideMD )

        # Analyse Grenzen festlegen
        warning = md.current.tolerance.MaxFromMeanError.warning.get("value", 0.3)
        error = md.current.tolerance.MaxFromMeanError.error.get("value", 0.5)

        #
        # Auswertungs text vorbereiten
        #
        energy_tolerance = md.current.tolerance

        text_values = {
            "MeanSpacing_warning": md.current.tolerance.MeanSpacing.warning.get("f","").replace("{value}", "Mean spacing"),
            "MeanSpacing_error": md.current.tolerance.MeanSpacing.error.get("f","").replace("{value}", "Mean spacing"),
            "MeanError_warning": md.current.tolerance.MeanError.warning.get("f","").replace("{value}", "Mean Error"),
            "MeanError_error": md.current.tolerance.MeanError.error.get("f","").replace("{value}", "Mean Error"),
            "MaxFromMeanError_warning": md.current.tolerance.MaxFromMeanError.warning.get("f","").replace("{value}", "Max v. Mean Error"),
            "MaxFromMeanError_error": md.current.tolerance.MaxFromMeanError.error.get("f","").replace("{value}", "Max v. Mean Error")
        }

        text = """
            Warnung bei:<b style="position:absolute;left:25mm;">{MeanSpacing_warning}</b>
            <b style="position:absolute;left:75mm;">{MeanError_warning}</b>
            <b style="position:absolute;left:125mm;">{MaxFromMeanError_warning}</b><br>
            Fehler bei:<b style="position:absolute;left:25mm;">{MeanSpacing_error}</b>
            <b style="position:absolute;left:75mm;">{MeanError_error}</b>
            <b style="position:absolute;left:125mm;">{MaxFromMeanError_error}</b>
        """

        if not passedOn:
            text += "<br>Der Test ist erfüllt wenn ein Fehler <b>{MaxFromMeanError_error}</b> vorliegt."

        def groupBySeries( df_group ):
            """Datumsweise Auswertung und PDF Ausgabe

            """

            # das Datum vom ersten Datensatz verwenden
            checkDate = df_group['AcquisitionDateTime'].iloc[0].strftime("%d.%m.%Y")
            self.pdf.setContentName( checkDate )

            #
            # Anleitung
            #
            self.pdf.textFile( **md.manual )

            data=[]
            # für jeden Datensatz (sollte eigentlich nur einer pro Tag sein)
            for info in df_group.itertuples():
                # mlc Prüfung aktivieren
                check = qa_mlc( self.getFullData( info._asdict() ), mlc=md.mlc_type )
                # image Flip oben unten durchführen da sonst die Darstellung falsch ist
                check.image.flipud()
                # Feld vorher beschneiden
                check.image.cropField( md.crop_field )
                
                '''
                default Parameter:
                sag_adjustment: float | int = 0,
                orientation: Orientation | str | None = None,
                invert: bool = False,
                leaf_analysis_width_ratio: float = 0.4
                picket_spacing: float | None = None
                height_threshold: float = 0.5
                edge_threshold: float = 1.5
                peak_sort: str = "peak_heights"
                required_prominence: float = 0.2
                '''
                # und picketfence analyse durchführen
                try:
                    check.analyze( 
                        tolerance=error, 
                        action_tolerance=warning, 
                    #    orientation=Orientation.LEFT_RIGHT, 
                        required_prominence=md.analyze.required_prominence, # 0.02, # 0.05
                    #    height_threshold=0.5, 
                        edge_threshold=1.5, 
                        invert=False 
                    )
                except ValueError as value_error:
                    logger.warning( "_doMLC_VMAT analyze ValueError: {}.\n{}{:02d} - {} - {} - {}".format( value_error, md.current.year, md.current.month, md.current.unit, md.current.energy,  md.current.testTag) )
                    result.append( self.pdf_error_result(
                        md, date=checkDate, group_len=len( result ),
                        msg= '<b>Analyze Error</b>: keine Pickets gefunden. "{}"'.format(value_error)
                    ) )

                results = check.picketfence_results()
                results["Kennung"] = results["Kennung"]
                # Grafiken nur für Felder mit Kolli 0° anzeigen
                if hasattr(check, "pickets") and results["collimator"] == 0:
                    # Bild mit analyse anzeigen
                    img = check.picketfence_plotImage( metadata=md )
                    self.pdf.image(img, md["_chartSize"] )

                # daten merken
                data.append( results )

                # progress pro file stimmt nicht immer genau (baseimage)
                # 40% für die dicom daten 40% für die Auswertung 20 % für das pdf
                self.fileCount += 1
                if hasattr( logger, "progress"):
                    logger.progress( md["testId"],  40 + ( 40 / filesMax * self.fileCount ) )

            if len(data) < 1:
                result.append( self.pdf_error_result(
                    md, date=checkDate, group_len=len( result ),
                    msg='<b>Datenfehler</b>: keine Felder gefunden.'
                ) )
                return

            # pandas dataframe erstellen
            df = pd.DataFrame( data )

            #
            # Abweichung ausrechnen und Passed setzen
            #
            check = [
                { "field": 'mean_spacing', 'tolerance':'MeanSpacing' },
                { "field": 'abs_mean_error', 'tolerance':'MeanError' },
                { "field": 'max_from_mean', 'tolerance':'MaxFromMeanError' }
            ]
            acceptance = self.check_acceptance( df, md, check )

            #
            # Gesamt check
            #   das schlechteste aus allen Auswertespalten Spalten
            #
            if not passedOn and acceptance == 1:
                # bei passed on ist ein Fehler OK
                acceptance = 5


            #
            # Ergebnis in result merken
            #
            result.append( self.createResult( df, md, check,
                    df_group['AcquisitionDateTime'].iloc[0].strftime("%Y%m%d"),
                    len( result ), # bisherige Ergebnisse in result
                    acceptance
            ) )

            #
            # ggf. offsets Tabelle erzeugen
            #
            if withOffsets:
                self.pdf.pandas( df,
                    attrs={"class":"layout-fill-width", "margin-top": "3mm"},
                    fields=md["table_fields_offsets"]
                )

            #
            # result Tabelle erzeugen
            #
            self.pdf.pandas( df,
                attrs={"class":"layout-fill-width", "margin-top": "3mm"},
                fields=md["table_fields"]
            )

            #
            # Toleranztext anzeigen
            #
            self.pdf.text(
                text.format( **text_values ),
                replaceNewLine=False,
                attrs={"class":"layout-fill-width", "margin-top": "3mm"}
            )

            #
            #   das schlechteste aus allen Auswertespalten Spalten
            #
            self.pdf.resultIcon( acceptance )

        #
        # Gruppiert nach Tag und SeriesNumber abarbeiten
        #
        fileData.sort_values( by=["gantry", "collimator"] ).groupby( [ 'day', 'SeriesNumber' ] ).apply( groupBySeries )

        # abschließen pdfdaten und result zurückgeben
        return self.pdf.finish(), result

    def doMT_8_02_4(self, fileData ):
        """Lamellenpositioniergenauigkeit
        Picket Fence Test 1 mm Schlitzbreite,

        Plan/Feld:
            Monatstest/MLC 4 neu

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

        md = {
            "_imgSize" : {"width" : 45, "height" : 55},
            "_imgField": {"border": 10 },
            "_chartSize" : { "width" : 90, "height" : 55}
        }
        return self._doMLC_VMAT( fileData, overrideMD=md, withOffsets=False )


    def doMT_VMAT_0_2( self, fileData ):
        """PicketFence statisch eines 80x100 großen Feldes
        Auswertung wie in VMAT 1.1 und 1.2 Ergebnisse in einer Tabelle
        Toleranz Angaben in der Config mit value, da value Werte für analyze benötigt werden
        
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
        md = {
            "_imgSize" : {"width" : 45, "height" : 55},
            "_imgField": {"border": 10 },
            "_chartSize" : { "width" : 90, "height" : 55}
        }
        return self._doMLC_VMAT( fileData, overrideMD=md, withOffsets=True )

    def doMT_VMAT_1_1( self, fileData ):
        """PicketFence mit rot

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

        return self._doMLC_VMAT( fileData )

    def doMT_VMAT_1_2( self, fileData ):
        """PicketFence mit rot und absichtlichen Fehler

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

        return self._doMLC_VMAT( fileData, passedOn=False )


    def doJT_10_3_1( self, fileData ):
        """Jahrestest: 10.3.1  ( )
        Breite des peaks bei 50% peakhöhe für jedes Leafpaar
        Abstand bei FWHM für alle Leafpaare

        - d-4: Bilder vom leafGAP Feld tips_0_0 verwenden (tips)
        - d-6:
        - d-7:
        - d-8:

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
        md = dict_merge( DotMap( {
            "manual": {
                "attrs": {"class":"layout-fill-width", "margin-bottom": "5mm"},
            },
            "imgSize" : {"width" : 100, "height" : 100},
            "plotImage_pdf": {
                "area" : { "left":40, "top":15, "width" : 100, "height":100  }
            },
            
            "_tableA": { "left":25, "top":110, "width" : 50 },
            "_tableB": { "left":110, "top":110, "width" : 50 },
            "table_fields" : [
                {'field': 'leaf', 'label':'Leaf', 'format':'{0:01.0f}' },
                {'field': 'position', 'label':'Position', 'format':'{0:01.1f}' },
                {'field': 'value', 'label':'50%', 'format':'{0:01.3f}' },
                {'field': 'value_passed', 'label':'Passed' }
            ],
            "tolerance_pdf": { 
                "area" : { "top": 85, "width" : 50 }
            },
            "tolerance_field": "value",
            "evaluation_replaces": { "value": "50%" }
        } ), self.metadata )

        # Auswertepositionen (Mitte der Leafs) festlegen
        fl1 = np.arange(-195, -100, 10 )
        hl =  np.arange(-97.5, 100, 5 )
        fl2 = np.arange(105, 200, 10 )
        checkPositions = np.concatenate( ( fl1, hl, fl2) )

        def groupBySeries( df_group ):
            """Datumsweise Auswertung
            """

            # alle Felder durchgehen auch mehrere pro tag sind möglich
            for (idx, info) in df_group.iterrows():

                # das Datum vom ersten Datensatz verwenden
                self.pdf.setContentName( info['AcquisitionDateTime'].strftime("%d.%m.%Y") )

                #
                # Anleitung
                #
                self.pdf.textFile( **md.manual )

                # Auswertung starten
                check = qa_mlc( self.getFullData( info ) )

                # alle check positionen prüfen
                data ={}
                i = 0
                for p in checkPositions:
                    i += 1
                    profile = FWXMProfilePhysical( 
                        check.image.array[ check.image.mm2dots_Y( p ) ],
                        fwxm_height=50,
                        dpmm=check.image.dpmm
                    )

                    # daten zusammenstellen
                    data[ i ] = {
                        "leaf" : i,
                        "position" :  p,
                        "value" : (profile.field_width_px / check.image.dpmm / 2)
                    }

                #
                # Bild anzeigen
                #
                img = check.image.plotImage(  )
                self.pdf.image(img, **md.plotImage_pdf )

                # pandas dataframe erstellen
                #
                # transpose um x und y zu vertauschen
                evaluation_df = pd.DataFrame( data ).T
                
                data_frame, text, acceptance = self.evaluationCalculate( evaluation_df, md, [], "value" )
        
                # erste Tabelle bis Leaf 30
                self.pdf.pandas( data_frame[:30],
                    area=md["_tableA"],
                    attrs={"class":"layout-fill-width", "margin-top": "5mm"},
                    fields=md["table_fields"]
                )
                # zweite Tabelle ab Leaf 31
                self.pdf.pandas( data_frame[30:],
                    area=md["_tableB"],
                    attrs={"class":"layout-fill-width", "margin-top": "5mm"},
                    fields=md["table_fields"]
                )
    
                self.pdf.text( text, **md.tolerance_pdf )
                self.pdf.resultIcon( acceptance )

                # progress pro file stimmt nicht immer genau (baseimage)
                # 40% für die dicom daten 40% für die Auswertung 20 % für das pdf
                self.fileCount += 1
                if hasattr( logger, "progress"):
                    logger.progress( md["testId"],  40 + ( 40 / filesMax * self.fileCount ) )

        #
        # Gruppiert nach Tag und SeriesNumber abarbeiten
        #
        series = fileData.groupby( [ 'day', 'SeriesNumber' ] )

        series.apply( groupBySeries )
        # abschließen pdfdaten und result zurückgeben
        return self.pdf.finish(), result
