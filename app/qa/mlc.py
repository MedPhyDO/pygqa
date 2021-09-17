# -*- coding: utf-8 -*-

__author__ = "R. Bauer"
__copyright__ = "MedPhyDO - Machbarkeitsstudien des Instituts für Medizinische Strahlenphysik und Strahlenschutz am Klinikum Dortmund im Rahmen von Bachelor und Masterarbeiten an der TU-Dortmund / FH-Dortmund"
__credits__ = ["R.Bauer", "K.Loot"]
__license__ = "MIT"
__version__ = "0.1.2"
__status__ = "Prototype"

from pylinac.picketfence import PFDicomImage, PicketFence, Settings, Overlay, UP_DOWN
from mpl_toolkits.axes_grid1 import make_axes_locatable

from app.base import ispBase
from app.image import DicomImage
from app.check import ispCheckClass

from isp.config import dict_merge
#from datetime import datetime
#from dateutil.parser import parse

from dotmap import DotMap
import numpy as np
import pandas as pd
#from pandas.io.json import json_normalize

from pylinac.core.profile import SingleProfile, MultiProfile

import matplotlib.pyplot as plt

import logging
logger = logging.getLogger( "MQTT" )

from isp.plot import plotClass


class PFImage( PFDicomImage, DicomImage ):
    '''
    '''

    def __init__(self, pathOrData=None, **kwargs ):
        """ Erweitert PFDicomImage um die eigene DicomImage Klasse

        """

        #print("PFImage.__init__", path, kwargs)

        # das pylinacpicketfence Image
        #image.LinacDicomImage.__init__( self, path, **kwargs )

        # die eigene Erweiterung
        DicomImage.__init__( self, pathOrData )


class qa_mlc( PicketFence, ispCheckClass ):
    """Erweitert die Klasse PicketFence, um eine eigene DicomImage Erweiterung zu verwenden

    """
    _log_fits = None

    _kennung = "{Kennung}"

    def __init__( self, checkField=None, baseField=None, normalize: str="diff", kennung:str="{Kennung}" ):
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
        #print( "qa_mlc" , checkField )

        self.checkField = checkField
        self.baseField = baseField

        # ispCheckClass initialisieren ruft ggf normalize auf
        if self.checkField and self.baseField:
            # checkField und baseField wurden angegeben, normalize möglich
            # self.image und self.baseImage initialisieren und ggf normalisieren
            ispCheckClass.__init__( self,
                image=PFImage( self.checkField ),
                baseImage=PFImage( self.baseField ),
                normalize=normalize
            )
        elif self.checkField:
            # nur checkfield wurde angegeben
            # self.image initialisieren
            ispCheckClass.__init__( self,
                image=PFImage( self.checkField )
            )

        # default Settings einstellen
        self._orientation = None
        tolerance = 0.5
        action_tolerance = None
        hdmlc = False

        # image muss da sein
        if self.image:
            self.settings = Settings(self.orientation, tolerance, action_tolerance, hdmlc, self.image, self._log_fits )

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
        # int(round( self.image.dpmm * position + self.image.cax.x ))
        """ Analysis """

        #position = 0.6
        # Profilwerte in %
        #profile = MultiProfile(self.image.array[:, int(round(self.image.array.shape[1]*vert_position))])
        #profile = MultiProfile( self.image.array[:, 563] * 100  )
        # evt. asl % mit MultiProfile( self.image.array[:, pixPosition]  * 100 )

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
        peak_idxs = profile.find_peaks( min_distance=10, threshold=0.1 )
        for peak_idx in peak_idxs:
            maxPeaks.append( int( peak_idx ) )

        # mittelwert von maxPeaks
        meanMaxPeaks = np.mean( profile[maxPeaks] )

        """ min Peaks (leaf) suchen """
        minPeaks = []
        profile.invert()
        # FIXED: manchmal werden als peak_idx floats mit .0 von find_peaks ermittelt deshalb nach int wandeln
        peak_idxs = profile.find_peaks( min_distance=10, threshold=0.1 )
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
                    profile = SingleProfile( self.image.array[ : , self.image.mm2dots_X( p ) ] )
                else:
                    profile = SingleProfile( self.image.array[ self.image.mm2dots_Y( p ) ] )

                # Abstand der Lamellen bei 50%
                leafData["fwxm"][p] = profile.fwxm( ) / self.image.dpmm

                # Zentrumsversatz bei 50% bestimmen
                leafData["shift"][p] = ( (len(profile.values) / 2) - profile.fwxm_center( ) ) / self.image.dpmm

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
            plotTitle = "lfd:{lfd:d} G:{gantry:01.1f} K:{collimator:01.1f}"

        fig, ax = self.initPlot( size, False, nrows=1, ncols=1 )
        ax.set_title( plotTitle.format( **data, position=(0.5, 1.05) ) )
        plot = {
            "num" : [],
            "x1": [],
            "x2": [],
        }
        positions = []

        leaf = leaf_from
        for k, v in data['fwxm.data'].items():
            shift = data['shift.data'][ k ]
            plot["num"].append( leaf )

            # position und shift
            positions.append(k)
            v = ( (v - 50) / 2 ) + virtLeafSize

            plot["x1"].append( v + shift  )
            plot["x2"].append( -1 * v + shift  )
            # nächster leaf
            leaf += 1

        # x1 und x2 plotten beide in blue
        ax.bar(plot["num"], plot["x1"], color="#0343dfCC", linewidth=1)
        ax.bar(plot["num"], plot["x2"], color="#0343dfCC", linewidth=1)

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

        return self.getPlot()


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
        fig, ax = self.initPlot( size, nrows=2, ncols=1)

        #
        # chart Leafpaarabstand
        #
        if "fwxm.data" in data:
            df_fwxm = pd.DataFrame( data["fwxm.data"] )#.transpose()
            df_fwxm.boxplot(ax = ax[0], whis="range")

            ax[0].set_title('Leafpaarabstand (fwxm)')
            ax[0].get_yaxis().set_ticklabels([48.5, 49, 49.5, 50, 50.5, 51, 51.5])
            ax[0].get_yaxis().set_ticks( [48.5, 49, 49.5, 50, 50.5, 51, 51.5] )
            ax[0].axhline(50, color='k', linewidth = 0.5)

        #
        # chart Zentrumsabweichung
        #
        if "shift.data" in data:
            df_shift = pd.DataFrame( data["shift.data"] )#.transpose()
            df_shift.boxplot(ax = ax[1], whis="range")

            ax[1].set_title('Zentrumsabweichung (shift)')
            ax[1].get_yaxis().set_ticklabels([1.5, 1, 0.5, 0, -0.5, -1, -1.5])
            ax[1].get_yaxis().set_ticks( [1.5, 1, 0.5, 0, -0.5, -1, -1.5] )
            ax[1].axhline(0, color='k', linewidth = 0.5)

        plt.tight_layout(pad=0.4, w_pad=0.5, h_pad=1.0)

        return self.getPlot()


    def plotTransmission( self, transmission, chartSize={}, showInterleafMean=False, showLeafMean=False, showInterleafPeaks=False, showLeafPeaks=False ):
        """
            profile mit Peaks anzeigen
        """

        # plotbereiche festlegen
        fig, ax = self.initPlot( chartSize )

        #ax.set_ylabel('%')
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

        # mittelwert linie
        #ax.axhline( vmean, linestyle="--", linewidth=1, color="gray" )

        #
        #plt.plot(peaks, x[peaks], "x", color="red" )

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
        return self.getPlot()


    def picketfence_plotImage(self, metadata={}, guard_rails: bool=True, mlc_peaks: bool=True, overlay: bool=True,
                            leaf_error_subplot: bool=True, show: bool=False):
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

        # self.axTicks( ax, fieldTicks )
        #field = { "X1":-100, "X2": 100, "Y1": -100, "Y2":100, "xStep":50, "yStep":50, "border": 10 }

        img, fig, ax = self.image.plotImage( original=False, getPlot=False
                        , metadata=metadata
                        , plotTitle="{Kennung} - G:{gantry:01.1f} K:{collimator:01.1f}"
                        , plotCax=False, plotField=True, figsize=figsize )

        # generate a leaf error subplot if desired
        if leaf_error_subplot:
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
            o = Overlay(self.image, self.settings, self.pickets)
            o.add_to_axes(ax)

        # plot CAX
        ax.plot(self.image.center.x, self.image.center.y, 'r+', ms=12, markeredgewidth=3)

        # tighten up the plot view
        ax.set_xlim([0, self.image.shape[1]])
        ax.set_ylim([0, self.image.shape[0]])

        if show:
            plt.show()

        return self.getPlot()

    def _add_leaf_error_subplot(self, ax: plt.Axes):
        """Überschreibt die ursprüngliche PicketFenceFunktion
        Es werden jetzt beide (tolerance und action_tolerance) Linien gezeichnet
        und das Chart hat jetzt bei UP_DOWN eine doppelte breite
        """

        """Add a bar subplot showing the leaf error."""
        tol_line_height = [self.settings.tolerance, self.settings.tolerance]
        tol_line_width = [0, max(self.image.shape)]

        atol_line_height = [self.settings.action_tolerance, self.settings.action_tolerance]

        # make the new axis
        divider = make_axes_locatable(ax)
        if self.settings.orientation == UP_DOWN:
            axtop = divider.append_axes('right', size=8, pad=1, sharey=ax)
        else:
            axtop = divider.append_axes('bottom', size=2, pad=1, sharex=ax)

        # get leaf positions, errors, standard deviation, and leaf numbers
        # error_plot_positions, error_means, error_stds, mlc_leaves
        pos, mean, stds, leaf_nums = self.pickets.error_hist()
        #print( "leaf_nums", pos, vals, err, leaf_nums)
        leafs = []
        for l in leaf_nums:
            # image muss up/down getauscht werden, deshalb auch die MLC Nummern ändern
            leafs.append( l[1]-60 )

        #ax2 = axtop.twiny()  # instantiate a second axes that shares the same x-axis

        #print(leaf_nums)
        # plot the leaf errors as a bar plot
        if self.settings.orientation == UP_DOWN:
            # ohne xerr
            axtop.barh(pos, mean, height=self.pickets[0].sample_width * 2, alpha=0.4, align='center', tick_label=leafs)
            #axtop.barh(pos, mean, xerr=stds, height=self.pickets[0].sample_width * 2, alpha=0.4, align='center')
            # plot the tolerance line(s)
            # TODO: replace .plot() calls with .axhline when mpld3 fixes funtionality
            axtop.plot(tol_line_height, tol_line_width, 'r-', linewidth=3)

            if self.settings.action_tolerance is not None:
                axtop.plot(atol_line_height, tol_line_width, 'y-', linewidth=3)

            # reset xlims to comfortably include the max error or tolerance value
            axtop.set_xlim([0, max(max(mean), self.settings.tolerance) + 0.1])

            #axtop.tick_params( 'y', colors='r' )

        else:
            # ohne yerr
            axtop.barh(pos, mean, height=self.pickets[0].sample_width * 2, alpha=0.4, align='center', tick_label=leafs)

            #axtop.bar(pos, mean, yerr=stds, width=self.pickets[0].sample_width * 2, alpha=0.4, align='center')
            axtop.plot(tol_line_width, tol_line_height,
                       'r-', linewidth=3)
            if self.settings.action_tolerance is not None:
                axtop.plot(tol_line_width, tol_line_height, 'y-', linewidth=3)
            axtop.set_ylim([0, max(max(mean), self.settings.tolerance) + 0.1])

        # add formatting to axis
        #axtop.grid(True)
        axtop.set_title("Average Error (mm)")

    @property
    def passed_action(self) -> bool:
        """Whether all the pickets passed_action tolerance."""
        return all(picket.mlc_passed_action for picket in self.pickets )


    def picketfence_results(self):
        """Gibt die Ergebnisse der Picketfence Auswertung als dict
        Verwendet dabei zusätzlich eine Auswertung über error_hist ( daten für subplot )
        """
        pass_pct = self.percent_passing
        offsets = ' '.join('{:.1f}'.format(pk.dist2cax) for pk in self.pickets)

        # mean statt  np.median(np.abs(self.error_array))
        self.abs_mean_error = np.mean(np.hstack([picket.error_array for picket in self.pickets]))

        # max von mean bestimmen
        error_plot_positions, error_means, error_stds, mlc_leaves = self.pickets.error_hist()
        # pandas serie max und position bestimmen
        pd_error_means = pd.Series( error_means)
        max_from_mean_error = pd_error_means.max()
        # FIXME: image muss up/down getauscht werden, deshalb auch die MLC Nummern ändern
        max_from_mean_leaf = mlc_leaves[ pd_error_means.idxmax() ][1] - 60

        return {
            'filename': self.infos["filename"],
            'Kennung': self._kennung.format( **self.infos ),
            'unit':  self.infos['unit'],
            'energy': self.infos['energy'],
            'gantry' : self.infos['gantry'],
            'collimator': self.infos['collimator'],
            'checkPositions': self.pickets,
            "offsets" : offsets,
            "pass_pct" : pass_pct,
            "abs_median_error": self.abs_median_error,
            "abs_mean_error": self.abs_mean_error,
            "mean_spacing" : self.pickets.mean_spacing,
            "max_error": self.max_error,
            "max_error_picket" : self.max_error_picket,
            "max_error_leaf" :self.max_error_leaf,
            "passed": self.passed,
            "passed_action" : self.passed_action,
            "max_from_mean" : max_from_mean_error,
            "max_from_mean_leaf" : max_from_mean_leaf,
        }
        """
        string = f"Picket Fence Results: \n{pass_pct:2.1f}% " \
                 f"Passed\nMedian Error: {self.abs_median_error:2.3f}mm \n" \
                 f"Mean picket spacing: {self.pickets.mean_spacing:2.1f}mm \n" \
                 f"Picket offsets from CAX (mm): {offsets}\n" \
                 f"Max Error: {self.max_error:2.3f}mm on Picket: {self.max_error_picket}, Leaf: {self.max_error_leaf}"
        """
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

        # print( fileData )
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
                "filename": self.metadata.info["anleitung"],
                "attrs": {"class":"layout-fill-width"},
            },
            "_image": { "width": 80, "height": 80 },
            "_image_attrs" : {"class":"layout-50-width", "margin-right": "20px"},
            "_chart": { "width": 180, "height": 45 },
            "_text" : { },
            "_text_attrs" : {"margin-left":"5mm"},
            # Messorte alle 10mm im Bereich von -70mm bis 70mm
            "checkPositions" : np.arange(-70, 80, 10),


            #"groupby": [ "day", "SeriesNumber" ], # groupby in der config angegeben werden sonst default (2019 nicht in der gleichen Serie)
            "table_fields" : [
                {'field': 'position', 'label':'Position', 'format':'{0:d}' },
                {'field': 'gantry', 'label':'Gantry', 'format':'{0:.1f}' },
                {'field': 'collimator', 'label':'Kollimator', 'format':'{0:.1f}' },
                {'field': 'leaf.mean_x', 'label':'X1-Leaf Mean', 'format':'{0:.3f}' },
                {'field': 'leaf.mean_x_passed', 'label':'X1-Passed'},
                {'field': 'leaf.mean_y', 'label':'X2-Leaf Mean', 'format':'{0:.3f}' },
                {'field': 'leaf.mean_y_passed', 'label':'X2-Passed'}
            ]
        } ), self.metadata )

        # print("doJT_4_2_2_1_A", md.groupby )
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

            #print("doJT_4_2_2_1_A - df_group", df_group)
            # das offene Feld merken
            try:
                df_base = df_group.query("check_subtag.isnull()", engine='python')
            except:
                # ein leeres df damit in checkFields geprüft wird
                df_base = pd.DataFrame()

            #print("doJT_4_2_2_1_A - df_base", df_base)
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
            '''
            if not self.checkFields( md, df_base, df_fields, 2 ):
                result.append( self.pdf_error_result(
                    md, date=checkDate, group_len=len( result ),
                    msg='<b>Datenfehler</b>: keine Felder gefunden oder das offene Feld fehlt.'

                ) )
                return
            '''

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

                self.pdf.image( img, md["_image"], attrs=md["_image_attrs"] )


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

        # print(fileData[ ["energy", "day", "AcquisitionMonth", "AcquisitionYear", "SeriesNumber"] ])
        #print( md.get("groupby", [ "day", "SeriesNumber" ]) )
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
        fileData : Pandas


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
                "filename": self.metadata.info["anleitung"],
                "attrs": {"class":"layout-fill-width"},
            },
            "field_count": 3,
            "_image": { "width": 58, "height": 58 },
            "_image_attrs" : {"class":"layout-50-width"},
            "_text" : {},
            "_text_attrs" : {},
            "_table_attrs" : {"class":"layout-fill-width", "margin-top": "2mm"},
            # Messorte nur im zentrum
            "checkPositions" : [0] ,

            "table_fields" : [
                {'field': 'Kennung', 'label':'Kennung', 'format':'{0}', 'style': [('text-align', 'left')] },
                {'field': 'gantry', 'label':'Gantry', 'format':'{0:.1f}' },
                {'field': 'collimator', 'label':'Kollimator', 'format':'{0:.1f}' },
                {'field': 'interleaf.mean', 'label':'interleaf Mean', 'format':'{0:.3f}' },
                {'field': 'interleaf.mean_passed', 'label':'Passed'}
            ]
        } ), self.metadata )

        #print(fileData[ ["energy", "day", "gantry", "collimator", "SeriesNumber", "check_subtag"] ])

        def groupBySeries( df_group ):
            """gruppenweise Auswertung
            """
            # print( df_group[ ['check_subtag', 'gantry', 'collimator', 'Kennung'] ] )
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
                '''
                # übergebene felder prüfen
                if not self.checkFields( md, df_base, df_fields, 3 ):
                    return
                '''
                #print( df[ ['check_subtag', 'gantry', 'collimator', 'Kennung'] ] )

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

                        self.pdf.image( img, md["_image"], attrs=md["_image_attrs"]  )

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
        fileData : Pandas


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
                "filename": self.metadata.info["anleitung"],
                "attrs": {"class":"layout-fill-width", "margin-bottom": "5mm"},
            },

            "_image": { "width": 58, "height": 58 },
            "_image_attrs" : {"class":"layout-50-width"},

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
                {'field': 'gantry', 'label':'Gantry', 'format':'{0:.1f}' },
                {'field': 'collimator', 'label':'Kollimator', 'format':'{0:.1f}' },
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

        #print("fileData", fileData[ [ "day", "SeriesNumber", "gantry", "collimator", "check_variante", "check_subtag" ] ] )


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

                # print("groupByGantryKolli", md.current)
                # logger.error( "Base: {}, Fields:{}".format( len(df_base.index), len(df_base.index) ) )
                # alles notwendige da? Ein base und 2 weitere Felder
                errors = self.checkFields( md, df_base, df_fields, md["field_count"])
                if len(errors) > 0:
                    result.append( self.pdf_error_result(
                        md, date=checkDate, group_len=len( result ),
                        errors=errors
                    ) )
                    return
                '''
                # übergebene felder prüfen
                if not self.checkFields( md, df_base, df_fields, 3, warn=False ):
                    return
                '''

                #print( df[ ['check_subtag', 'gantry', 'collimator', 'Kennung'] ] )
                #print( df_fields[ ['check_subtag', 'gantry', 'collimator'] ] )
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
                        self.pdf.image( img, md[ "_image_{0:d}".format( positions[0] ) ], attrs=md["_image_attrs"] )

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
            df["Gantry/Kollimator"] = df.apply(lambda x:'{0:.1f}/{1:.1f}'.format( x['gantry'], x['collimator']  ),axis=1)

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
        fileData : Pandas


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
            "field_count": 1,
            "manual": {
                "filename": self.metadata.info["anleitung"],
                "attrs": {"class":"layout-fill-width", "margin-bottom": "5mm"},
            },
            "_text": { "left":0, "top": 0 },
            "_table": { "class":"layout-40-width", "margin-top": "1mm"},
           # "_table": { "left":0, "top":55, "width":65 },
            "_infobox" : { "left":75, "top":50, "width":100 },
            "_clip" : { "width":"80mm", "height":"30mm", "margin-left":"10mm", "margin-top":"5mm" },
            "_clipLegend" : { "margin-top": "5mm" },
            "_chart": { "left":75, "top":135, "width":100, "height":100},
            "_toleranz": { "left":75, "top":235, "width" : 100 },
            "table_fields": [
                {'field': 'doserate', 'label':'Dosisleistung', 'format':'{0}'},
                {'field': 'gantry', 'label':'Gantry', 'format':'{0:.1f}' },
                {'field': 'collimator', 'label':'Kolli', 'format':'{0:.1f}' },
                {'field': 'speed', 'label':'Geschw.', 'format':'{0}'},
                {'field': 'delta', 'label':'Delta [%]', 'format':'{0:.1f}' },
                {'field': 'delta_passed', 'label':'Passed', 'style':  [('max-height', '10px'), ('vertical-align','top')] }
            ]
        } ), self.metadata )

        def groupBy( df_group ):
            """
            """

            # das Datum vom ersten Datensatz verwenden
            checkDate=df_group['AcquisitionDateTime'].iloc[0].strftime("%d.%m.%Y")
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

            data = []
            # pro speed
            def groupBySpeed(df_speed):
                #print( len(df_speed) )
                #print( df_speed)
                df_base = df_speed.query("open == 'OF'")
                df_fields = df_speed.query("open != 'OF'")

                # alles notwendige da?
                errors = self.checkFields( md, df_base, df_fields, md["field_count"])
                if len(errors) > 0:
                    result.append( self.pdf_error_result(
                        md, date=checkDate, group_len=len( result ),
                        errors=errors
                    ) )
                    return
                '''
                if not self.checkFields( md, df_base, df_field, 1 ):
                    return
                '''

                check = qa_mlc(
                    checkField=self.getFullData( df_fields.iloc[0] ),
                    baseField=self.getFullData( df_base.iloc[0] ),
                    normalize="prozent"
                )

                # Daten merken
                data.append( {
                    "doserate" : check.infos["doserate"],
                    "speed" : check.infos["speed"],
                    "gantry" : check.infos["gantry"],
                    "collimator" : check.infos["collimator"],
                    "delta" : check.image.getFieldRoi().mean() * 100
                })

                # progress pro file stimmt nicht immer genau (baseimage)
                # 40% für die dicom daten 40% für die Auswertung 20 % für das pdf
                self.fileCount += 2
                if hasattr( logger, "progress"):
                    logger.progress( md["testId"],  40 + ( 40 / filesMax * self.fileCount ) )

            # alle speed arten durch gehen
            df_group.groupby( [ "gantry", "collimator", "doserate", "speed" ] ).apply( groupBySpeed )


            self.pdf.html( html,  md["_infobox"], { "class" : "infobox" })

            # es wurden keine Felder gefunden (checkFields fehler)
            if len( data ) < 1:
                result.append( self.pdf_error_result(
                    md, date=checkDate, group_len=len( result ),
                    msg='<b>Datenfehler</b>: keine Felder gefunden oder das offene Feld fehlt.',
                    pos={ "top":150 }
                ) )
                return


            df = pd.DataFrame(data)

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
            self.pdf.pandas( df,
                attrs=md["_table"],
                fields=md["table_fields"]
            )


            #
            # chart
            #

            # plot anlegen
            plot = plotClass( )
            fig, ax = plot.initPlot( md["_chart"] , True )

            # data frame gruppieren und mit neuem index versehen
            df_chart = df.set_index(['gantry', 'collimator', 'speed', 'doserate' ])['delta'].unstack()
            # als bar plot ausgeben
            df_chart.plot( ax=ax, kind='bar', rot=75)

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
            self.pdf.text( text, md["_toleranz"] )


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
             .sort_values(["gantry", "collimator", "doserate", "speed"])
             .groupby( [ 'day' ] ) # , 'SeriesNumber'
             .apply( groupBy )
        )
        # abschließen pdfdaten und result zurückgeben
        return self.pdf.finish(), result


    def doMT_LeafSpeed(self, fileData ):
        """Monatstest Leafspeed
        Wie JT_LeafSpeed aber nur bei Gantry 0 sowie mit und ohne Gating

        Parameters
        ----------
        fileData : Pandas


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
                "filename": self.metadata.info["anleitung"],
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
                {'field': 'collimator', 'label':'Kolli', 'format':'{0}' },
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
            #print( df_group[ ["open", "check_subtag" ] ] )
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
                #print( len(df_speed) )
                #print( df_speed[ ["open" ] ] )

                try:
                    # das offene Feld merken
                    df_base = df_speed.query("open == 'OF'").iloc[0]
                    self.fileCount += 1
                except:
                    # ein leeres df damit in checkFields geprüft wird
                    df_base = pd.DataFrame()
                    #logger.warning( "kein offenes Feld" )
                #df_base = pd.DataFrame()
                # prüfung von df_base

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
                    pos={ "top":150 }
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
# es wurden keine Felder gefunden (checkFields fehler)
            if len( data ) > 12:
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
        fileData : Pandas

        md : dotmap

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
            #print( df )

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
        fileData : pandas.dataframe

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
                "filename": self.metadata.info["anleitung"],
                "attrs": {"class":"layout-fill-width"},
            },
            "_leafPlot" : { "width" : 45, "height" : 45},
            "_boxPlot" : { "width" : 90, "height" : 45},
            "plotTitle" : "lfd:{lfd:d} G:{gantry:01.1f} K:{collimator:01.1f}",
            "table_fields" : [
                {'field': 'lfd', 'label':'lfd', 'format':'{0:d}' },
                {'field': 'gantry', 'label':'Gantry', 'format':'{0:1.1f}' },
                {'field': 'collimator', 'label': 'Kollimator', 'format':'{0:1.1f}' },
                {'field': 'fwxm.min', 'label':'FWXM<br>min', 'format':'{0:.3f}' },
                {'field': 'fwxm.mean', 'label':'FWXM<br>mean', 'format':'{0:.3f}' },
                {'field': 'fwxm.max', 'label':'FWXM<br>max', 'format':'{0:.3f}' },
                {'field': 'fwxm.passed', 'label':'FWXM<br>passed' },
                {'field': 'shift.min', 'label':'Shift<br>min', 'format':'{0:.3f}' },
                {'field': 'shift.mean', 'label':'Shift<br>mean', 'format':'{0:.3f}' },
                {'field': 'shift.max', 'label':'Shift<br>max', 'format':'{0:.3f}' },
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
            "series_sort_values" : ['day'],
            "series_groupby": ["day", "SeriesNumber"],
            "manual": {
                "filename": self.metadata.info["anleitung"],
                "attrs": {"class":"layout-fill-width"},
            },
            "_leafPlot" : { "width" : 45, "height" : 45},
            "_boxPlot" : { "width" : 90, "height" : 45},
            "plotTitle" : "lfd:{lfd} - {Richtung}",
            "table_fields" : [
                {'field': 'lfd', 'label':'lfd', 'format':'{0:d}' },
                {'field': 'Richtung', 'label':'Richtung', 'format':'{0}' },
                {'field': 'Datum', 'label':'Datum', 'format':'{0:%d.%m.%Y %H:%M:%S}' },
                {'field': 'fwxm.min', 'label':'FWXM<br>min', 'format':'{0:.3f}' },
                {'field': 'fwxm.mean', 'label':'FWXM<br>mean', 'format':'{0:.3f}' },
                {'field': 'fwxm.max', 'label':'FWXM<br>max', 'format':'{0:.3f}' },
                {'field': 'fwxm.passed', 'label':'FWXM<br>passed' },
                {'field': 'shift.min', 'label':'Shift<br>min', 'format':'{0:.3f}' },
                {'field': 'shift.mean', 'label':'Shift<br>mean', 'format':'{0:.3f}' },
                {'field': 'shift.max', 'label':'Shift<br>max', 'format':'{0:.3f}' },
                {'field': 'shift.passed', 'label':'Shift<br>passed' },
            ],

            "options":{
                "leafs" : {
                    "from": 1,
                    "to" : 60
                }
            }
        }), self.metadata )

        # und mit den Angaben aus config (info) ergänzen / überschreiben


        return self._doLamellenpositioniergenauigkeit(fileData, md)

    def _doMLC_VMAT( self, fileData, overrideMD={}, passedOn=True, withOffsets=False ):
        """VMAT MLC-PicketFence Auswertung

        In tolerance value und nicht Formel angeben, da analyze die Angaben benötigt

        fileData : pandas.DataFrame

        overrideMD: dict

        passedOn : bool
            wann ist der Test OK bei VMAT_1_2 ist er bei false OK

        withOffsets: bool

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
                "filename": self.metadata.info["anleitung"],
                "attrs": {"class":"layout-fill-width"},
            },
            "_chartSize" : { "width" : 180, "height" : 110},
            "_table" : { "top" : 165 },
            "table_fields_offsets" : [
                {'field': 'Kennung', 'label':'Kennung', 'format':'{0}', 'style': [('text-align', 'left')] },
                {'field': 'gantry', 'label':'Gantry', 'format':'{0:1.1f}' },
                {'field': 'offsets', 'label':'Picket offsets from CAX [mm]' }
            ],
            "table_fields" : [
                {'field': 'Kennung', 'label':'Kennung', 'format':'{0}', 'style': [('text-align', 'left')] },
                {'field': 'gantry', 'label':'Gantry', 'format':'{0:1.1f}' },
                {'field': 'collimator', 'label':'Kollimator', 'format':'{0:1.1f}' },
                {'field': 'pass_pct', 'label':'Passed %', 'format':'{0:2.1f}' },

                {'field': 'mean_spacing', 'label':'Mean spacing [mm]', 'format':'{0:2.1f}' },
                {'field': 'mean_spacing_passed', 'label':'Mean spacing Passed' },

                {'field': 'abs_mean_error', 'label':'Mean Error [mm]', 'format':'{0:2.3f}' },
                {'field': 'abs_mean_error_passed', 'label':'Mean Error Passed' },

                {'field': 'max_from_mean', 'label':'Max von Mean Error [mm]', 'format':'{0:2.3f}' },
                {'field': 'max_from_mean_passed', 'label':'Max von Mean Error Passed' },
                {'field': 'max_from_mean_leaf', 'label':'Max von Mean Error<br>bei Leaf', 'format':'{0:d}' },

            ]
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
                check = qa_mlc( self.getFullData( info._asdict() ) )
                # image Flip oben unten durchführen da sonst die Darstellung falsch ist
                check.image.flipud()
                # Feld vorher beschneiden
                check.image.cropField(  { "X1":-110, "X2": 110, "Y1": -110, "Y2":110 } )
                # und picketfence analyse durchführen
                check.analyze( tolerance=error, action_tolerance=warning )

                results = check.picketfence_results()
                results["Kennung"] = results["Kennung"]
                # nur Kolli 0° felder
                if results["collimator"] == 0:
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

        """
        md = {
            "_imgSize" : {"width" : 45, "height" : 55},
            "_imgField": {"border": 10 },
            "_chartSize" : { "width" : 90, "height" : 55}
        }
        return self._doMLC_VMAT( fileData, overrideMD=md, withOffsets=True )

    def doMT_VMAT_1_1( self, fileData ):
        """PicketFence mit rot

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
        d-4: Bilder vom leafGAP Feld tips_0_0 verwenden (tips)

        d-6:

        d-7:

        d-8:

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
                "filename": self.metadata.info["anleitung"],
                "attrs": {"class":"layout-fill-width", "margin-bottom": "5mm"},
            },
            "imgSize" : {"width" : 100, "height" : 100},
            "_image": { "left":40, "top":10, "width" : 100, "height":100 },
            "_tableA": { "left":25, "top":110, "width" : 50 },
            "_tableB": { "left":110, "top":110, "width" : 50 },
            "table_fields" : [
                {'field': 'leaf', 'label':'Leaf' },
                {'field': 'position', 'label':'Position', 'format':'{0:01.1f}' },
                {'field': 'value', 'label':'50%', 'format':'{0:01.3f}' },
            ]
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
                    profile = SingleProfile( check.image.array[ check.image.mm2dots_Y( p ) ] )
                    # daten zusammenstellen
                    data[ i ] = {
                        "leaf" : i,
                        "position" :  p,
                        "value" : (profile.fwxm() / check.image.dpmm / 2)
                    }


                #
                # Bild anzeigen
                #
                img = check.image.plotImage(  )
                self.pdf.image(img, md["_image"] )

                #
                # Tabellen
                #

                # pandas dataframe erstellen
                #
                # durch zusätzliche angabe von columns kann sortiert werden
                # transpose um x und y zu vertauschen
                data_frame = pd.DataFrame( data ).transpose()
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

                # progress pro file stimmt nicht immer genau (baseimage)
                # 40% für die dicom daten 40% für die Auswertung 20 % für das pdf
                self.fileCount += 1
                if hasattr( logger, "progress"):
                    logger.progress( md["testId"],  40 + ( 40 / filesMax * self.fileCount ) )

        #
        # Gruppiert nach Tag und SeriesNumber abarbeiten
        #
        series = fileData.groupby( [ 'day', 'SeriesNumber' ] )

        #print( series.size() )

        series.apply( groupBySeries )
        # abschließen pdfdaten und result zurückgeben
        return self.pdf.finish(), result


