# -*- coding: utf-8 -*-

__author__ = "R. Bauer"
__copyright__ = "MedPhyDO - Machbarkeitsstudien des Instituts für Medizinische Strahlenphysik und Strahlenschutz am Klinikum Dortmund im Rahmen von Bachelor und Masterarbeiten an der TU-Dortmund / FH-Dortmund"
__credits__ = ["R.Bauer", "K.Loot"]
__license__ = "MIT"
__version__ = "0.1.2"
__status__ = "Prototype"

import os.path as osp
import glob
import json
import pandas as pd

infoFields = {
        'id': "",
        'PatientId': "",
        'RadiationId': "",
        'RadiationSer': "",
        'CourseId': "", # gibt es nur in der AriaClass und nicht in der imageClass
        'PlanSetupId': "", # gibt es nur in der AriaClass und nicht in der imageClass
        'SliceRTType': "",
        'ImageId': "",
        'SeriesId': "",
        'SeriesNumber' : "",
        'CreationDate' : "",
        'studyID': '', # FIXME: studyID
        'filepath': "",
        'filename': "",
        'Kennung' : ":",
        'SOPClassUID': "",
        'acquisition': "",  
        'AcquisitionYear': "",  # int "%Y" aus acquisition
        'AcquisitionMonth': "", # int "%m" aus acquisition
        'day': "", # "%Y-%m-%d" aus acquisition
        'Tag': "", # "%d.%m.%Y" aus acquisition
        'unit':  "",
        'energy': "",        
        'doserate': "",
        'MetersetExposure': "",
        'ME': 0,
        'Technique': "",
        'gantry' : 0,    # GantryRtn
        'GantryRtnExt' : "",
        'GantryRtnDirection' : "", # NONE, CW, CC
        'StopAngle' : 0,
        'collimator': 0, # BeamLimitingAngle
        'CollMode' : "", # Symmetry, AsymmetryX&Y, AsymmetryX (bei MLC)
        'table' : 0, # PatientSupportAngle
        'SID': 0,
        'MLCPlanType': "", # None, DynMLCPlan
        'IndexParameterType': "",
        'X1': 0, # in mm
        'X2': 0, # in mm
        'Y1': 0, # in mm
        'Y2': 0, # in mm
        'SliceUID' : "",  # SOP Instance UID  
        'SeriesUID' : "", # Series Instance UID
        'StudyUID': "", #StudyInstanceUID
        'FrameOfReferenceUID': "",
        'gating': "",
        'testTags': [],  
        'subTags': [],
        'varianten': {} # {testTag:subTag} 
}


class gqa_config():
    
    
    def __init__( self ):
        
        # BASE_DIR festlegen
        self._basedir = osp.abspath( osp.join( osp.dirname( osp.abspath( __file__ ) ) , "../" ) )
        
        
    def read(self):
        """
        

        Returns
        -------
        TYPE
            DESCRIPTION.

        """
        self.configs = {}
        
        configPath = osp.join(  self._basedir, "config")
            
        # alle configs einlesen und gqa bestimmen
        config_files = sorted(glob.glob(osp.join( configPath, 'config-*.json') ))
        
        config_files.insert( 0, osp.join( configPath, 'config.json') ) 
        # sort 
        
        for name in config_files:
            config_name = osp.basename( name ).replace("config-", "").replace(".json", "")
    
            with open(name, 'r') as f:
                try:
                    config = json.load(f)
        
                    self.configs[ config_name ] = config
                except:  # pragma: no cover
                    # Fehler hier anzeigen, da noch kein mqtt logger bereitsteht
                    #self.configs[ config_name ] = "error"
                    print( "CONFIG: Fehler bei json.load", name )
                    # fehler hier anzeigen, da noch kein mqtt logger bereitsteht
                    
                    pass

        return self
         
    def matrix(self):
        """
        
        Returns
        -------
        TYPE
            DESCRIPTION.

        """
        tags = {}
        cross = {}
        for config_name, config in self.configs.items():
            
            if not config_name in cross:
                cross[config_name] = { 
                    " Version" : config.get("version", "")
                }
                                
            gqa = {}
            if "GQA" in config:
                gqa = config["GQA"]
                
            for tag, settings in gqa.items():
                if not tag in cross[config_name]:
                    cross[config_name][ tag ]= json.dumps( settings, indent=2, sort_keys=True ) 
                     
        # tabelle erzeugen 

        df = pd.DataFrame.from_dict(cross)
        
        return df.sort_index()
        