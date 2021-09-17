# -*- coding: utf-8 -*-

"""Aria Database connetion and querys for pyGqa


"""

__author__ = "R. Bauer"
__copyright__ = "MedPhyDO - Machbarkeitsstudien des Instituts für Medizinische Strahlenphysik und Strahlenschutz am Klinikum Dortmund im Rahmen von Bachelor und Masterarbeiten an der TU-Dortmund / FH-Dortmund"
__credits__ = ["R.Bauer", "K.Loot"]
__license__ = "MIT"
__version__ = "0.1.5"
__status__ = "Prototype"

import pytds

from pathlib import Path
import re

import logging
logger = logging.getLogger( "MQTT" )

from isp.mssql import ispMssql

class ariaClass( ispMssql ):
    '''Database querys on Aria Database

    Attributes
    ----------

    name : str
        database configuration name from config

    connect : class
         An instance of :class:`Connection`

    engine : str
         Databaseengine `pytds` or `pyodbc`

    dbname : object
        Names of dbname in connection. Default is `name`

    lastExecuteSql: str
        Holds last executed sql query

    '''

    def __init__( self, name:str=None, config=None):
        '''initialise class

        Parameters
        ----------
        name : str, optional
            database configuration name from config. The default is None.
        config : Dot, optional
            An instance of ispConfig. The default is None.

        Returns
        -------
        None.

        '''

        # initialise ispMssql
        ispMssql.__init__( self, name, config )


    def getMLC( self, RadiationSer ):
        """DynMLCPlan hat mehrere ControlPoints, deshalb nur ControlPointIndex=0 verwenden
        Nur die inneren 10 leafs verwenden um die Art zu bestimmen
        """

        sql = """
SELECT TOP 1000 [ControlPointSer]
      ,[RadiationSer]
      ,[ControlPointIndex]
      ,[ControlPointType]
      ,[MetersetWeight]
      ,[NominalEnergy]
      ,[CollX1]
      ,[CollX2]
      ,[CollY1]
      ,[CollY2]
      ,[GantryRtn]
      ,[CollRtn]
      ,[OffPlaneAngle]
      ,[PlanPosLeaf25A] AS [A-25]
      ,[PlanPosLeaf26A] AS [A-26]
      ,[PlanPosLeaf27A] AS [A-27]
      ,[PlanPosLeaf28A] AS [A-29]
      ,[PlanPosLeaf29A] AS [A-29]
      ,[PlanPosLeaf30A] AS [A-30]
      ,[PlanPosLeaf31A] AS [A-31]
      ,[PlanPosLeaf32A] AS [A-32]
      ,[PlanPosLeaf33A] AS [A-33]
      ,[PlanPosLeaf34A] AS [A-34]
      ,[PlanPosLeaf25B] AS [B-25]
      ,[PlanPosLeaf26B] AS [B-26]
      ,[PlanPosLeaf27B] AS [B-27]
      ,[PlanPosLeaf28B] AS [B-28]
      ,[PlanPosLeaf29B] AS [B-29]
      ,[PlanPosLeaf30B] AS [B-30]
      ,[PlanPosLeaf31B] AS [B-31]
      ,[PlanPosLeaf32B] AS [B-32]
      ,[PlanPosLeaf33B] AS [B-33]
      ,[PlanPosLeaf34B] AS [B-34]
      ,[PatientSupportAngle]
      ,[IsoCenterPositionX]
      ,[IsoCenterPositionY]
      ,[IsoCenterPositionZ]
  FROM [variansystem].[dbo].[ControlPoint]
          WHERE [ControlPointIndex] = 0
          AND RadiationSer = {rs:d}
        """
        mlc = self.execute( sql.format( rs=RadiationSer) )
        if len(mlc) > 0:
            return mlc[0]
        else:
            return None

    def getImages( self,
                  PatientId=None, CourseId=None,
                  PlanSetupId=None, RadiationSer=None,
                  AcquisitionYear=None,
                  AcquisitionMonth=None,
                  AcquisitionDay=None,
                  testTags:list=None, addWhere:str="" ):
        """Alle felder holen die für die Auswertungen benötigt werden.

        Nicht SliceRTType: SliceDRR verwendet werden: SlicePI :

        """
        if not PatientId and addWhere == "":
            return [], ""

        # alles aufeinmal holen
        sql = """
        SELECT [Patient].[PatientId], [Course].[CourseId], [PlanSetup].[PlanSetupId], [Radiation].[RadiationId]
          , [Series].[SeriesUID], [Series].[FrameOfReferenceUID]
          , [Series].[SeriesId], [Series].[SeriesNumber], [Series].[CreationDate]
          , [Slice].[SliceUID], [Study].[StudyUID]
          , [SliceRT].[SliceRTType], [SliceRT].[AcqNote], [SliceRT].[Energy],[SliceRT].[MetersetExposure], [SliceRT].[DoseRate], [SliceRT].[SAD], [SliceRT].[GantryAngle], [SliceRT].[CollRtn]
          , [SliceRT].[CollX1], [SliceRT].[CollX2], [SliceRT].[CollY1], [SliceRT].[CollY2], [SliceRT].[RadiationMachineName]
          , [ExternalField].[GantryRtn], [ExternalField].[GantryRtnExt], [ExternalField].[GantryRtnDirection], [ExternalField].[StopAngle], [ExternalField].[CollMode]
          , [Slice].[AcquisitionDateTime], [Slice].[SliceUID], [Slice].[PatientSupportAngle], [Slice].[FileName], [Slice].[SliceModality]
          , [MLCPlan].[MLCPlanType], [MLCPlan].[IndexParameterType]
          , [Radiation].[RadiationSer], [Radiation].[TechniqueLabel], [Radiation].[Comment]
          , [Image].[ImageId]
        FROM [{dbname}].[dbo].[Patient] [Patient]
          INNER JOIN [{dbname}].[dbo].[Course] [Course] ON ([Patient].[PatientSer] = [Course].[PatientSer])
          INNER JOIN [{dbname}].[dbo].[PlanSetup] [PlanSetup] ON ([Course].[CourseSer] = [PlanSetup].[CourseSer])
          INNER JOIN [{dbname}].[dbo].[Radiation] [Radiation] ON ([PlanSetup].[PlanSetupSer] = [Radiation].[PlanSetupSer])
          INNER JOIN [{dbname}].[dbo].[ExternalField] [ExternalField] ON ([Radiation].[RadiationSer] = [ExternalField].[RadiationSer])
          INNER JOIN [{dbname}].[dbo].[SliceRT] [SliceRT] ON ([Radiation].[RadiationSer] = [SliceRT].[RadiationSer])
          INNER JOIN [{dbname}].[dbo].[Slice] [Slice] ON ([SliceRT].[SliceSer] = [Slice].[SliceSer])
          INNER JOIN [{dbname}].[dbo].[Series] [Series] ON ([Slice].[SeriesSer] = [Series].[SeriesSer])
          LEFT JOIN [{dbname}].[dbo].[MLCPlan] [MLCPlan] ON ([Radiation].[RadiationSer] = [MLCPlan].[RadiationSer])
          INNER JOIN [{dbname}].[dbo].[Study] [Study] ON ([Series].[StudySer] = [Study].[StudySer])
          INNER JOIN [{dbname}].[dbo].[ImageSlice] [ImageSlice] ON ([Slice].[SliceSer] = [ImageSlice].[SliceSer])
          INNER JOIN [{dbname}].[dbo].[Image] [Image] ON ([ImageSlice].[ImageSer] = [Image].[ImageSer])
        WHERE NOT [SliceRT].[SliceRTType] = 'SliceDRR'
        """

        if PatientId:
            sql = sql + " AND [Patient].[PatientId] = '{}' ".format( PatientId )
        if CourseId:
            sql = sql + " AND [Course].[CourseId] = '{}' ".format( CourseId)
        if PlanSetupId:
            sql = sql + " AND [PlanSetup].[PlanSetupId] = '{}' ".format( PlanSetupId)
        if RadiationSer:
            sql = sql + " AND [Radiation].[RadiationSer] = {} ".format( RadiationSer)
        if AcquisitionYear:
            sql = sql + " AND YEAR([Slice].[AcquisitionDateTime]) = {} ".format( AcquisitionYear)
        if AcquisitionMonth:
            sql = sql + " AND MONTH([Slice].[AcquisitionDateTime]) = {} ".format( AcquisitionMonth )
        if AcquisitionDay:
            sql = sql + " AND DAY([Slice].[AcquisitionDateTime]) = {} ".format( AcquisitionDay )

        if testTags:
            subSql = []
            for tag in testTags:
                subSql.append("CHARINDEX('{}', [Radiation].[Comment] ) > 0".format( tag ) )
            if len( subSql ) > 0:
                sql += " AND (" + " OR ".join( subSql ) + ")"

        if addWhere != "":
            sql += " AND " + addWhere

        return self.execute( sql ), sql

    def getTestData( self,
                  PatientId=None,
                  AcquisitionYear=None,
                  AcquisitionMonth=None,
                  AcquisitionDay=None,
                  testTags:list=None, addWhere:str="" ):
        """ Alle Felder für ein Gerät, einen testTag und das angegebene Jahr holen

        und data aufbereiten
        """

        imagedatas, sql = self.getImages(
            PatientId = PatientId,
            AcquisitionYear=AcquisitionYear,
            AcquisitionMonth=AcquisitionMonth,
            AcquisitionDay=AcquisitionDay,
            testTags=testTags
        )

        data = {}

        for imagedata in imagedatas:
            # bereitetet die Datenbank Informationen auf
            info = self.getImageInfos( imagedata )
            # test auf testTag um ungültige auszuschließen z.B.suche nach 10.3 findet auch 10.3.1
            # da in der SQL mit CHARINDEX gesucht wird werden auch Teile gefunden
            ok = False
            for tt in testTags:
                if tt in info["testTags"]:
                    ok = True

            if not ok:
                continue

            if not info["energy"] in data:
                data[ info["energy"] ] = {}

            data[ info["energy"] ][ info["SliceUID"] ] = info

        return data

    def getTags(self, PatientId=None, split=True ):
        """Holt alle in Comment verwendeten Tags

        Parameters
        ----------
        PatientId : str|list

        split: bool
            True - content bei mehreren zeilen aufteilen (default)
            False - content komplett zurückgeben
        """
        if not PatientId:
            return []

        sql = """
        SELECT
        [Patient].[PatientId], [Course].[CourseId], [PlanSetup].[PlanSetupId]
        , [Radiation].[RadiationId]
        , [SliceRT].[AcqNote]
        , CAST([SliceRT].[Energy] / 1000 AS INT) as Energy
        , [Radiation].[Comment]
        , 1 as nummer
        FROM [{dbname}].[dbo].[Patient] [Patient]
          INNER JOIN [{dbname}].[dbo].[Course] [Course] ON ([Patient].[PatientSer] = [Course].[PatientSer])
          INNER JOIN [{dbname}].[dbo].[PlanSetup] [PlanSetup] ON ([Course].[CourseSer] = [PlanSetup].[CourseSer])
          INNER JOIN [{dbname}].[dbo].[Radiation] [Radiation] ON ([PlanSetup].[PlanSetupSer] = [Radiation].[PlanSetupSer])
          INNER JOIN [{dbname}].[dbo].[SliceRT] [SliceRT] ON ([Radiation].[RadiationSer] = [SliceRT].[RadiationSer])
        WHERE
          NOT ([Radiation].[Comment] is null or [Radiation].[Comment] = '')
          AND SUBSTRING( [Radiation].[Comment], 2, 2 ) = 'T_'
        """

        if isinstance( PatientId, list):
            sql = sql + " AND (1=2 "
            for _id in PatientId:
                sql = sql + " OR [Patient].[PatientId] = '{}'".format(_id)
                #print(_id)
            sql = sql + ")"
        else:
            sql = sql + " AND [Patient].[PatientId] = '{}'".format(PatientId)

        result = self.execute( sql )

        # alle durchgehen und Comment aufteilem
        if len( result ) == 0:
            return []

        data = []
        for row in result:
            d = row.copy()
            # energie und doserate ais AcqNote bestimmen
            desc = re.split("[\r\n|,]", d["AcqNote"])
            energy = d["Energy"]
            doserate = 0
            # ohne energie Angabe sind es Setupfelder
            if len(desc) <= 2:
                pass
            else:
                try:
                    energy = desc[0].replace( " [MV]", "" ).strip()
                    doserate = int( desc[1].replace( " [MU/min]", "" ).strip() )
                except:
                    pass

            if split:
                # Comment nach neuer zeile oder leerzeichen Splitten
                comment = (lambda v: v.split() if v else [] )( d["Comment"] )
                for t in comment:
                    # comment ersetzen
                    data.append( {
                        'PatientId': d['PatientId'],
                        'CourseId': d['CourseId'],
                        'PlanSetupId': d['PlanSetupId'],
                        'RadiationId': d['RadiationId'],
                        'Energy': energy,
                        'DoseRate': doserate,
                        'nummer': d['nummer'],
                        'Comment':  t,
                    } )
            else:
                data.append( {
                    'PatientId': d['PatientId'],
                    'CourseId': d['CourseId'],
                    'PlanSetupId': d['PlanSetupId'],
                    'RadiationId': d['RadiationId'],
                    'Energy': energy,
                    'DoseRate': doserate,
                    'nummer': d['nummer'],
                    'Comment':  d["Comment"],
                 } )

        return data


    def getImageInfos(self, imageRow:dict=None ):
        """ Bestimmt die Infos der Aufnahme.

        Parameters
        ----------
        imageRow : dict


        {
          gerät - <string>
          studyID - <string>
          filename - <string>
          filepath - <string>
          id - <string>
          energy - <string>
          gantry - <float %1.1f>
          collimator - <float %1.1f>
          type - <string> - (offen, kamm, x1zu, x2zu, tips)
        }

        dateinamen z.B.


        {
        'PatientId': '_xxxQA VB',
        'CourseId': 'Jahrestest',
        'PlanSetupId': '4Quadrant',
        'RadiationId': 'X6 Q1',
        'Energy': 6000,
        'GantryAngle': 0.01990341513203,
        'CollRtn': 359.999840036008,
        'AcquisitionDateTime': datetime.datetime(2019, 3, 20, 19, 7, 9, 510000),
        'SliceUID': '1.2.246.352.62.1.5343640968774208147.13210826594556886954',
        'ResourceSer': 1301,
        'PatientSupportAngle': 0.03125,
        'FileName': '%%imagedir1\\Patients\\_716\\SliceRT\\1820744_id1432516'
        }

        Energy aus SliceRT.Energy, Doserate -> SliceRT.MetersetExposure

        """

        # in der DICOM datei steht 'RT Image Storage' und nicht RTIMAGE
        if imageRow["SliceModality"] == 'RTIMAGE':
            imageRow["SliceModality"] = 'RT Image Storage'

        f =  Path( imageRow["FileName"].replace("\\", "/" ) )

        # kolli  360° ist 0°
        colli = float("{:1.1f}".format(imageRow["CollRtn"]) ) # BeamLimitingAngle
        if colli == 360:
            colli = 0.0
        # gantry  360° ist 0°
        gantry = float("{:1.1f}".format(imageRow["GantryRtn"]) ) # GantryAngle, GantryRtn
        if gantry == 360:
            gantry = 0.0

        # TischRotation 360° ist 0°
        table = float("{:1.1f}".format(imageRow["PatientSupportAngle"]) ) #
        if table == 360:
            table = 0.0

        # Energie und Doserate aus AcqNote bestimmen
        desc = re.split("[\r\n|,]", imageRow["AcqNote"])
        energy = ""
        doserate = 0
        if len(desc) <= 2:
            logger.warning( "aria.getImageInfos:AcqNote: {}".format( imageRow["FileName"] ) )
        else:
            try:
                energy = desc[0].replace( " [MV]", "" ).strip()
                doserate = int( desc[1].replace( " [MU/min]", "" ).strip() )
            except:
                pass

        # type zuerst nach neuer zeile oder leerzeichen Splitten
        comment = (lambda v: v.split() if v else [] )( imageRow["Comment"] )

        testTags = []
        subTags = []
        varianten = {}
        for t in comment:
            tags = t.split(":")
            _tag = tags[0]
            _sub = None
            if len( tags ) > 1:
                # mit subtag verwenden
                _sub = tags[1]
            '''
            else:
                # ohne subtag versuchen ihn für MLC plan zu bestimmen
                logger.warning( "ariaClass.get_SubTag_from_MLCPlanType: {} ".format(comment ) )
                _sub = self.get_SubTag_from_MLCPlanType( imageRow )
                logger.warning( "ariaClass.get_SubTag_from_MLCPlanType: {} ".format(_sub ) )
            '''

            # testTag und subTag merken
            testTags.append( _tag )
            subTags.append( _sub )
            # Varianten merken
            varianten[ _tag ] =  _sub

        gating = ""
        if "gating" in subTags:
            gating = "gating"

        infos = self.infoFields.copy()
        infos.update( {
             'id': imageRow["SliceUID"],
             'PatientId': imageRow["PatientId"],
             'RadiationId': imageRow["RadiationId"],
             'RadiationSer': imageRow["RadiationSer"],
             'CourseId': imageRow["CourseId"], # gibt es in der imageClass nicht
             'PlanSetupId': imageRow["PlanSetupId"], # gibt es in der imageClass nicht
             'SliceRTType': imageRow["SliceRTType"],
             'ImageId': imageRow["ImageId"],

             'SeriesId': imageRow["SeriesId"],
             'SeriesNumber' : imageRow["SeriesNumber"],
             'CreationDate' : imageRow["CreationDate"],

             'studyID': '', # FIXME: studyID
             'filepath': str( f ) ,
             'filename': f.name,
             'Kennung' : imageRow["PlanSetupId"] + ":" + imageRow["RadiationId"] + ":" + imageRow["ImageId"],
             'SOPClassUID': imageRow["SliceModality"],
             'AcquisitionDateTime': imageRow["AcquisitionDateTime"],
             'acquisition': imageRow["AcquisitionDateTime"].strftime("%Y-%m-%d %H:%M:%S"),
             'AcquisitionYear': int(imageRow["AcquisitionDateTime"].strftime("%Y")),
             'AcquisitionMonth': int(imageRow["AcquisitionDateTime"].strftime("%m")),
             'day' : imageRow["AcquisitionDateTime"].strftime("%Y-%m-%d"),
             'Tag' : imageRow["AcquisitionDateTime"].strftime("%d.%m.%Y"),
             'unit':  imageRow["RadiationMachineName"],
             'energy': energy,
             'doserate': doserate,
             'MetersetExposure' : imageRow["MetersetExposure"],
             'ME': int( round( imageRow["MetersetExposure"] ) ),
             'Technique': imageRow["TechniqueLabel"],
             'gantry' : gantry,    # GantryRtn
             'GantryRtnDirection' : imageRow["GantryRtnDirection"], # NONE, CW, CC
             'GantryRtnExt' : imageRow["GantryRtnExt"], # EN, NN
             'StopAngle' : imageRow["StopAngle"],
             'collimator': colli, # BeamLimitingAngle
             'CollMode' : imageRow["CollMode"], # Symmetry, AsymmetryX&Y, AsymmetryX (bei MLC)
             'table' : table, # PatientSupportAngle
             'SID': imageRow["SAD"],
             'MLCPlanType': imageRow["MLCPlanType"],
             'IndexParameterType': imageRow["IndexParameterType"],
             'X1': float("{:1.1f}".format( imageRow["CollX1"] ) ) * 10, # in mm
             'X2': float("{:1.1f}".format( imageRow["CollX2"] ) ) * 10, # in mm
             'Y1': float("{:1.1f}".format( imageRow["CollY1"] ) ) * 10, # in mm
             'Y2': float("{:1.1f}".format( imageRow["CollY2"] ) ) * 10, # in mm
             'SliceUID' : imageRow["SliceUID"],  # SOP Instance UID
             'SeriesUID' : imageRow["SeriesUID"], # Series Instance UID
             'StudyUID': imageRow["StudyUID"], #StudyInstanceUID
             'FrameOfReferenceUID': imageRow["FrameOfReferenceUID"],
             'gating': gating,
             'testTags':  testTags,
             'subTags': subTags,
             'varianten': varianten

        })

        return infos
    '''
    def get_SubTag_from_MLCPlanType(self, imageRow):
        """ Versucht bei MLCPlanType den subTag über die geplanten MLC Position zu bestimmen

        Parameters
        ----------
        imageRow : dict

        """
        subTag = ""
        if imageRow["MLCPlanType"] != None:
            mlc = self.getMLC( imageRow["RadiationSer"] )
            if mlc:
            #    print( mlc )
                if mlc["A-30"]==4000 and mlc["B-30"]==4000 and mlc["B-31"]==-4000 and mlc["B-31"]==-4000:
                    subTag = 'int.dig.'
                elif mlc["A-30"]==-9000 and mlc["B-30"]==-9000 and mlc["B-31"]==-9000 and mlc["B-31"]==-9000:
                    subTag = 'X2'
                elif mlc["A-30"]==9000 and mlc["B-30"]==9000 and mlc["B-31"]==9000 and mlc["B-31"]==9000:
                    subTag = 'X1'
                elif mlc["A-30"]==0 and mlc["B-30"]==0 and mlc["B-31"]==0 and mlc["B-31"]==0:
                    subTag = 'tips'
                elif mlc["A-30"]==4000 and mlc["B-30"]==4000 and mlc["B-31"]==4000 and mlc["B-31"]==4000:
                    subTag = 'tipsX1'
                elif mlc["A-30"]==-4000 and mlc["B-30"]==-4000 and mlc["B-31"]==-4000 and mlc["B-31"]==-4000:
                    subTag = 'tipsX2'
                elif mlc["A-30"]==-6000 and mlc["B-30"]==-7500 and mlc["B-31"]==-7500 and mlc["B-31"]==-7500:
                    subTag = 'MLC'
                else:
                    #st.append('tipsX2')
                    #print("aria.getImageInfos:MLCPlan", infos["PlanSetupId"], mlc["A-30"], mlc["B-30"] , mlc["B-31"], mlc["B-31"] )
                    pass
            return subTag
        '''