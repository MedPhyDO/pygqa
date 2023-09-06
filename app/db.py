# -*- coding: utf-8 -*-

__author__ = "R. Bauer"
__copyright__ = "MedPhyDO - Machbarkeitsstudien des Instituts für Medizinische Strahlenphysik und Strahlenschutz am Klinikum Dortmund im Rahmen von Bachelor und Masterarbeiten an der TU-Dortmund / FH-Dortmund"
__credits__ = ["R.Bauer", "K.Loot"]
__license__ = "MIT"
__version__ = "0.2.0"
__status__ = "Prototype"

from safrs import jsonapi_rpc # rpc decorator
from sqlalchemy import func, case, or_ #, inspect

from isp.safrs import ispSAFRSModel, db

import json

class gqadb( ispSAFRSModel ):
    """
        description: Geräte QA - Datenbank mit Auswertungen

    ----

        __bind_key__ same as config database main 

    """
    __tablename__ = "gqadb"      
    __bind_key__ = 'gqa'      
    __table_args__ = {'extend_existing': True}
    
    id = db.Column('id', db.Integer, primary_key=True, unique=True, autoincrement=True)
    unit = db.Column('unit', db.String, nullable=False)
    energy = db.Column('energy', db.String, nullable=False)
    testid = db.Column('testid', db.String, nullable=False)
    date = db.Column('date', db.Date, nullable=False) # YYYYMMDD
    group = db.Column('group', db.Integer, nullable=False)
    acceptance = db.Column('acceptance', db.Integer, nullable=False)
    year = db.Column('year', db.Integer, nullable=False)
    month = db.Column('month', db.Integer, nullable=False)
    data = db.Column('data', db.JSON ) 
    
