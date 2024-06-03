# -*- coding: utf-8 -*-

__author__ = "R. Bauer"
__copyright__ = "MedPhyDO - Machbarkeitsstudien des Instituts für Medizinische Strahlenphysik und Strahlenschutz am Klinikum Dortmund im Rahmen von Bachelor und Masterarbeiten an der TU-Dortmund / FH-Dortmund"
__credits__ = ["R.Bauer", "K.Loot", "J.Wüller"]
__license__ = "MIT"
__version__ = "0.2.1"
__status__ = "Prototype"

from pylinac.field_analysis import FieldAnalysis, Protocol
from pylinac.core.profile import Interpolation, FWXMProfilePhysical, SingleProfile

from app.base import ispBase
from app.image import DicomImage
from app.check import ispCheckClass

from isp.config import dict_merge
from isp.plot import plotClass

import numpy as np
import pandas as pd
from dotmap import DotMap

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

# logging
import logging
logger = logging.getLogger( "ISP" )

class qa_field( ispCheckClass, FieldAnalysis ):
    """Erweitert die Klasse FieldAnalysis mit ispCheckClass

    """
    def __init__( self, checkField, baseField=None, normalize: str="none" ):
        """ checkField und ggf baseField laden und ispCheckClass initialisieren

        """
        self._is_FFF = False
        self.checkField = checkField
        self.baseField = baseField

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
            if "info" in checkField:
                self._is_FFF = checkField["info"]["is_FFF"]

        self._is_analyzed = False
        self._from_device = False
        self._path = ""    
     
    def _plot_field_edges(self, profile: SingleProfile, axis: plt.Axes) -> None:
        """Overrides pylinac _plot_field_edges function
        
        - Add center line 
        - Add field_ratio=0.8 Area and Lines

        """
        data80 = profile.field_data(
            in_field_ratio=0.8, slope_exclusion_ratio=self._slope_exclusion_ratio
        )
        axis.axvline( 
            data80["beam center index (rounded)"], 
            color="r", 
            linewidth=2,
            linestyle="-."
        )
        w = data80["right index (rounded)"] - data80["left index (rounded)"]
        axis.add_patch(
            Rectangle(
                (data80["left index (rounded)"], 0), w, 1.1,
                fill=True,
                alpha=0.2,
                in_layout=False,
                clip_on=False
            )
        )        
        axis.axvline( 
            data80["left index (rounded)"], 
            color="r", 
            linewidth=2,
            linestyle="-."
        )
        axis.axvline( 
            data80["right index (rounded)"], 
            color="r", 
            linewidth=2,
            linestyle="-."
        )
       
        # pylinac original 
        data = profile.field_data(
            in_field_ratio=1.0, slope_exclusion_ratio=self._slope_exclusion_ratio
        )
        axis.plot(
            data["left index (rounded)"],
            data["left value (@rounded)"],
            "x",
            color="red",
            label="Field edge",
        )
        axis.plot(
            data["right index (rounded)"],
            data["right value (@rounded)"],
            "x",
            color="red",
        )
    
    def _plot_profile(self, axis: plt.Axes = None, profile:SingleProfile=None, grid: bool = True, metadata={} ) -> None:
        """Inspired by pylinac _plot_horiz and _plot_vert

        Args:
            axis (plt.Axes, optional): Axis to plot. Defaults to None.
            profile (SingleProfile, optional): profile to plot. Defaults to None.
            grid (bool, optional): plot grid. Defaults to True.
            metadata (dict, optional): _description_. Defaults to {}.
        """
        if axis is None:
            fig, axis = plt.subplots()

        axis.grid(grid)
        
        if self._from_device:
            axis.set_xlabel("detector")
            if self._interpolation_method == Interpolation.NONE:
                markers = "b+"
            else:
                markers = "b"
        else:
            axis.set_xlabel("mm")
            markers = "b"

        axis.plot(
            profile.x_indices,
            profile.values,
            markers,
            label="Profile",
        )

        # plot basic parameters on profile
        self._plot_penumbra(profile, axis)
        self._plot_field_edges(profile, axis)
        if self._is_FFF:
            self._plot_top(profile, axis)
            self._plot_infield_slope(profile, axis)
            axis.set_ylabel("Inflection")
        else:
            axis.set_ylabel("Flatness")

        for name, item in self._protocol.value.items():
            if item.get("plot"):
                item["plot"](self, profile, axis)

        self.image.axTicks(axis, metadata.fieldTicks)

    def plotProfile(self, metadata={} ):
        """Ein horizontale und vertikale Profilachse plotten

        Parameters
        ----------
        metadata : dict
            - profileSize
            - profileTitle - format Ersetzungen aus self.infos sind möglich
            - fieldTicks
        """

        # plotbereiche festlegen und profileSize als imgSize übergeben
        plot = plotClass( )
        fig, ax = plot.initPlot( imgSize=metadata["profileSize"], ncols=2 )
    
        # Kurven Informationen
        if not "profileTitle" in metadata:
            metadata["profileTitle"] = "{Kennung} - Energie:{energy} Gantry:{gantry:.0f} Kolli:{collimator:.0f}"

        # x-Achse (crossline)           
        self._plot_profile( ax[0], profile=self.horiz_profile, grid=True, metadata=metadata)
        ax[0].set_title( metadata["profileTitle"].format( **self.infos ) + " - crossline" )
        
        # y-Achse (inline)
        self._plot_profile( ax[1], profile=self.vert_profile, grid=True, metadata=metadata)
        ax[1].set_title( metadata["profileTitle"].format( **self.infos ) + " - inline" )
      
        # Layout optimieren
        plt.tight_layout(pad=0.4, w_pad=2.0, h_pad=1.0)
        # data der Grafik zurückgeben
        return plot.getPlot()

    def find4Qdata( self, field=None ):
        """ Die transmissions eines 4 Quadranten Feldes im angegebenem Bereich ermitteln

        Reihenfolge in result 'Q2Q1','Q2Q3','Q3Q4','Q1Q4'

        """
        if not field:
            field = { "X1":-50, "X2": 50, "Y1": -50, "Y2": 50 }

        roi = self.image.getRoi( field ).copy()

        result = {}

        result['Q2Q1'] = {
            'name' : 'Q2 - Q1',
            'profile' : FWXMProfilePhysical( 
                roi[ : , 0 ],
                dpmm=self.image.dpmm 
            ),
            'field' : field

        }
        result['Q2Q3'] = {
            'name' : 'Q2 - Q3',
            'profile' : FWXMProfilePhysical( 
                roi[ 0 ],
                dpmm=self.image.dpmm 
            ),
            'field' : field
        }
        result['Q3Q4'] = {
            'name' : 'Q3 - Q4',
            'profile' : FWXMProfilePhysical( 
                roi[ : , -1 ],
                dpmm=self.image.dpmm 
            ),
            'field' : field
        }
        result['Q1Q4'] = {
            'name' : 'Q1 - Q4',
            'profile' : FWXMProfilePhysical( 
                roi[ -1 ],
                dpmm=self.image.dpmm 
            ),
            'field' : field
        }

        for k in result:
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

        ax.set_title(data["name"])

        # kurve plotten
        ax.plot(data["profile"].values, color='b')

        # y Achsenlimit
        ax.set_ylim(0.5, 1.5)
        
        # x-Achse
        ax.get_xaxis().set_ticks( [0, len(data["profile"].values) ] )
        ax.get_xaxis().set_ticklabels([ data["name"][0:2], data["name"][-2:] ])
        
        # y-achse anzeigen
        ax.get_yaxis().set_ticks( [0.75, 1.0, 1.25] )
        ax.get_yaxis().set_ticklabels( [0.75, 1.0, 1.25] )
        
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
        fileData : pandas.DataFrame

        md : dict, optional
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

        # prepare metadata
        md = dict_merge( DotMap( md ), self.metadata )

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

        def groupBySeries( df_group ):
            """Datumsweise Auswertung und PDF Ausgabe
            Die Daten kommen nach doserate und ME sortiert
            """
           
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
                    'fieldMeanDose': baseMeanDose,
                    'diff': np.nan # (baseMeanDose - 1.0) * 100
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

        # place for testing parameters
        md = dict_merge( DotMap( {
            
        } ), self.metadata )

        return self._doField_one2n(fileData, md=md )


    def doJT_7_3(self, fileData):
        """Jahrestest: 7.3.  ()
        Abhängigkeit der Kalibrierfaktoren vom Dosismonitorwert

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
                "attrs": {"class":"layout-fill-width"},
            },
            "tolerance_pdf" : {
                "attrs": {"margin-top":"-2mm"},
                "mode": "text"
            },

            "doseArea" : { "X1":-5, "X2": 5, "Y1": -5, "Y2": 5 },
            "plotImage_pdf": {
                "area" : { "width" : 80, "height" : 80 },
                "attrs": {"margin-left":"5mm"} ,
            },
            "plotImage_field" : 10,
            "evaluation_table_pdf" : {
                "attrs": { "class":"layout-fill-width", "margin-top": "5mm" },
                "fields": [
                    {'field': 'Kennung', 'label':'Kennung', 'format':'{0}', 'style': [('text-align', 'left')] },
                    {'field': 'gantry', 'label':'Gantry', 'format':'{0:.0f}' },
                    {'field': 'collimator','label':'Kollimator', 'format':'{0:.0f}' },
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
                        , plotTitle="{Kennung} - G:{gantry:.0f} K:{collimator:.0f}"
                        , field=md["plotImage_field"]
                        , invert=False # , cmap="jet"
                        , plotCax=True, plotField=True
                    )
            self.pdf.image(img, **md.plotImage_pdf )

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
                img = checkField.image.plotImage( 
                    original=False,
                    plotTitle="{Kennung} - G:{gantry:.0f} K:{collimator:.0f}",
                    field=md["plotImage_field"],
                    invert=False, # cmap="jet",
                    plotCax=True, 
                    plotField=True
                )
                self.pdf.image(img, **md.plotImage_pdf )

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

    def doJT_7_5_pre2020(self, fileData):
        """Jahrestest: 7.5.  ()
        Der Test überprüft die Konstanz des Outputs unter Rotation in vier Winkelsegmenten.
        Überprüft wird jeweils ein 10x10 Feld.
        Die 45°-Segmente erhalten für den maximal bzw. minimal möglichen winkelbezogenen 
        Dosismonitorwert bei 6MV bspw. 900MU mit DR600 bzw. 3MU mit DR20.

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

        # prepare metadata werden von den Angaben in der config überschrieben
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
                "area" : { "width" : 75, "height" : 75 },
                "attrs": { "margin-left": "10mm" }
            },
            "evaluation_text": True,
            "tolerance_field": "diff",
            "tolerance_pdf": {
                "mode": "text"
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
                df_base = df.query( md.querys[ "sub_base"] )
                df_fields = df.query( md.querys[ "sub_fields"] )

                # base Field und dosis bereitstellen
                baseField = qa_field( self.getFullData( df_base.loc[df_base.index[0]] ) )
                baseMeanDose = baseField.getMeanDose( md["doseArea"] )

                # zusätzliche Spalte in fields anlegen
                df_fields["von_nach"] = df_group[['gantry','StopAngle']].apply(lambda x : '{:.1f} -> {:.1f}'.format(x[0],x[1]), axis=1)

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
                    data.append({
                            'Kennung': checkField.infos["Kennung"],
                            'von_nach': checkField.infos["von_nach"],
                            'ME': checkField.infos["ME"],
                            'baseMeanDose': np.nan,
                            'fieldMeanDose': fieldDose,
                            'diff': (fieldDose-baseMeanDose) / baseMeanDose * 100,
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
            acceptance = self.evaluationResult( evaluation_df, md, result, md["tolerance_field"] )

        # call evaluate with sorted and grouped fields
        fileData.sort_values(md["series_sort_values"]).groupby( md["series_groupby"] ).apply( evaluate )

        # abschließen pdfdaten und result zurückgeben
        return self.pdf.finish(), result

    def doJT_7_5(self, fileData):
        """Jahrestest: 7.5.  ()
        Der Test überprüft die Konstanz des Outputs unter Rotation in vier Winkelsegmenten.
        Überprüft wird jeweils ein 10x10 Feld.
        Die 45°-Segmente erhalten für den maximal bzw. minimal möglichen winkelbezogenen 
        Dosismonitorwert bei 6MV bspw. 900MU mit DR600 bzw. 3MU mit DR20.

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

        if self.metadata.get("AcquisitionYear", 0) < 2020:
            return self.doJT_7_5_pre2020( fileData )
        
        # used on progress
        filesMax=len( fileData )
        self.fileCount = 0
        # holds evaluation results
        result=[]

        # prepare metadata werden von den Angaben in der config überschrieben
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
                "area" : { "width" : 45, "height" : 45 },
                "attrs": { },
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
                df_base = df.query( md.querys[ "sub_base"] )
                df_fields = df.query( md.querys[ "sub_fields"] )

                # base Field und dosis bereitstellen
                baseField = qa_field( self.getFullData( df_base.loc[df_base.index[0]] ) )
                baseMeanDose = baseField.getMeanDose( md["doseArea"] )

                # zusätzliche Spalte in fields anlegen
                df_fields["von_nach"] = df_group[['gantry','StopAngle']].apply(lambda x : '{:.1f} -> {:.1f}'.format(x[0],x[1]), axis=1)

                # alle Felder durchgehen
                for info in df_fields.itertuples():
                    # prüf Field und dosis bereitstellen
                    checkField = qa_field( self.getFullData(info), normalize="none" )
                    fieldDose = checkField.getMeanDose( md["doseArea"] )
                    #
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
            acceptance = self.evaluationResult( evaluation_df, md, result, md["tolerance_field"] )

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
                "attrs": { "class":"layout-fill-width" },
            },
            "fieldTicks" : { "X1":-200, "X2": 200, "xStep":50, "Y": "auto" },
            "analyze" :{
                "edge_detection_method": "FWHM", # Edge.FWHM
                "in_field_ratio": 0.8,
            },
            "analyze_FFF" :{
                "edge_detection_method": "Inflection Hill", # Edge.INFLECTION_HILL
                "in_field_ratio": 0.8,
            },
            "_clip" : { "width":"35mm", "height":"50mm" },
            "mathtext_flatness": { 
                "text" : "",
                "area": { 
                    "left":40, "top": 210, 
                    "width":21, "height": 20
                }            
            },
            "mathtext_inflection": { 
                "text" : "",
                "area": { 
                    "left":40, "top": 210, 
                    "width":21, "height": 20
                }            
            },
            "mathtext_symmetry": { 
                "text" : "",
                "area": { 
                    "left":40, "top": 230, 
                    "width":21, "height" : 22
                }
            },
            "_table": { "width" :105, "height": 45, "left":65, "top":210 },
            "_chart" : {"width" :180, "height" : 35 },
            "_info" : { "left":65, "top":240 },
            "profileSize" : { "width" : 180, "height" : 35 },
            "profileTitle" : "Gantry: {gantry:.0f}°",
            "table_fields" : [
                {'field': 'gantry', 'label':'Gantry', 'format':'{0:.0f}' },
                {'field': 'c_flat', 'label':'c-flat [%]', 'format':'{0:.1f}' },
                {'field': 'c_flat_passed', 'label':'c-flat'},
                {'field': 'i_flat', 'label':'i-flat [%]', 'format':'{0:.1f}' },
                {'field': 'i_flat_passed', 'label':'i-flat'},
                {'field': 'c_sym', 'label':'c-sym [%]', 'format':'{0:.1f}' },
                {'field': 'c_sym_passed', 'label':'c-sym'},
                {'field': 'i_sym', 'label':'i-sym [%]', 'format':'{0:.1f}' },
                {'field': 'i_sym_passed', 'label':'i-sym'},

            ],
            "table_fields_FFF" : [
                {'field': 'gantry', 'label':'Gantry', 'format':'{0:.0f}' },
                {'field': 'c_flat', 'label':'Inf [%]', 'format':'{0:.1f}' },
                {'field': 'c_flat_passed', 'label':'c-Inf'},
                {'field': 'i_flat', 'label':'i-Inf [%]', 'format':'{0:.1f}' },
                {'field': 'i_flat_passed', 'label':'i-Inf'},
                {'field': 'c_sym', 'label':'c-sym [%]', 'format':'{0:.1f}' },
                {'field': 'c_sym_passed', 'label':'c-sym'},
                {'field': 'i_sym', 'label':'i-sym [%]', 'format':'{0:.1f}' },
                {'field': 'i_sym_passed', 'label':'i-sym'},

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
            isFFF = False
            # alle Felder durchgehen
            for info in df_group.itertuples():
                checkField = qa_field( self.getFullData( info ), normalize="none" )         

                # Protocol.VARIAN
                #
                # flatness = 100*|Dmax - Dmin|/(Dmax + Dmin)
                # symetrie = 100*max(|Lpt - Rpt|/Dcax
                if checkField._is_FFF:
                    isFFF = True
                    checkField.analyze( 
                        protocol=Protocol.VARIAN, 
                        edge_detection_method=md["analyze_FFF"]["edge_detection_method"], # Edge.INFLECTION_HILL,
                        in_field_ratio=md["analyze_FFF"]["in_field_ratio"],
                        is_FFF = checkField._is_FFF,
                        # penumbra = (20, 80),
                    )
                else: 
                    checkField.analyze( 
                        protocol=Protocol.VARIAN, 
                        edge_detection_method=md["analyze"]["edge_detection_method"], # Edge.FWHM,
                        in_field_ratio=md["analyze"]["in_field_ratio"],
                        is_FFF = checkField._is_FFF,
                        # penumbra = (20, 80),
                    )
                results = checkField.results_data()
                
                # Bild anzeigen
                img =  checkField.plotProfile( metadata=md )
                self.pdf.image(img, md["_chart"], {"padding":"2mm 0 2mm 0"} )

                data.append( {
                    'gantry' : checkField.infos["gantry"],
                    'c_flat': results.protocol_results["flatness_horizontal"],
                    'c_sym': results.protocol_results["symmetry_horizontal"],
                    'i_flat': results.protocol_results["flatness_vertical"],
                    'i_sym': results.protocol_results["symmetry_vertical"],
                } )

                # progress pro file stimmt nicht immer genau (baseimage)
                # 40% für die dicom daten 40% für die Auswertung 20 % für das pdf
                self.fileCount += 1
                if hasattr( logger, "progress"):
                    logger.progress( md["testId"],  40 + ( 40 / filesMax * self.fileCount ) )

            # Grafik und Formel anzeigen
            self.pdf.image( "qa/Profile.svg", attrs=md["_clip"])
            if isFFF == True:
                label = md.current.tolerance.flatness.get("label", "")
                self.pdf.mathtext( label + " =\n" + r"$A+\frac{B-A} {1+\frac{C^D}{x}}$", area=md["mathtext_flatness"]["area"]  )
            else:
                label = md.current.tolerance.flatness.get("label", "")
                #self.pdf.mathtext( label + " =\n" + r"$\frac{\vert D_{max} - D_{min}\vert} {D_{CAX}}$", area=md["mathtext_flatness"]["area"]  )
                self.pdf.mathtext( label + " =\n" + r"100 * $\frac{\vert D_{max} - D_{min}\vert} {(D_{max} + D_{min})}$", area=md["mathtext_flatness"]["area"]  )
                
            label = md.current.tolerance.symmetry.get("label", "")
            self.pdf.mathtext( label + " =\n" + r"$100 * \frac{\vert L_{pt} - R_{pt}\vert} {D_{CAX}}$", area=md["mathtext_symmetry"]["area"]  )
            
            # dataframe erstellen
            df = pd.DataFrame( data )

            #
            # Abweichung ausrechnen und Passed setzen
            #
            # 
            check = [
                { "field": 'c_flat', 'tolerance': 'flatness' },
                { "field": 'i_flat', 'tolerance': 'flatness' },
                { "field": 'c_sym', 'tolerance': 'symmetry' },
                { "field": 'i_sym', 'tolerance': 'symmetry' }
            ]
            acceptance = self.check_acceptance( df, md, check, withSoll=True )

            tolerance_format = '<b>{}</b> <span style="position:absolute;left:75mm;">{}</span> <span style="position:absolute;left:125mm;">{}</span> <br>'
            infoText = tolerance_format.format("<br>", "<b>Warnung [%]</b>", "<b>Fehler [%]</b>")
            infos = []
            for tolerance_name, tolerance in md.current.tolerance.items():
                tolerance_check = tolerance.check
                infos.append({
                    "Prüfung" : tolerance.get("label", ""),
                    "Warnung" : tolerance.warning.f,
                    "Fehler" :  tolerance.error.f 
                })
                tolerance_check["tolerance"] = tolerance_name
                check.append( tolerance_check )
                infoText += tolerance_format.format( tolerance_name, tolerance.warning.f, tolerance.error.f )
    
            df_info = pd.DataFrame(infos)
            
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
            table_fields = md["table_fields"]
            if isFFF == True:
                table_fields = md["table_fields_FFF"]
            self.pdf.pandas( df,
                area=md["_table"],
                attrs={"class":"layout-fill-width", "margin-top": "5mm"},
                fields=table_fields
            )

            self.pdf.pandas( df_info, area=md["_info"] )

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
                "attrs": {"class":"layout-fill-width", "margin-bottom": "5mm"},
            },
            "_chart" : {"width" : 90, "height" : 50},
            "plotImage_pdf": {
                "area" : { "width" : 120, "height" : 120 },
                "attrs": { "margin-top": "5mm" },
            },
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
            self.pdf.image(img, **md.plotImage_pdf  )

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
                "attrs": {"class":"layout-fill-width", "margin-bottom": "5mm"},
            },

            "doseArea" : { "X1":-0.75, "X2": 0.75, "Y1": -4, "Y2": 4 },
            "plotImage_pdf": {
                "area" : { "width" : 36, "height" : 70 },
                "attrs": {  },
            },
            "_imgField": {"border": 10 },
            "_chart": { "width" : 180, "height" : 60},
            "table_fields" : [
                {'field': 'Kennung', 'label':'Kennung', 'format':'{0}', 'style': [('text-align', 'left')] },
                {'field': 'gantry', 'label':'Gantry', 'format':'{0:1.0f}' },
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
            self.pdf.image( img, **md.plotImage_pdf )

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
                self.pdf.image( img, **md.plotImage_pdf )

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
                "attrs": {"class":"layout-fill-width"},
            },
            "plotImage_pdf": {
                "area" : { "width" : 45, "height" : 45},
                "attrs": { "margin-top": "5mm" },
            },
            "fieldArea" : { "X1":-80, "X2":80, "Y1": -80, "Y2":80, "xStep":20, "yStep":20 },
            "doseArea" : { "X1": -60, "X2": 60, "Y1": -60, "Y2": 60 },
            "table_fields": [
                {'field': 'gantry', 'label':'Gantry', 'format':'{0:.0f}' },
                {'field': 'collimator', 'label':'Kollimator', 'format':'{0:.0f}' },
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
                        , plotTitle="G:{gantry:1.0f} K:{collimator:.0f}"
                        , cmap='twilight'
                        #, cmap='gray_r'
                        , invert=False, plotCax=True, plotField=False )
                self.pdf.image( img, **md.plotImage_pdf )
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

    def doJT_4_1_3(self, fileData):
        """Jahrestest: 4.1.3.  ()

        http://192.168.131.66:5010/api/gqa/run?year=2024&month=2&unit=TrueBeamSN2898&testid=JT-4_1_3&energy=6x
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
            "_table": { "width" :105, "height": 45, "left":65, "top":210 },
            "_chart" : {"width" :180, "height" : 35 },
            "profileSize" : { "width" : 180, "height" : 35 },
            "profileTitle" : "Gantry: {gantry:.0f}°",
            "_info" : {  },
            "analyze" :{
                "edge_detection_method": "FWHM", # Edge.FWHM
                "in_field_ratio": 0.8,
            },
            "analyze_FFF" :{
                "edge_detection_method": "Inflection Hill", # Edge.INFLECTION_HILL
                "in_field_ratio": 0.8,
            },
            "table_fields" : [
                {'field': 'Kennung', 'label':'Kennung' },
                {'field': 'doserate', 'label':'Doserate', 'format':'{0:.0f}' },
                {'field': 'ME', 'label':'ME', 'format':'{0:.0f}' },

                {'field': 'c_flat', 'label':'c-flat [%]', 'format':'{0:.2f}' },
                {'field': 'c_flat_diff', 'label':'c-flat-diff'},
                {'field': 'c_flat_diff_passed', 'label':'c-flat-diff-passed'},
                
                {'field': 'i_flat', 'label':'i-flat [%]', 'format':'{0:.2f}' },
                {'field': 'i_flat_diff', 'label':'c-flat-diff'},
                {'field': 'i_flat_diff_passed', 'label':'i-flat-diff-passed'},
                
                {'field': 'c_sym', 'label':'c-sym [%]', 'format':'{0:.2f}' },
                {'field': 'c_sym_diff', 'label':'c-sym-diff'},
                {'field': 'c_sym_diff_passed', 'label':'c-sym-diff-passed'},
                
                {'field': 'i_sym', 'label':'i-sym [%]', 'format':'{0:.2f}' },
                {'field': 'i_sym_diff', 'label':'c-sym-diff'},
                {'field': 'i_sym_diff_passed', 'label':'i-sym-diff-passed'},

            ],
            "table_fields_FFF" : [
                {'field': 'gantry', 'label':'Gantry', 'format':'{0:.0f}' },

                {'field': 'c_flat', 'label':'c-Inf [%]', 'format':'{0:.1f}' },
                {'field': 'c_flat_diff', 'label':'c-Inf-diff'},
                {'field': 'c_flat_diff_passed', 'label':'c-Inf-diff_passed'},

                {'field': 'i_flat', 'label':'i-Inf [%]', 'format':'{0:.1f}' },
                {'field': 'i_flat_passed', 'label':'i-Inf-diff'},
                {'field': 'i_flat_diff_passed', 'label':'i-Inf-diff_passed'},

                {'field': 'c_sym', 'label':'c-sym [%]', 'format':'{0:.2f}' },
                {'field': 'c_sym_diff', 'label':'c-sym-diff'},
                {'field': 'c_sym_diff_passed', 'label':'c-sym-diff-passed'},
                
                {'field': 'i_sym', 'label':'i-sym [%]', 'format':'{0:.2f}' },
                {'field': 'i_sym_diff', 'label':'c-sym-diff'},
                {'field': 'i_sym_diff_passed', 'label':'i-sym-diff-passed'},
            ]
        } ), self.metadata )
        print( "************* doJT_4_1_3" )
        #md.pprint(pformat='json')

        def groupBySeries( df_group ):
            """Datumsweise Auswertung und PDF Ausgabe
            Die Daten kommen nach doserate und ME sortiert
            """
            # print("doJT_4_1_3", df_group[ ["energy", "doserate", "ME"] ] )

            # get base and fields check number of data
            ok, df_base, df_fields = self.evaluationPrepare(df_group, md, result)
            if not ok:
                return

            result_doserate = []

            def groupByDoserate( df_doserate ):               
                #print( df_doserate )
                text = ""
                # in den Toleranzangaben der config steht die default query
                openFieldQuery = md.current.tolerance.default.get('flat_c').check.get("query", "")
                #openFieldQuery = md.current.tolerance.default.flat_c.check.query
                fieldQuery = openFieldQuery.replace("==", "!=")
                

                # das offene Feld bestimmen
                df_base = df_doserate.query( openFieldQuery )
    
                # base Field und dosis bereitstellen
                baseField = qa_field( self.getFullData( df_base.loc[df_base.index[0]] ), normalize="none" )

                # unterschiedliche Auswertung FFF oder nicht
                analyze_method = "analyze"
                table_fields = md["table_fields"]
                if baseField._is_FFF:
                    analyze_method += "_FFF"
                    table_fields = md["table_fields_FFF"]

                baseField.analyze( 
                    protocol=Protocol.VARIAN, 
                    edge_detection_method=md[analyze_method]["edge_detection_method"], # Edge.FWHM,
                    in_field_ratio=md[analyze_method]["in_field_ratio"],
                    is_FFF = baseField._is_FFF,
                        # penumbra = (20, 80),
                )

                results = baseField.results_data()
                # print( "####### results", results.protocol_results )

                # baseField Image anzeigen
                img =  baseField.plotProfile( metadata=md )
                self.pdf.image(img, md["_chart"], {"padding":"2mm 0 2mm 0"} )

                c_f_b = results.protocol_results["flatness_horizontal"]
                i_f_b = results.protocol_results["flatness_vertical"]
                c_s_b = results.protocol_results["symmetry_horizontal"]
                i_s_b = results.protocol_results["symmetry_vertical"]               

                '''
                # Analyse nach DIN (max-min)/center rückgabe in valueiec
                profile = baseField.getProfileData()
                # crossplane und inplane
                f_c_b = profile["flatness"]["horizontal"]["value"]
               
                openFieldQuery = md.current.tolerance.default.flat_i.check.query
                fieldQuery = openFieldQuery.replace("==", "!=")
                #print( openFieldQuery, fieldQuery )

                # das offene Feld bestimmen
                df_base = df_doserate.query( openFieldQuery )

                # base Field und dosis bereitstellen
                baseField = qa_field( self.getFullData( df_base.loc[df_base.index[0]] ), normalize="none" )
                
                # Analyse nach DIN (max-min)/center rückgabe in valueiec
                profile = baseField.getProfileData()
                
                f_i_b = profile["flatness"]["vertical"]["value"]
                
                s_c_b = profile["symmetry"]["horizontal"]["value"]
                
                s_i_b = profile["symmetry"]["vertical"]["value"]
                
                '''
                # 100  referenz Dose 1.0
                #data = [ {
                #    'Kennung': baseField.infos["RadiationId"],
                #    'doserate': baseField.infos["doserate"],
                #    'ME': baseField.infos["ME"],
                # #   'baseMeanDose': baseMeanDose,
                #    'fieldMeanDose': baseMeanDose,
                #    'diff': (baseMeanDose - 1.0) * 100
#
#                }]
                # print(baseField.infos)
                data = [ {
                    'Kennung': baseField.infos["RadiationId"],
                    'doserate': baseField.infos["doserate"], 
                    'ME': baseField.infos["ME"],
                   #'baseMeanDose': baseMeanDose,
                    'c_flat': c_f_b,
                    'c_flat_diff': np.nan,
                    'c_flat_diff_passed': np.nan,
                    'i_flat': i_f_b,
                    'i_flat_diff': np.nan,
                    'i_flat_diff_passed': np.nan,
                    'c_sym': c_s_b,
                    'c_sym_diff': np.nan,
                    'c_sym_diff_passed': np.nan,
                    'i_sym': i_s_b,
                    'i_sym_diff': np.nan,
                    'i_sym_diff_passed': np.nan,
                }]

                
                # alle anderen filtern
                df_fields = df_doserate.query( fieldQuery )

                # alle anderen durchgehen
                for info in df_fields.itertuples():
                    # prüft Field und dosis bereitstellen
                    checkField = qa_field( self.getFullData(info), normalize="none" )
                    checkField.analyze( 
                        protocol=Protocol.VARIAN, 
                        edge_detection_method=md[analyze_method]["edge_detection_method"], # Edge.FWHM,
                        in_field_ratio=md[analyze_method]["in_field_ratio"],
                        is_FFF = baseField._is_FFF,
                        # penumbra = (20, 80),
                    )

                    results = checkField.results_data()

                    c_f = results.protocol_results["flatness_horizontal"]
                    i_f = results.protocol_results["flatness_vertical"]
                    c_s = results.protocol_results["symmetry_horizontal"]
                    i_s = results.protocol_results["symmetry_vertical"]
   
                    data.append( {
                      'Kennung': checkField.infos["RadiationId"],
                      'doserate': checkField.infos["doserate"], 
                      'ME': checkField.infos["ME"],
                      'c_flat': c_f,
                      'c_flat_diff': c_f - c_f_b,
                      'i_flat': i_f,
                      'i_flat_diff': i_f - i_f_b,
                      'c_sym': c_s,
                      'c_sym_diff': c_s - c_s_b,
                      'i_sym': i_s,
                      'i_sym_diff': i_s - i_s_b
                    } )
                    
                    # progress
                    self.fileCount += 1
                    if hasattr( logger, "progress"):
                        logger.progress( md["testId"],  40 + ( 40 / filesMax * self.fileCount ) )

                # aus den daten ein DataFrame machen
                evaluation_df = pd.DataFrame( data )
                # check tolerance - printout tolerance, evaluation_df -  md["tolerance_field"],
                
                # print("########", evaluation_df)

                

                # flat_c  diff_flat_c    flat_i  diff_flat_i    sym_c  diff_sym_c    sym_i  diff_sym_i
                # 'diff_flat_i_passed', 'diff_sym_c_passed', 'diff_sym_i_passed'
                #acceptance = self.evaluationResult( evaluation_df, md, result_doserate, md.current.tolerance.default.flat_c.check.field, printResultIcon=False )
                #acceptance = self.evaluationResult( evaluation_df, md, result_doserate, printResultIcon=False )
                
                check = [
                    { "field": 'c_flat_diff', 'tolerance': 'flatness' },
                    { "field": 'i_flat_diff', 'tolerance': 'flatness' },
                    { "field": 'c_sym_diff', 'tolerance': 'symmetry' },
                    { "field": 'i_sym_diff', 'tolerance': 'symmetry' }
                ]
                acceptance = self.check_acceptance( evaluation_df, md, check, withSoll=True )
                '''
                # debug pandas ausgabe
                self.pdf.pandas( 
                    evaluation_df, 
                    area=md["_info"]
                )
                '''
                self.pdf.pandas( 
                    evaluation_df, 
                    area=md["_info"],
                    fields=table_fields
                )
                # print( md.current.tolerance.items() )
                '''
                tolerance_format = '<b>{}</b> <span style="position:absolute;left:75mm;">{}</span> <span style="position:absolute;left:125mm;">{}</span> <br>'
                infoText = tolerance_format.format("<br>", "<b>Warnung [%]</b>", "<b>Fehler [%]</b>")
                infos = []
                for tolerance_name, tolerance in md.current.tolerance.items():
                    tolerance_check = tolerance.check
                    infos.append({
                        "Prüfung" : tolerance.get("label", tolerance_name),
                        "Warnung" : tolerance.warning.f,
                        "Fehler" :  tolerance.error.f 
                    })
                    tolerance_check["tolerance"] = tolerance_name
                    check.append( tolerance_check )
                    infoText += tolerance_format.format( tolerance_name, tolerance.warning.f, tolerance.error.f )
        
                df_info = pd.DataFrame(infos)
                self.pdf.pandas( df_info, area=md["_info"] )
                
                            #
                # Tabelle erzeugen
                #
                table_fields = md["table_fields"]
                
                self.pdf.pandas( evaluation_df,
                    area=md["_table"],
                    attrs={"class":"layout-fill-width", "margin-top": "5mm"},
                 #   fields=table_fields
                )

                self.pdf.pandas( df_info, area=md["_info"] )
                '''
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