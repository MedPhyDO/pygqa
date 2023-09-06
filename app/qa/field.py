# -*- coding: utf-8 -*-

__author__ = "R. Bauer"
__copyright__ = "MedPhyDO - Machbarkeitsstudien des Instituts für Medizinische Strahlenphysik und Strahlenschutz am Klinikum Dortmund im Rahmen von Bachelor und Masterarbeiten an der TU-Dortmund / FH-Dortmund"
__credits__ = ["R.Bauer", "K.Loot"]
__license__ = "MIT"
__version__ = "0.2.0"
__status__ = "Prototype"

from typing import BinaryIO

from pylinac.field_analysis import FieldAnalysis
from pylinac.core.profile import MultiProfile
from pylinac.core.geometry import Point
from pylinac.core.profile import SingleProfile

from app.base import ispBase
from app.image import DicomImage
from app.check import ispCheckClass

from isp.config import dict_merge
from isp.plot import plotClass

import numpy as np
import pandas as pd
from dotmap import DotMap

import matplotlib.pyplot as plt

# logging
import logging
logger = logging.getLogger( "MQTT" )

import math

def pointRotate(origin, point, angle):
    """
    Rotate a point counterclockwise by a given angle around a given origin.
    with the usual axis conventions:
        x increasing from left to right, y increasing vertically upwards.

        The angle should be given in dec.

    """
    ox = origin.x
    oy = origin.y
    px = point.x
    py = point.y

    angle = math.radians( angle )

    qx = ox + math.cos(angle) * (px - ox) - math.sin(angle) * (py - oy)
    qy = oy + math.sin(angle) * (px - ox) + math.cos(angle) * (py - oy)

    return Point( qx, qy )

class FSImage( FieldAnalysis, DicomImage ):

    def __init__(
        self,
        path: str | BinaryIO,
        filter: int | None = None,
        image_kwargs: dict | None = None,
    ):
        """ Erweitert field_analysis um die eigene DicomImage Klasse

        """
        # die eigene Erweiterung
        DicomImage.__init__( self, path )


class qa_field( ispCheckClass ):
    """Erweitert die Klasse , um eine eigene DicomImage Erweiterung zu verwenden

    """
    def __init__( self, checkField, baseField=None, normalize: str="none" ):
        """ checkField und ggf baseField laden und ispCheckClass initialisieren

        """

        self.checkField = checkField
        self.baseField = baseField

        if self.checkField and self.baseField:
            # checkField und baseField wurden angegeben, normalize möglich
            # self.image und self.baseImage initialisieren und ggf normalisieren
            ispCheckClass.__init__( self,
                image=FSImage( self.checkField ),
                baseImage=FSImage( self.baseField ),
                normalize=normalize
            )
        elif self.checkField:
            # nur checkfield wurde angegeben
            # self.image initialisieren
            ispCheckClass.__init__( self,
                image=FSImage( self.checkField )
            )


    def getProfileData( self ):
        """Profildaten aus image holen flatness='iec' symmetry='pdq iec'
        DONE: flatness selbst berechnen - flatness = (dmax-dmin) / np.mean(m)

        """
        def flatness_calculation(profile:SingleProfile):
            """IEC specification for calculating flatness
            'der CAX wird aus 5 benachbarten Werten gebildet'
            """
            # cax_idx = profile.fwxm_center()

            fwxm_data = profile.fwxm_data()
            cax_idx= fwxm_data["center index (rounded)"]           
            #print( fwxm_data )
            # cax von 5 benachbarten Werten bilden
            cax5 = np.mean( profile.values[cax_idx-2:cax_idx+3] )

            #print( cax, profile, cax5 )

            dmax = profile.field_calculation(in_field_ratio=0.8, calculation='max')
            dmin = profile.field_calculation(in_field_ratio=0.8, calculation='min')
            flatness = (dmax - dmin) / cax5 * 100


            #lt_edge, rt_edge = profile.field_edges()
            lt_edge = fwxm_data["left index (rounded)"]    
            rt_edge = fwxm_data["right index (rounded)"]    
            return flatness, dmax, dmin, lt_edge, rt_edge

        vert_position = 0.5
        horiz_position = 0.5

        vert_profile = SingleProfile(self.image.array[:, int(round(self.image.array.shape[1] * vert_position))])
        horiz_profile = SingleProfile(self.image.array[int(round(self.image.array.shape[0] * horiz_position)), :])

        vert_flatness, vert_max, vert_min, vert_lt, vert_rt = flatness_calculation(vert_profile)
        horiz_flatness, horiz_max, horiz_min, horiz_lt, horiz_rt = flatness_calculation(horiz_profile)
        flatness =  {
            'method': "IEC",
            'horizontal': {
                'value': horiz_flatness, 'profile': horiz_profile, 'profile max': horiz_max, 'profile min': horiz_min, 'profile left': horiz_lt, 'profile right': horiz_rt,
            },
            'vertical': {
                'value': vert_flatness, 'profile': vert_profile, 'profile max': vert_max, 'profile min': vert_min, 'profile left': vert_lt, 'profile right': vert_rt,
            },
        }

        return {
                'filename': self.infos["filename"],
                'Kennung': self.infos["Kennung"],
                'type': self.infos['testTags'],
                'unit':  self.infos['unit'],
                'energy': self.infos['energy'],
                'gantry' : self.infos['gantry'],
                'collimator': self.infos['collimator'],
                'flatness': flatness
               }

    def plotProfile(self, data, metadata={} ):
        """Ein horizontale und vertikale Profilachse plotten

        Parameters
        ----------
        data : dict

        metadata : dict
                profileSize
                profileTitle - format Ersetzungen aus self.infos sind möglich
        """
        # plotbereiche festlegen und profileSize als imgSize übergeben
        plot = plotClass( )
        fig, ax = plot.initPlot( imgSize=metadata["profileSize"], nrows=2 )
    
        # axes coordinates are 0,0 is bottom left and 1,1 is upper right

        # Kurven Informationen
        if not "profileTitle" in metadata:
            metadata["profileTitle"] = "{Kennung} - Energie:{energy} Gantry:{gantry:.1f} Kolli:{collimator:.1f}"

        ax[0].set_title( metadata["profileTitle"].format( **self.infos ) )

        #x= np.divide(data["horizontal"]['profile'].values, self.image.dpmm + self.image.cax.x)
        #ax[0].get_xaxis().set_ticks( np.arange( self.mm2dots_X(-200), self.mm2dots_X(200), self.mm2dots_X(50) ) )
        #ax[0].get_xaxis().set_ticklabels([-200,0,200])
        #ax[0].set_xlim([ self.mm2dots_X(-210), self.mm2dots_X(210) ])

        #ax[0].set_title( 'horizontal' )

        # 2. Kurve horizontal

        # x-Achse
        ax[0].get_xaxis().set_ticklabels([])
        ax[0].get_xaxis().set_ticks( [] )

        # y-achse
        ax[0].get_yaxis().set_ticklabels([])
        ax[0].get_yaxis().set_ticks( [] )

        # kurve plotten
        ax[0].plot(data["horizontal"]['profile'].values , color='b')

        # links rechts min max
        ax[0].axhline(data["horizontal"]['profile max'], color='g', linewidth=1 )
        ax[0].axhline(data["horizontal"]['profile min'], color='g', linewidth=1 )
        ax[0].axvline(data["horizontal"]['profile left'], color='g', linewidth=1, linestyle='-.')
        ax[0].axvline(data["horizontal"]['profile right'], color='g', linewidth=1, linestyle='-.')

        fwxm_data = data["horizontal"]['profile'].fwxm_data()
        cax_idx= fwxm_data["center index (rounded)"]      
        
        ax[0].axvline(cax_idx, color='g', linewidth=1, linestyle='-.')

        # limits nach dem autom. setzen der Kurve
        xlim = ax[0].get_xlim()
        width = xlim[1] + xlim[0]

        ylim = ax[0].get_ylim()
        height = ylim[1] + ylim[0]

        ax[0].text(
              width / 2, height / 10,
              #self.image.mm2dots_X(0), # x-Koordinate: 0 ganz links, 1 ganz rechts
              #self.image.mm2dots_Y(500), # y-Koordinate: 0 ganz oben, 1 ganz unten
              'crossline', # der Text der ausgegeben wird
              ha='center', # horizontalalignment
              va='center', # verticalalignment
              fontsize=20, #  'font' ist äquivalent
              alpha=.5 # Floatzahl von 0.0 transparent bis 1.0 opak
        )
        #ax[0].text(2.5, 2.5, 'horizontal', ha='center', va='center', size=20, alpha=.5)

        #ax[0].set_title('Horizontal')

        # 2. Kurve vertikal

        # label und Ticks abschalten
        # x-Achse
        ax[1].get_xaxis().set_ticklabels([])
        ax[1].get_xaxis().set_ticks( [] )
        # y-achse
        ax[1].get_yaxis().set_ticklabels([])
        ax[1].get_yaxis().set_ticks( [] )

        # Kurve plotten
        ax[1].plot(data["vertical"]['profile'].values, color='r')

        # links rechts min max
        ax[1].axhline(data["vertical"]['profile max'], color='g', linewidth=1)
        ax[1].axhline(data["vertical"]['profile min'], color='g', linewidth=1)
        ax[1].axvline(data["vertical"]['profile left'], color='g', linewidth=1, linestyle='-.')
        ax[1].axvline(data["vertical"]['profile right'], color='g', linewidth=1, linestyle='-.')

        fwxm_data = data["vertical"]['profile'].fwxm_data()
        cax_idx = fwxm_data["center index (rounded)"]      
        
        ax[1].axvline(cax_idx, color='g', linewidth=1, linestyle='-.')
        #ax[1].set_title('Vertikal')

        # limits nach dem autom. setzen der Kurve
        xlim = ax[0].get_xlim()
        width = xlim[1] + xlim[0]

        ylim = ax[0].get_ylim()
        height = ylim[1] + ylim[0]
        ax[1].text(
                width / 2, height / 10,
                #self.image.mm2dots_X(0),
                #self.image.mm2dots_Y(500),
                'inline',
                ha='center',
                va='center',
                size=20,
                alpha=.5
        )

        
        # Layout optimieren
        plt.tight_layout(pad=0.4, w_pad=1.0, h_pad=1.0)
        # data der Grafik zurückgeben
        return plot.getPlot()


    def find4Qdata( self, field=None ):
        """ Die transmissions eines 4 Quadranten Feldes im angegebenem Bereich ermitteln

        Reihenfolge in result 'Q2Q1','Q2Q3','Q3Q4','Q1Q4'

        [start:stop:step, start:stop:step ]

        roi = np.array([
            [11, 12, 13, 14, 15],
            [21, 22, 23, 24, 25],
            [31, 32, 33, 34, 35],
            [41, 42, 43, 44, 45],
            [51, 52, 53, 54, 55]])
        print( roi[ : , 0:1 ] )
            [[11] [21] [31] [41] [51]] -  ( 1 Line2D gezeichnet LU-RO)
        print( roi[ 0 ] )
            [11 12 13 14 15] -  ( 1 Line2D gezeichnet LU-RO)
        print( roi[ 0:1, ] )
            [[11 12 13 14 15]] - ( 5 Line2D nicht gezeichnet)
        print( roi[ 0:1, ][0] )
            [11 12 13 14 15] - ( 1 Line2D gezeichnet LU-RO)
        print( roi[ :, -1: ] )
            [[15] [25] [35] [45] [55]] -  ( 1 Line2D gezeichnet LU-RO)
        print( roi[ -1 ] )
            [51 52 53 54 55] -  ( 1 Line2D gezeichnet LU-RO)
        print( roi[ -1:, : ][0] )
            [51 52 53 54 55] -  ( 1 Line2D gezeichnet LU-RO)

        # richtungsumkehr
        print( roi[ ::-1, -1: ] )
            [[55] [45] [35] [25] [15]] -  ( 1 Line2D gezeichnet LO-RU)

        """
        if not field:
            field = { "X1":-50, "X2": 50, "Y1": -50, "Y2": 50 }

        roi = self.image.getRoi( field ).copy()


        result = {}

        result['Q2Q1'] = {
            'name' : 'Q2 - Q1',
            'profile' : MultiProfile( roi[:, 0:1] ),
            'field' : field
        }
        result['Q2Q3'] = {
            'name' : 'Q2 - Q3',
            'profile' : MultiProfile( roi[ 0:1, ][0] ),
            'field' : field
        }
        result['Q3Q4'] = {
            'name' : 'Q3 - Q4',
            'profile' : MultiProfile( roi[ :, -1: ] ),
            'field' : field
        }
        result['Q1Q4'] = {
            'name' : 'Q1 - Q4',
            'profile' : MultiProfile( roi[ -1:, : ][0] ),
            'field' : field
        }

        #print( result )

        for k in result:
            #print(k)
            p_min = np.min( result[k]["profile"] )
            p_max = np.max( result[k]["profile"] )

            result[k]["min"] = p_min
            result[k]["max"] = p_max
            result[k]["value"] = (lambda x: p_min if x < 0.9 else p_max )(p_min)


        return {
                'filename': self.infos["filename"],
                'Kennung': self.infos["Kennung"],
                'type': self.infos['testTags'],
                'unit':  self.infos['unit'],
                'energy': self.infos['energy'],
                'gantry' : self.infos['gantry'],
                'collimator': self.infos['collimator'],
                'field' : field,
                'result' : result
        }

    def plot4Qprofile( self, data , metadata={} ):
        """ Ein angegebenes 4Q Profil plotten

            Parameters
            ----------
            data : dict

        """

        # plotbereiche festlegen
        plot = plotClass( )
        fig, ax = plot.initPlot(  metadata["profileSize"] )
       # fig, ax = self.initPlot( metadata["profileSize"] )
        #print("plot4Qprofile", data)
        ax.set_title(data["name"])

        # kurve plotten
        ax.plot(data["profile"].values, color='b')

        # y Achsenlimit
        ax.set_ylim(0.5, 1.5)

        # x-Achse
        ax.get_xaxis().set_ticklabels([ data["name"][0:2], data["name"][-2:] ])
        ax.get_xaxis().set_ticks( [0, len(data["profile"].values) ] )

        # y-achse anzeigen
        ax.get_yaxis().set_ticklabels( [0.75, 1, 1.25] )
        ax.get_yaxis().set_ticks( [0.75, 1, 1.25] )

        # grid anzeigen
        ax.grid( True )

        plt.tight_layout(pad=0.4, w_pad=0.5, h_pad=1.0)
        # data der Grafik zurückgeben
        return plot.getPlot()


class checkField( ispBase ):

    def _doField_one2n(self, fileData, md={}, passedOn=True, withOffsets=False):
        """

        TODO: query aus tolerance?
            openFieldQuery = md.current.tolerance.default.check.query
            fieldQuery = openFieldQuery.replace("==", "!=")

        Parameters
        ----------
        fileData : TYPE
            DESCRIPTION.
        overrideMD : TYPE, optional
            DESCRIPTION. The default is {}.
        passedOn : TYPE, optional
            DESCRIPTION. The default is True.
        withOffsets : TYPE, optional
            DESCRIPTION. The default is False.

        Returns
        -------
        TYPE
            DESCRIPTION.
        result : TYPE
            DESCRIPTION.

        """
        # used on progress
        filesMax=len( fileData )
        self.fileCount = 0
        # holds evaluation results
        result=[]

        # prepare metadata
        md = dict_merge( DotMap( md ), self.metadata )

        #md.pprint(pformat='json')

        def evaluate( df_group ):
            """Evaluate grouped Fields.

            create PDF output and fills result

            Parameters
            ----------
            df_group : pandas Dataframe

            """
            # get base and fields check number of data
            ok, df_base, df_fields = self.evaluationPrepare(df_group, md, result)
            if not ok:
                return

            # base Field und dosis bereitstellen
            baseField = qa_field( self.getFullData( df_base.loc[df_base.index[0]] ) )
            baseMeanDose = baseField.getMeanDose( md["doseArea"] )

            #
            evaluation_table = [ {
                'Kennung': baseField.infos["RadiationId"],
                'doserate': baseField.infos["doserate"],
                'ME': baseField.infos["ME"],
                'baseME': baseField.infos["ME"],
                'baseMeanDose': 1,
                'fieldMeanDose': baseMeanDose
            }]

            # print BaseField Image
            img = baseField.image.plotImage( **md.plotImage )
            self.pdf.image(img, **md.plotImage_pdf )

            # alle anderen durchgehen
            for info in df_fields.itertuples():
                # prüf Field und dosis bereitstellen
                checkField = qa_field( self.getFullData(info), normalize="none" )
                fieldMeanDose = checkField.getMeanDose( md["doseArea"] )

                #
                evaluation_table.append( {
                      'Kennung': checkField.infos["Kennung"],
                      'doserate': checkField.infos["doserate"],
                      'ME': checkField.infos["ME"],
                      'baseME': baseField.infos["ME"],
                      'baseMeanDose': baseMeanDose,
                      'fieldMeanDose': fieldMeanDose
                } )

                if md["print_all_images"] == True:
                    # print checkField Image
                    img = checkField.image.plotImage( **md.plotImage )
                    self.pdf.image(img, **md.plotImage_pdf )

                # progress
                self.fileCount += 1
                if hasattr( logger, "progress"):
                    logger.progress( md["testId"],  40 + ( 40 / filesMax * self.fileCount ) )

            evaluation_df = pd.DataFrame( evaluation_table )

            # check tolerance - printout tolerance, evaluation_df and result icon
            acceptance = self.evaluationResult( evaluation_df, md, result, md["tolerance_field"] )

        #
        # call evaluate with sorted and grouped fields
        fileData.sort_values(md["series_sort_values"]).groupby( md["series_groupby"] ).apply( evaluate )

        #print("one2n", result)
        return self.pdf.finish(), result


    def doJT_end2end( self, filedata ):
        """
        .. note:: Test noch nicht erstellt
        """
        pass

    def doMT_4_1_2(self, fileData):
        """Monatstest: 4.1.2.  ()

        - Gruppiert nach Doserate, sortiert nach MU
        -

        Parameters
        ----------
        fileData : pandas.DataFrame

        Returns
        -------
        pdfFilename : str
            Name der erzeugten Pdfdatei
        result : list
            list mit dicts der Testergebnisse

        """
        # used on progress
        filesMax=len( fileData )
        self.fileCount = 0
        # holds evaluation results
        result=[]

        # place for testing parameters
        md = dict_merge( DotMap( {

        } ), self.metadata )

        #md.pprint(pformat='json')

        def groupBySeries( df_group ):
            """Datumsweise Auswertung und PDF Ausgabe
            Die Daten kommen nach doserate und ME sortiert
            """
            #print("doMT_7_2", df_group[ ["energy", "doserate", "ME"] ] )

            # get base and fields check number of data
            ok, df_base, df_fields = self.evaluationPrepare(df_group, md, result)
            if not ok:
                return

            result_doserate = []

            def groupByDoserate( df_doserate ):                
                text = ""
                # in den Toleranzangaben der config steht die default query
                openFieldQuery = md.current.tolerance.default.check.query
                fieldQuery = openFieldQuery.replace("==", "!=")
                #print( openFieldQuery, fieldQuery )

                # das offene Feld bestimmen
                df_base = df_doserate.query( openFieldQuery )

                # base Field und dosis bereitstellen
                baseField = qa_field( self.getFullData( df_base.loc[df_base.index[0]] ), normalize="none" )
                baseMeanDose = baseField.getMeanDose( md["doseArea"] )

                # 100  referenz Dose 1.0
                data = [ {
                    'Kennung': baseField.infos["RadiationId"],
                    'doserate': baseField.infos["doserate"],
                    'ME': baseField.infos["ME"],
                 #   'baseMeanDose': baseMeanDose,
                    'fieldMeanDose': baseMeanDose,
                    'diff': (baseMeanDose - 1.0) * 100

                }]

                # alle anderen filtern
                df_fields = df_doserate.query( fieldQuery )

                # alle anderen durchgehen
                for info in df_fields.itertuples():
                    # prüft Field und dosis bereitstellen
                    checkField = qa_field( self.getFullData(info), normalize="none" )

                    # Berechnung der mittleren Felddosis
                    fieldMeanDose = checkField.getMeanDose( md["doseArea"] )

                    # Berechnung
                    baseFmu = baseMeanDose / baseField.infos['ME'] * checkField.infos['ME']

                    data.append( {
                      'Kennung': checkField.infos["RadiationId"],
                      'doserate': checkField.infos["doserate"],
                      'ME': checkField.infos["ME"],
                      'fieldMeanDose': fieldMeanDose,
                      'diff': (fieldMeanDose - baseFmu) / baseFmu * 100,
                    } )

                    # progress
                    self.fileCount += 1
                    if hasattr( logger, "progress"):
                        logger.progress( md["testId"],  40 + ( 40 / filesMax * self.fileCount ) )

                # aus den daten ein DataFrame machen
                evaluation_df = pd.DataFrame( data )
                # check tolerance - printout tolerance, evaluation_df -  md["tolerance_field"],
                acceptance = self.evaluationResult( evaluation_df, md, result_doserate, printResultIcon=False )
                # acceptance dieser Gruppe zurückgeben
                return acceptance

            #
            # Gruppiert nach doserate abarbeiten und min zurückgeben
            acceptance = df_group.groupby( [ "doserate" ] ).apply( groupByDoserate ).min()

            #
            # Ergebnis in result merken
            #
            result.append( self.createResult( result_doserate, md, [],
                df_group['AcquisitionDateTime'].iloc[0].strftime("%Y%m%d"),
                len( result ), # bisherige Ergebnisse in result
                acceptance
            ) )

            # Gesamt check - das schlechteste von result_doserate
            self.pdf.resultIcon( acceptance )

        #
        # Gruppiert nach SeriesNumber abarbeiten
        fileData.sort_values( md["series_sort_values"] ).groupby( md["series_groupby"] ).apply( groupBySeries )

        # abschließen pdfdaten und result zurückgeben
        return self.pdf.finish(), result

    def doJT_7_2(self, fileData):
        """Jahrestest: 7.2.  ()
        Abhängigkeit der Kalibrierfaktoren von der Monitorrate
        """

        # place for testing parameters
        md = dict_merge( DotMap( {

        } ), self.metadata )

        return self._doField_one2n(fileData, md=md )


    def doJT_7_3(self, fileData):
        """Jahrestest: 7.3.  ()
        Abhängigkeit der Kalibrierfaktoren vom Dosismonitorwert
        """
        # place for testing parameters
        md = dict_merge( DotMap( {

        } ), self.metadata )

        return self._doField_one2n(fileData, md=md )

    def doJT_7_4(self, fileData):
        """Jahrestest: 7.4.  ()
        Abhängikeit Kalibrierfaktoren vom Tragarm Rotationswinkel
        10x10 Feld unter 0° mit Aufnahmen unter 90, 180, 270 vergleichen
        Auswertung in einer ROI von 10mmx10mm

        Energie: alle

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
        # used on progress
        filesMax=len( fileData )
        self.fileCount = 0
        # holds evaluation results
        result=[]

        # prepare metadata
        md = dict_merge( DotMap( {
            "series_sort_values": ["gantry", "collimator"],
            "series_groupby": ["day", "SeriesNumber"],
            "querys" : {
                "base" : "gantry == 0 & collimator == 0",
                "fields" : "gantry != 0 | collimator != 0",
            },
            # "field_count": 3,
            "manual": {
                "filename": self.metadata.info["anleitung"],
                "attrs": {"class":"layout-fill-width"},
            },
            "tolerance_pdf" : {
                "attrs": {"margin-top":"-2mm"},
                "mode": "text"
            },

            "doseArea" : { "X1":-5, "X2": 5, "Y1": -5, "Y2": 5 },
            "_imgSize" : { "width" : 80, "height" : 80},
            "plotImage_field" : 10,
            "evaluation_table_pdf" : {
                "attrs": { "class":"layout-fill-width", "margin-top": "5mm" },
                "fields": [
                    {'field': 'Kennung', 'label':'Kennung', 'format':'{0}', 'style': [('text-align', 'left')] },
                    {'field': 'gantry', 'label':'Gantry', 'format':'{0:1.1f}' },
                    {'field': 'collimator','label':'Kollimator', 'format':'{0:1.1f}' },
                    {'field': 'baseMeanDose', 'label':'Dosis', 'format':'{0:.5f}' },
                    {'field': 'fieldMeanDose', 'label':'Prüf Dosis', 'format':'{0:.5f}' },
                    {'field': 'diff', 'label':'Abweichung [%]', 'format':'{0:.2f}' },
                    {'field': 'diff_passed', 'label':'Passed' }
                ],
            },
            "table_sort_values_by": ["doserate"],
            "table_sort_values_ascending": [True],

        } ), self.metadata )


        def evaluate( df_group ):
            """Evaluate grouped Fields

            create PDF output and fills result

            Parameters
            ----------
            df_group : pandas Dataframe

            """

            # get base and fields, check number of data
            ok, df_base, df_fields = self.evaluationPrepare(df_group, md, result)
            if not ok:
                return

            # base Field und dosis bereitstellen
            baseField = qa_field( self.getFullData( df_base.loc[df_base.index[0]] ) )
            baseMeanDose = baseField.getMeanDose( md["doseArea"] )

            data = [{
                'Kennung': baseField.infos["Kennung"],
                'gantry': baseField.infos["gantry"],
                'collimator': baseField.infos["collimator"],
                'baseMeanDose': baseMeanDose,
                'fieldMeanDose': np.nan,
                'diff': np.nan,
            }]

            # Bild anzeigen
            img = baseField.image.plotImage( original=False
                        , plotTitle="{Kennung} - G:{gantry:01.1f} K:{collimator:01.1f}"
                        , field=md["plotImage_field"]
                        , invert=False # , cmap="jet"
                        , plotCax=True, plotField=True
                    )
            self.pdf.image(img, md["_imgSize"], attrs={"margin-left":"5mm"} )

            # alle anderen durchgehen
            for info in df_fields.itertuples():
                # prüf Field und dosis bereitstellen
                checkField = qa_field( self.getFullData(info), normalize="none" )
                fieldDose = checkField.getMeanDose( md["doseArea"] )
                #
                data.append( {
                      'Kennung': checkField.infos["Kennung"],
                      'gantry': checkField.infos["gantry"],
                      'collimator': checkField.infos["collimator"],
                      'baseMeanDose': np.nan,
                      'fieldMeanDose': fieldDose,
                      'diff': (fieldDose-baseMeanDose) / baseMeanDose * 100,
                } )
                # Bild anzeigen
                img = checkField.image.plotImage( original=False
                            , plotTitle="{Kennung} - G:{gantry:01.1f} K:{collimator:01.1f}"
                            , field=md["plotImage_field"]
                            , invert=False # , cmap="jet"
                            , plotCax=True, plotField=True
                        )
                self.pdf.image(img, md["_imgSize"], attrs={"margin-left":"5mm"} )

                # progress pro file stimmt nicht immer genau (baseimage)
                # 40% für die dicom daten 40% für die Auswertung 20 % für das pdf
                self.fileCount += 1
                if hasattr( logger, "progress"):
                    logger.progress( md["testId"], 40 + ( 40 / filesMax * self.fileCount ) )

            evaluation_df = pd.DataFrame( data )

            # check tolerance - printout tolerance, evaluation_df and result icon
            acceptance = self.evaluationResult( evaluation_df, md, result, 'diff' )

        #
        # call evaluate with sorted and grouped fields
        fileData.sort_values(md["series_sort_values"]).groupby( md["series_groupby"] ).apply( evaluate )

        # abschließen pdfdaten und result zurückgeben
        return self.pdf.finish(), result

    def doJT_7_5(self, fileData):
        """Jahrestest: 7.5.  ()

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
        # used on progress
        filesMax=len( fileData )
        self.fileCount = 0
        # holds evaluation results
        result=[]

        # prepare metadata
        md = dict_merge( DotMap( {
            "series_sort_values": ["gantry", "StopAngle"],
            "series_groupby": ["day"],
            "sub_series_groupby": ["energy"],
            "querys" : {
                "base" : "GantryRtnDirection == 'NONE'",
                "fields" : "GantryRtnDirection != 'NONE'",
                "sub_base" : "GantryRtnDirection == 'NONE'",
                "sub_fields" : "GantryRtnDirection != 'NONE'",
            },
            "manual": {
                "filename": self.metadata.info["anleitung"],
                "attrs": {"class":"layout-fill-width", "margin-bottom": "5mm"},
            },
            "doseArea" : { "X1":-5, "X2": 5, "Y1": -5, "Y2": 5 },
            "plotImage": {
                "original": False,
                "plotTitle": "{Kennung} - G:{von_nach}",
                "field": 10,
                "invert": True,
                "cmap": "gray_r", # gray_r twilight jet
                "plotCax": True,
                "plotField": True
            },
            "plotImage_pdf": {
                "area" : { "width" : 90, "height" : 90 },
                #"attrs": "",
            },

            "evaluation_table_pdf" : {
                "attrs": { "class":"layout-fill-width", "margin-top": "5mm" },
                "fields": [
                    {'field': 'Kennung', 'label':'Kennung', 'format':'{0}', 'style': [('text-align', 'left')] },
                 #   {'field': 'ME', 'label':'MU' },
                    {'field': 'von_nach', 'label':'Gantry' },
                    {'field': 'baseMeanDose', 'label':'Dosis', 'format':'{0:.5f}' },
                    {'field': 'fieldMeanDose', 'label':'Prüf Dosis', 'format':'{0:.5f}' },
                    {'field': 'diff', 'label':'Abweichung [%]', 'format':'{0:.2f}' },
                    {'field': 'diff_passed', 'label':'Passed' }
                ],
            },

            "table_sort_values_by": ["ME"],
            "table_sort_values_ascending": [True],

        } ), self.metadata )
        # alte Auswertung
        pre2020 = False
        if md.get("AcquisitionYear", 0) < 2020:
            md.evaluation_text = ""
            md.tolerance_pdf.mode = "text"
            pre2020 = True

        #md.pprint(pformat='json')

        def evaluate( df_group ):
            """Evaluate grouped Fields

            create PDF output and fills result

            Parameters
            ----------
            df_group : pandas Dataframe


            felder unter 0° sind basis für die winkel felder
            Auswertung je doserate
            """
            # get base and fields, check number of data
            ok, df_base, df_fields = self.evaluationPrepare(df_group, md, result)
            if not ok:
                return

            data = []
            # gruppiert nach gantry und kollimator
            def sub_evaluate( df ):
                # get base and fields, check number of data
              #  print("doJT_7_5", df[ [ "RadiationId", "gantry", "StopAngle", "collimator", "ME", "doserate", "check_subtag" ] ])
                df_base = df.query( md.querys[ "sub_base"] )
                df_fields = df.query( md.querys[ "sub_fields"] )

                # base Field und dosis bereitstellen
                baseField = qa_field( self.getFullData( df_base.loc[df_base.index[0]] ) )
                baseMeanDose = baseField.getMeanDose( md["doseArea"] )

                # zusätzliche Spalte in fields anlegen
                df_fields["von_nach"] = df_group[['gantry','StopAngle']].apply(lambda x : '{:.1f} -> {:.1f}'.format(x[0],x[1]), axis=1)

                if pre2020 == True:
                    data.append({
                        'Kennung': baseField.infos["Kennung"],
                        'von_nach': "{:01.1f}".format( baseField.infos["gantry"] ),
                        'ME': baseField.infos["ME"],
                        'baseMeanDose': baseMeanDose,
                        'fieldMeanDose': np.nan,
                        'diff': np.nan,
                    })
                # alle Felder durchgehen
                for info in df_fields.itertuples():
                    # prüf Field und dosis bereitstellen
                    checkField = qa_field( self.getFullData(info), normalize="none" )
                    fieldDose = checkField.getMeanDose( md["doseArea"] )
                    #
                    if pre2020 == True:
                        data.append({
                              'Kennung': checkField.infos["Kennung"],
                              'von_nach': checkField.infos["von_nach"],
                              'ME': checkField.infos["ME"],
                              'baseMeanDose': np.nan,
                              'fieldMeanDose': fieldDose,
                              'diff': (fieldDose-baseMeanDose) / baseMeanDose * 100,
                        })
                    else:
                        data.append({
                              'Kennung': checkField.infos["Kennung"],
                              'von_nach': checkField.infos["von_nach"],
                              'ME': checkField.infos["ME"],
                              'baseMeanDose': baseMeanDose,
                              'fieldMeanDose': fieldDose,
                        })
                    # Bild anzeigen
                    img = checkField.image.plotImage( **md["plotImage"] )
                    self.pdf.image(img, **md["plotImage_pdf"] )

                    # progress pro file stimmt nicht immer genau (baseimage)
                    # 40% für die dicom daten 40% für die Auswertung 20 % für das pdf
                    self.fileCount += 1
                    if hasattr( logger, "progress"):
                        logger.progress( md["testId"],  40 + ( 40 / filesMax * self.fileCount ) )

            # sub evaluate
            #
            df_group.groupby( md["sub_series_groupby"] ).apply( sub_evaluate )

            evaluation_df = pd.DataFrame( data )

            # check tolerance - printout tolerance, evaluation_df and result icon
            acceptance = self.evaluationResult( evaluation_df, md, result, 'diff' )

        # call evaluate with sorted and grouped fields
        fileData.sort_values(md["series_sort_values"]).groupby( md["series_groupby"] ).apply( evaluate )

        # abschließen pdfdaten und result zurückgeben
        return self.pdf.finish(), result

    def doJT_9_1_2(self, fileData):
        """Jahrestest: 9.1.2.  ()
        Abhängigkeit der Variation des Dosisquerprofils vom Tragarm-Rotationswinkel
        DIN 6847-5:2013; DIN EN 60976: 2011-02
        30x30 Feld bei im Bereich 80% der Feldbreite max-min/Wert im Zentralstrahl Bereich von 2mm"

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
        # used on progress
        filesMax=len( fileData )
        self.fileCount = 0
        # holds evaluation results
        result=[]

        # prepare metadata
        md = dict_merge( DotMap( {
            "series_sort_values": ["gantry"],
            "series_groupby": ["day"],
            "querys" : {
                "fields" : "check_subtag != 'base'",
              #  "field_count": self.metadata.current.get("fields", 0), # 4
            },
            "manual": {
                "filename": self.metadata.info["anleitung"],
                "attrs": {"class":"layout-fill-width", "margin-bottom": "5mm"},
            },
            "_clip" : { "width":"50mm", "height":"45mm" },
            "_formel": { "margin-top":"15mm", "width":"21mm", "height":"11mm"},
            "_table": { "width":105, "height": 45, "left":75, "top":215 },
            "_chart" : {"width" : 90, "height" : 70},
            "profileSize" : { "width" : 90, "height" : 70 },
            "profileTitle" : "Gantry: {gantry}°",
            "table_fields" : [
                {'field': 'gantry', 'label':'Gantry', 'format':'{0:.1f}' },
                {'field': 'crossline', 'label':'crossline [%]', 'format':'{0:.1f}' },
               # {'field': 'crossline_soll', 'label':'c-soll [%]', 'format':'{0:.1f}' },
                {'field': 'c_soll', 'label':'c-soll [%]', 'format':'{0:.1f}' },

                {'field': 'crossline_acceptance', 'label':'c-abw.[%]', 'format':'{0:.3f}' },
                {'field': 'inline', 'label':'inline [%]', 'format':'{0:.1f}' },
               # {'field': 'inline_soll', 'label':'i-soll [%]', 'format':'{0:.1f}' },
                {'field': 'i_soll', 'label':'i-soll [%]', 'format':'{0:.1f}' },
                {'field': 'inline_acceptance', 'label':'i-abw.[%]', 'format':'{0:.3f}' },
               # {'field': 'i_diff', 'label':'i-abw.[%]', 'format':'{0:.3f}' }

            ]
        } ), self.metadata )



        # tolerance Werte bereitstellen
        #toleranz = {}
        #if "toleranz" in md["testConfig"] and md["energy"] in md["testConfig"]["toleranz"]:
        #    toleranz = md["testConfig"]["toleranz"][ md["energy"] ]

        def evaluate( df_group ):
            """Datumsweise Auswertung
            """

            # get base and fields check number of data
            ok, df_base, df_fields = self.evaluationPrepare(df_group, md, result)
            if not ok:
                return

            data = []
            # alle Felder durchgehen
            for info in df_group.itertuples():

                checkField = qa_field( self.getFullData( info ), normalize="none" )

                # Analyse nach DIN (max-min)/center rückgabe in valueiec
                profile = checkField.getProfileData()
                # crossplane und inplane
                c = profile["flatness"]["horizontal"]
                i = profile["flatness"]["vertical"]
                # key für tolerance
                #sollKeyC = "{gantry:1.0f}-cl".format( **checkField.infos )
                #sollKeyI = "{gantry:1.0f}-il".format( **checkField.infos )
                #sollKey = "{gantry:1.0f}-cl".format( **checkField.infos )

                # Bild anzeigen
                img =  checkField.plotProfile( profile["flatness"], metadata=md )
                self.pdf.image(img, md["_chart"], {"padding":"2mm 0 2mm 0"} )

                data.append( {
                    'gantry' : checkField.infos["gantry"],
                    'crossline': c["value"],
                    'c_soll'  : 5,
                    #'c_soll' : toleranz.get( sollKeyC, np.nan ),
                    'inline': i["value"],
                    'i_soll' :  5,
                    #'i_soll' : toleranz.get( sollKeyI, np.nan ),
                } )

                # progress pro file stimmt nicht immer genau (baseimage)
                # 40% für die dicom daten 40% für die Auswertung 20 % für das pdf
                self.fileCount += 1
                if hasattr( logger, "progress"):
                    logger.progress( md["testId"],  40 + ( 40 / filesMax * self.fileCount ) )

            # Grafik und Formel anzeigen
            self.pdf.image( "qa/Profile.svg", attrs=md["_clip"])
            self.pdf.mathtext( r"$\frac{D_{max} - D_{min}} {D_{CAX}}$", attrs=md["_formel"]  )


            # dataframe erstellen
            df = pd.DataFrame( data )
            # berechnete Splaten einfügen
            #df['c_diff'] = (df.crossline - df.c_soll ) / df.c_soll * 100
            #df['i_diff'] = (df.inline - df.i_soll ) / df.i_soll * 100


            #
            # Abweichung ausrechnen und Passed setzen
            #
            check = [
                { "field": 'crossline', 'tolerance':'default' },
                { "field": 'inline', 'tolerance':'default' }
            ]
            acceptance = self.check_acceptance( df, md, check, withSoll=True )

            #print( df.columns )
            # 'gantry', 'crossline', 'inline', 'crossline_soll',
            # 'crossline_acceptance', 'crossline_passed', 'inline_soll',
            # 'inline_acceptance', 'inline_passed'

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
                area=md["_table"],
                attrs={"class":"layout-fill-width", "margin-top": "5mm"},
                fields=md["table_fields"]
            )

            # Gesamt check - das schlechteste aus der tabelle
            self.pdf.resultIcon( acceptance )

        #
        # call evaluate with sorted and grouped fields
        fileData.sort_values(md["series_sort_values"]).groupby( md["series_groupby"] ).apply( evaluate )
        # fileData.sort_values(["gantry"]).groupby( [ 'day' ] ).apply( groupBySeries )
        # abschließen pdfdaten und result zurückgeben
        return self.pdf.finish(), result

    def doJT_10_3(self, fileData ):
        """Jahrestest: 10.3.  ( Vierquadrantentest)
        Das zusammengesetzte Feld mit dem Full Feld vergleichen
        5cm Profil über die Mitte je zwei zusammengesetzter Bereiche

        davon min/mean max/mean  wobei Mean des gleichen Profils aus dem Full Feld kommt

        In den Übergängen ca 70% des vollen Feldes

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
        # used on progress
        filesMax=len( fileData )
        self.fileCount = 0
        # holds evaluation results
        result=[]

        # prepare metadata
        md = dict_merge( DotMap( {
            "series_sort_values" : ['check_subtag'],
            "series_groupby": ["day", "SeriesNumber"],
            "querys" : {
                "base": "check_subtag.isnull()",
                "fields": "check_subtag.notnull()",
                "engine": "python"
              #  "field_count": self.metadata.current.get("fields", 0), # 5
            },
            "manual": {
                "filename": self.metadata.info["anleitung"],
                "attrs": {"class":"layout-fill-width", "margin-bottom": "5mm"},
            },
            "_chart" : {"width" : 90, "height" : 50},
            "_imgSize" : {"width" : 120, "height" : 120},
            "_image_attrs" : { "margin-top": "5mm" },

            "field" : { "X1":-110, "X2": 110, "Y1": -110, "Y2": 110 },
            "evaluation_table_pdf" : {
                "fields": [
                    {'field': 'name', 'label':'von - nach' },
                    {'field': 'value', 'label':'Wert', 'format':'{0:.3f}' },
                    {'field': 'value_passed', 'label':'Passed' }
                ],
                "area": {"left" : 125, "top" : 165, "width": 50},
                "attrs": {"class":"layout-fill-width"},
            },
            "evaluation_replaces" : {"value":"Wert"},

            "tolerance_pdf": {
                "area" : { "left" : 10, "top" : 240, "width": 180},
                "mode" : "text"
            },
            "tolerance_field": "value"
        } ), self.metadata )

        #print("doJT_10_3-current", md.current )

        def evaluate( df_group ):
            """Evaluate grouped Fields.

            create PDF output and fills result

            Parameters
            ----------
            df_group : pandas Dataframe

            """

            # get base and fields check number of data
            ok, df_base, df_fields = self.evaluationPrepare(df_group, md, result)
            if not ok:
                return

            # base Field und dosis bereitstellen
            baseField = qa_field( self.getFullData( df_base.loc[df_base.index[0]] ) )

            sumfield = []
            # alle Felder durchgehen
            for (idx, info) in df_fields.iterrows():
                checkField = qa_field( self.getFullData(info), normalize="none" )
                if len(sumfield) == 0:
                    sumfield = checkField.image.array
                else:
                    sumfield = np.add( sumfield, checkField.image.array )

                # progress
                self.fileCount += 1
                if hasattr( logger, "progress"):
                    logger.progress( md["testId"],  40 + ( 40 / filesMax * self.fileCount ) )

            # das baseField durch das normalisierte Summenfeld erstezen
            baseField.image.array = np.divide( sumfield, baseField.image.array + 0.00000001 )

            # baseField auswerten
            data4q = baseField.find4Qdata()
            evaluation_df = pd.DataFrame( data4q['result'] ).T

            # alle vier Quadranten durchgeghen
            for k, item in data4q["result"].items():
                # plot des Quadranten
                img =  baseField.plot4Qprofile( item, metadata=md )
                self.pdf.image(img, md["_chart"] )

            #
            # Bild mit Beschriftung anzeigen
            #
            def addToPlot( **args ):

                self = args["self"]
                ax = args["ax"]
                # print( args["field"] )
                da = self.getFieldDots( {
                    "X1": args["field"]["X1"] - 20,
                    "X2": args["field"]["X2"] + 20,
                    "Y1": args["field"]["Y1"] - 20,
                    "Y2": args["field"]["Y2"] + 20
                } )

                style = dict(size=40, color='green', ha='center', va='center', alpha=.9)

                ax.text( da["X1"] , da["Y1"] , 'Q1', **style)
                ax.text( da["X1"] , da["Y2"] , 'Q2', **style)
                ax.text( da["X2"] , da["Y2"] , 'Q3', **style)
                ax.text( da["X2"] , da["Y1"] , 'Q4', **style)

            img = baseField.image.plotImage(
                    original=False
                    , invert=False
                    , plotTitle=False
                    , plotCax=False
                    , plotField=data4q["field"]
                    , field=md["field"]
                    , plotTicks=True
                    , metadata=md
                    , arg_function=addToPlot, arg_dict=data4q
                )
            self.pdf.image(img, md["_imgSize"], attrs=md["_image_attrs"]  )

           # print("doJT_10_3", md.current, evaluation_df )
            # check tolerance - printout tolerance, evaluation_df and result icon
            acceptance = self.evaluationResult( evaluation_df, md, result, md["tolerance_field"] )

        #
        # Sortiert nach check_subtag
        # Gruppiert nach Tag und SeriesNumber abarbeiten
        #
        ( fileData
             .sort_values( md["series_sort_values"], na_position='first')
             .groupby( md[ "series_groupby" ] )
             .apply( evaluate )
        )
        # abschließen pdfdaten und result zurückgeben
        return self.pdf.finish(), result


    def doMT_VMAT_0_1( self, fileData ):
        """PicketFence DMLC Dosimetrie eines 40x100 großen Feldes

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
        md = dict_merge( DotMap( {
            "series_sort_values": ["MLCPlanType", "gantry"],
            "series_groupby": ["day", "SeriesNumber"],
            "current": {
                "field_count": self.metadata.current.get("fields", 0) - 1, # 4
            },
            "querys" : {
                "base" : 'MLCPlanType!="DynMLCPlan"', # "check_subtag == 'base'",
                "fields" : 'MLCPlanType=="DynMLCPlan"', # "check_subtag != 'base'",
            },
            "manual": {
                "filename": self.metadata.info["anleitung"],
                "attrs": {"class":"layout-fill-width", "margin-bottom": "5mm"},
            },

            "doseArea" : { "X1":-0.75, "X2": 0.75, "Y1": -4, "Y2": 4 },
            "_imgSize" : {"width" : 36, "height" : 70},
            "_imgField": {"border": 10 },
            "_chart": { "width" : 180, "height" : 60},
            "table_fields" : [
                {'field': 'Kennung', 'label':'Kennung', 'format':'{0}', 'style': [('text-align', 'left')] },
                {'field': 'gantry', 'label':'Gantry', 'format':'{0:1.1f}' },
             #   {'field': 'Mof', 'label':'M<sub>OF</sub>', 'format':'{0:.5f}' },
                {'field': 'Mcorr', 'label':'M<sub>corr</sub>', 'format':'{0:.4f}' },
                {'field': 'Mdev', 'label':'M<sub>dev</sub> [%]', 'format':'{0:.2f}' },
                {'field': 'Mdev_passed', 'label':'Passed' },
            ]
        } ), self.metadata )


        def groupBySeries( df_group ):
            """Datumsweise Auswertung und PDF Ausgabe.

            """
            # get base and fields check number of data
            ok, df_base, df_fields = self.evaluationPrepare(df_group, md, result)
            if not ok:
                return

            # base Field und dosis bereitstellen
            baseField = qa_field( self.getFullData( df_base.loc[df_base.index[0]] ) )

            
            data = [{
                    'Kennung': baseField.infos["Kennung"],
                    'gantry': baseField.infos["gantry"],
                    'Mcorr': np.nan,
                    'Mdev': np.nan,
                    'Passed' : np.nan
            }]
            img = baseField.image.plotImage( original=False
                        , field = md["_imgField"]
                        , metadata = md
                        , plotTitle = "{Kennung}"
                        , invert=False, plotCax=False, plotField=True )
            # Bild anzeigen
            self.pdf.image( img, md["_imgSize"] )

            Mof = baseField.image.getRoi( md["doseArea"] ).copy()

            # alle felder durchgehen
            for info in df_fields.itertuples():

                field = qa_field( self.getFullData( info ) )

                img = field.image.plotImage( original=False
                            , field = md["_imgField"]
                            , metadata = md
                            , plotTitle = "{Kennung}"
                            , invert=False, plotCax=False, plotField=True )
                # Bild anzeigen
                self.pdf.image( img, md["_imgSize"] )

                #Mdmlc = field.getMeanDose( md["doseArea"] )
                Mdmlc = field.image.getRoi( md["doseArea"] ).copy()
                Mcorr = (Mdmlc / Mof).mean()

                data.append( {
                    'Kennung': field.infos["Kennung"],
                    'gantry': field.infos["gantry"],
                    'Mcorr': Mcorr,
                    'Mdev': np.nan,
                    'Pass' : np.nan
                } )

                # progress pro file stimmt nicht immer genau (baseimage)
                # 40% für die dicom daten 40% für die Auswertung 20 % für das pdf
                self.fileCount += 1
                if hasattr( logger, "progress"):
                    logger.progress( md["testId"],  40 + ( 40 / filesMax * self.fileCount ) )

            df = pd.DataFrame( data )
            McorrMean = df['Mcorr'].mean( )
            df[ 'Mdev' ] = (df[ 'Mcorr' ] - McorrMean ) / McorrMean * 100

            #
            # Abweichung ausrechnen und Passed setzen
            #
            check = [
                { "field": 'Mdev', 'tolerance':'default' }
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

            # Formel
            self.pdf.mathtext( r"Berechnung des Flatness-korrigierten Bildes: $M_{corr,i}(x,y) = \frac{M_{DMLC,i}(x,y)}{M_{OF}(x,y)}$", attrs={ "margin-top": "5mm" }  )
            self.pdf.mathtext( r"Dosimetrische Abweichung aus den ROI-Mittelwerten: $M_{dev,i} = \frac{\overline{M_{corr,i}}-\overline{M_{corr}}}{\overline{M_{corr}}}$", attrs={ "margin-top": "5mm" }  )

            #
            # Tabelle erzeugen
            #
            self.pdf.pandas( df,
                attrs={"class":"layout-fill-width", "margin-top": "5mm"},
                fields=md["table_fields"]
            )

            text_values = {
                "f_warning": md.current.tolerance.default.warning.get("f",""),
                "f_error": md.current.tolerance.default.error.get("f","")
            }
            text = """<br>
                Warnung bei: <b style="position:absolute;left:45mm;">{f_warning}</b><br>
                Fehler bei: <b style="position:absolute;left:45mm;">{f_error}</b>
            """.format( **text_values ).replace("{value}", "M<sub>dev</sub>")
            self.pdf.text( text )

            # Gesamt check
            self.pdf.resultIcon( acceptance )


        #
        # Gruppiert nach SeriesNumber abarbeiten
        #
        fileData.sort_values(["MLCPlanType", "gantry"], na_position='first').groupby( [ 'day', 'SeriesNumber' ] ).apply( groupBySeries )
        # abschließen pdfdaten und result zurückgeben
        return self.pdf.finish(), result

    def doMT_8_02_5(self, fileData ):
        """
        Die jeweilig gleichen Gantry und Kolliwinkel übereinanderlegen und mit dem offenem Feld vergleichen

            # Anzahl der Felder gesamt - MLCPlanType nicht None
            count_0 = len(df) - df["MLCPlanType"].count()
            count_other = len( df ) - count_0
            if count_0 != 1 and count_other != 4:
                print( "Falsche Anzahl der Felder offen:{} other:{}".format( count_0, count_other) )
                return

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
        # used on progress
        filesMax=len( fileData )
        self.fileCount = 0
        # holds evaluation results
        result=[]

        # prepare metadata
        md = dict_merge( DotMap( {
            "manual": {
                "filename": self.metadata.info["anleitung"],
                "attrs": {"class":"layout-fill-width"},
            },
            "_imgSize" : {"width" : 45, "height" : 45},
            "fieldArea" : { "X1":-80, "X2":80, "Y1": -80, "Y2":80, "xStep":20, "yStep":20 },
            "doseArea" : { "X1": -60, "X2": 60, "Y1": -60, "Y2": 60 },
            "table_fields": [
                {'field': 'gantry', 'label':'Gantry', 'format':'{0:1.1f}' },
                {'field': 'collimator', 'label':'Kollimator', 'format':'{0:1.1f}' },
                {'field': 'basedose', 'label':'Ref. Dosis', 'format':'{0:1.4f}' },
                {'field': 'fielddose', 'label':'Feld Dosis', 'format':'{0:1.4f}' },
                {'field': 'diff', 'label':'Diff [%]', 'format':'{0:1.2f}' },
                {'field': 'diff_passed', 'label':'Passed' }
            ]
        } ), self.metadata )

        # für jeden datensatz
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

            #print( df.query("CollMode == 'Symmetry'") )
            # es muss ein symetrisches basis Feld geben
            df_sym = df_group.query("CollMode == 'Symmetry'")

            if len(df_sym) != 1:
                result.append( self.pdf_error_result(
                    md, date=checkDate, group_len=len( result ),
                    msg='<b>Datenfehler</b>: keine Felder gefunden oder das offene Feld fehlt.'
                ) )
                return


            # base Field bereitstellen
            baseField = qa_field( self.getFullData( df_sym.loc[df_sym.index[0]] ) )

            # progress
            self.fileCount += 1

            # dosis ermitteln
            baseDose = baseField.getMeanDose( md["doseArea"] )

            data = []
            def joinImages( jdf ):
                # für beide Bilder
                if len(jdf) != 2:
                    return

                # die felder bereitstellen
                field = []
                for index, row in jdf.iterrows():
                    field.append( qa_field( self.getFullData( row ) ) )

                # die image daten des ersten feldes mit der Summe beider überschreiben
                field[0].image.array = np.add( field[0].image.array, field[1].image.array )

                # das Summenfeld ausgeben
                img = field[0].image.plotImage( original=False
                        , metadata=md
                        , field = md["fieldArea"]
                        , plotTitle="G:{gantry:01.1f} K:{collimator:01.1f}"
                        , cmap='twilight'
                        #, cmap='gray_r'
                        , invert=False, plotCax=True, plotField=False )
                self.pdf.image( img, md["_imgSize"], attrs={"margin-top": "5mm"} )
                # die sumendosis ermitteln
                fieldDose = field[0].getMeanDose( md["doseArea"] )
                # Ergebnisse merken
                data.append( {
                    "gantry" : field[0].infos["gantry"],
                    "collimator" : field[0].infos["collimator"],
                    "basedose": baseDose,
                    "fielddose": fieldDose,
                    "diff": (fieldDose-baseDose) / baseDose * 100
                } )

                # progress pro file stimmt nicht immer genau (baseimage)
                # 40% für die dicom daten 40% für die Auswertung 20 % für das pdf
                # progress hier immer 2 Felder
                self.fileCount += 2
                #print( md["variante"], filesMax, self.fileCount,  50 + ( 50 / filesMax *  self.fileCount ) )
                if hasattr( logger, "progress"):
                    logger.progress( md["testId"],  40 + ( 40 / filesMax * self.fileCount ) )


            # Gruppiert nach Gantry und Kollimator auswerten
            ( df_group
                .query( "CollMode == 'AsymmetryX'" )
                .groupby( [ 'gantry', 'collimator' ] )
                .apply( joinImages )
            )


            # das Ergebnis verarbeiten
            df = pd.DataFrame( data )

            #
            # Abweichung ausrechnen und Passed setzen
            #
            check = [
                { "field": 'diff', 'tolerance':'default' }
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
            # result Tabelle erzeugen
            #
            self.pdf.pandas( df,
                attrs={"class":"layout-fill-width", "margin-top": "5mm"}
                , fields=md["table_fields"]
            )

            # toleranz anzeigen
            text_values = {
                "f_warning": md.current.tolerance.default.warning.get("f",""),
                "f_error": md.current.tolerance.default.error.get("f","")
            }
            text = """<br>
                Warnung bei: <b style="position:absolute;left:25mm;">{f_warning}</b><br>
                Fehler bei: <b style="position:absolute;left:25mm;">{f_error}</b>
            """.format( **text_values ).replace("{value}", "Diff")
            self.pdf.text( text )

            # Gesamt check - das schlechteste aus der tabelle
            self.pdf.resultIcon( acceptance )


        #
        # Gruppiert nach Tag und SeriesNumber abarbeiten
        #
        ( fileData
             .sort_values(by=[ "gantry", "collimator", "CollMode", "AcquisitionDateTime"])
             .groupby( [ 'day', 'SeriesNumber' ] )
             .apply( groupBySeries )
        )
        # abschließen pdfdaten und result zurückgeben
        return self.pdf.finish(), result




