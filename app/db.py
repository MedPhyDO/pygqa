# -*- coding: utf-8 -*-

__author__ = "R. Bauer"
__copyright__ = "MedPhyDO - Machbarkeitsstudien des Instituts für Medizinische Strahlenphysik und Strahlenschutz am Klinikum Dortmund im Rahmen von Bachelor und Masterarbeiten an der TU-Dortmund / FH-Dortmund"
__credits__ = ["R.Bauer", "K.Loot"]
__license__ = "MIT"
__version__ = "0.2.1"
__status__ = "Prototype"

from safrs import jsonapi_rpc, errors # rpc decorator
from sqlalchemy import text, func, case, and_, or_ #, inspect
from sqlalchemy.schema import Index
from sqlalchemy.types import String, Integer, Date
import operator
import pandas as pd

import os.path as osp
import json
from time import strptime, strftime

from isp.safrs import ispSAFRSModel, isoDateType, db
from isp.config import ispConfig

class gqadb( ispSAFRSModel ):
    """
        description: Geräte QA - Datenbank mit Auswertungen

    ----

        __bind_key__ same as config database main 

        index(onetest) : 'unit', 'energy', 'test', 'date', 'group'
        
        - date und group auch im index damit mehrere pro jahr/monat möglich sind

    """

    __onetest_fields__ = ['unit', 'energy', 'test', 'date', 'group']
    __table_args__ = (
        ( Index('onetest', *__onetest_fields__, unique=True) ),
        { 'extend_existing': True }
    )
    __tablename__ = 'gqadb'
    __bind_key__ = 'gqadb'
    
    id = db.Column('id', db.Integer, primary_key=True, unique=True, autoincrement=True)
    unit = db.Column('unit', db.String(25), nullable=False)
    energy = db.Column('energy', db.String(25), nullable=False)
    test = db.Column('test', db.String(25), nullable=False)
    date = db.Column('date', isoDateType, nullable=False) # TODO: YYYYMMDD
    group = db.Column('group', db.Integer, nullable=False)
    acceptance = db.Column('acceptance', db.Integer, nullable=False)
    year = db.Column('year', db.Integer, nullable=False)
    month = db.Column('month', db.Integer, nullable=False)
    data = db.Column('data', db.JSON ) 

    """
    Add a simple update() method to instances that accepts
    a dictionary of updates.
    """
    def update_values(self, values):
        for k, v in values.items():
            setattr(self, k, v)

    """
    Add a simple update() method to instances that accepts
    a dictionary of updates.
    """
    @classmethod
    def _doUpdate(cls, values):
        instance = None
        if "id" in values:
            instance = cls.get_instance( values["id"] )
            if instance:
                instance = instance._s_patch( **values )

        return instance
    
    """
    Wrapper to _s_post

    """
    @classmethod
    def _doInsert(cls, values):
        return cls._s_post(**values)
    
    """
    Add a simple update() / insert() method to instances that accepts
    a dictionary of updates.
    """
    @classmethod
    def _doUpsert(cls, values):
        instance = None
        try:
            if "id" in values:
                instance = cls.get_instance( values["id"] )
                if instance:
                    instance = instance._s_patch( **values )
                else: 
                    instance = cls._s_post(**values)
            else: 
                instance = cls._s_post(**values)
        except errors.GenericError as exc:
            print( exc )
        return instance
    
       
    @classmethod
    def getYearQueryString(cls, year):
        session = cls._get_session()
        query = cls.query
      
        query = query.filter( operator.eq( cls.year, year ) )
        
        engine = cls._get_engine()
        full_query = query.statement.compile( engine, compile_kwargs={"literal_binds": True} ) 
        return full_query

    @classmethod
    def years( cls ):
        session = cls._get_session()
        query = ( session
            .query(cls.year)
            .order_by( cls.year )
            .group_by( cls.year ) 
        )
        years = [r["year"] for r in cls._int_query( query, flat=True )["data"]]
        return years
    
    @classmethod
    def upsert( cls, data: dict={} ):
        """_summary_

        Parameters
        ----------
        data : dict, optional
            _description_, by default {}

        Returns
        -------
        _type_
            eingefügter datensatz
        """

        query = cls.query
        filter = []
        if "id" in data:
            filter.append( operator.eq( cls.id, data["id"] ) )
        else:
            # wenn keine id in data dann onetest index verwenden
            hasAllIndexFields = True
            for field in cls.__onetest_fields__:
                if not field in data:
                    hasAllIndexFields = False
                else:
                    if field == "date":
                        d = strptime(data["date"], "%Y%m%d")
                        data["date"] = strftime("%Y-%m-%d", d)
                    attr = cls._s_jsonapi_attrs[field] # if key != "id" else cls.id
                    
                    filter.append( operator.eq( attr, data[field] ) )
                
            # query nur durchführen wenn alle IndexFields da sind
            if not hasAllIndexFields:
                filter = [text("1=2")]

        query = query.filter( and_(*filter) )

        # gibt es eine id (record gefunden) dann update sonst insert
        try:
            rec = query.first()
            data["id"] = rec.id
        except Exception as exc:
            pass

        instance = cls._doUpsert( data )
        return instance
    
        '''
        _data = {
        #    "id" : 2305,
            "unit" : "TrueBeamSN2898",
            "energy" : "6x",
            "test" : "MT_4.1.2",
            "date" : "2025-01-18", # WARNING: Invalid datetime.date time data '20240116' does not match format '%Y-%m-%d' for value "20240116"
            "group" : 0,
            "acceptance" : 5,
            "year" : 2024,
            "month": 1,
            "data" : { "A": 0 }
        }
        

        # stmt = select(self.gqadb).filter(self.gqadb.id == 1)
        # session = self.gqadb._get_session()
        # session = cls._get_session()
        # query = session.query( self.gqadb.id )
        # rs = session.execute(stmt)
        # query = query.filter( sql.and_(**data))
        # query = query.get( data )
        
        # config = ispConfig()

        instance= None
        if id:
            data["id"] = id
            instance = cls._doUpdate(data)
        else:
            instance = cls._doInsert(data)

        #engine = cls._get_engine()
        #full_query = query.statement.compile( engine, compile_kwargs={"literal_binds": True} ) 
       
        #print( full_query )
        # 
        ''' 

        # print( "instance", instance )
        
        # safrs rückgabe
        #data = dict( instance )
        data = cls._int_query( query )


        # pandas rückgabe
        '''
        engine = cls._get_engine()
        full_query = query.statement.compile( engine, compile_kwargs={"literal_binds": True} ) 
        df = pd.read_sql_query(sql=full_query, con=engine  )
        pandas_data = df.to_dict( orient="records" )
        '''
        # print( full_query)
        #
        #print( result )
        return cls._int_json_response( {
            "data" : data
        })
 