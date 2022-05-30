# -*- coding: utf-8 -*-
from safrs import jsonapi_rpc
from flask import Response
from sqlalchemy import func, case

from isp.safrs import db, ispSAFRSModel, isoDateType, isoDateTimeType

class dbtestsrel( ispSAFRSModel ):
    """
        description:  Tests - Test von ispSAFRSModel mit relationen
        ---
        
    """
    __table_args__ = {
       'extend_existing': True,
     #  'useexisting': True
    }
        
    __bind_key__ = 'tests'
    
    __tablename__ = "dbtestsrel"
    
    id = db.Column('id', db.Integer, primary_key=True, unique=True, autoincrement=True)
    dbtests_id = db.Column( 'dbtests_id', db.Integer, db.ForeignKey("dbtests.id") ) 
    
    rstring = db.Column('rstring', db.String, nullable=True) # 

    rdate = db.Column('rdate', db.Date, nullable=True) # YYYYMMDD
    rinteger = db.Column('rinteger', db.Integer, nullable=True)
    rdata = db.Column('rdata', db.JSON ) # .. todo::json type?
    
    # relationen 
    dbtests = db.relationship(
        "dbtests", 
        back_populates="dbtestsrel", 
        foreign_keys=[dbtests_id] 
    ) # one to many
    

class dbtests( ispSAFRSModel ):
    """
        description:  Tests - Test von ispSAFRSModel mit relationen
        ---
        
        In der Datenbank wird immer komplett abgelegt
        
       
        Specify 'extend_existing=True' to redefine options and columns on an existing Table object.


        Numeric auch DECIMAL
        
        precision=None,
        scale=None,
        decimal_return_scale=None, 
        asdecimal=True, - es wird ein formatierter string zurückgegeben (gerundet)
        
        db.Float( precision=5, asdecimal=True, decimal_return_scale=4 )
    """
    __table_args__ = {
        'extend_existing': True,
       # 'useexisting': True
    }
    
    __bind_key__ = 'tests'
    
    __tablename__ = "dbtests"
    
    id = db.Column('id', db.Integer, primary_key=True, unique=True, autoincrement=True)
    string = db.Column('string', db.String, nullable=False) #
    date = db.Column('date', isoDateType, nullable=True ) # YYYY-MM-DD
    
    isodatetime = db.Column('isodatetime', isoDateTimeType, nullable=True) # YYYY-MM-DD HH:mm:SS
    isodate = db.Column('isodate', isoDateType, nullable=True) # YYYY-MM-DD
    
    integer = db.Column('integer', db.Integer, nullable=True)
    float = db.Column('float', db.Float( asdecimal=True ), nullable=False, default=0) # (5,True,4) gibt 0.3333 als str
    decimal = db.Column('decimal', db.DECIMAL( 5, 2, 1, True ), nullable=False, default=0)
    numeric = db.Column('numeric', db.Numeric( 5, 2, 3, False ), nullable=False, default=0 )

    active = db.Column('active', db.Integer, nullable=False, default=1)
    tags = db.Column('tags',  db.String, nullable=True)

    gruppe = db.Column('gruppe',  db.String, nullable=True)
    data = db.Column('data', db.JSON ) # .. todo::json type?
 
    # relationen
    dbtestsrel = db.relationship(
        "dbtestsrel", 
        back_populates="dbtests", 
        foreign_keys=[dbtestsrel.dbtests_id], 
        lazy="dynamic", 
        cascade="delete"
    ) # one to many
    
    @classmethod
    @jsonapi_rpc( http_methods=['GET'] )
    def pandas( cls, **kwargs ):
        """
        .. restdoc::

        description : Testdaten ausgabe
        parameters:
            - name : _ispcp
              default : {}
              description : zusätzliche parameter
              type: object
            - name: art
              description : bestimmt die art
              default :
            - name: filter
              description : rql Filterbedingung
        ----

        Parameters
        ----------
        **kwargs : dict
            named arguments allows you to pass keyworded variable length of arguments to a function.

        """
        import pandas as pd

        query = cls.query

        data_frame = pd.read_sql_query(sql=str(query), con=cls._get_connection() )

        # pandas dataframe als Tabelle
        table_html = (
            data_frame.round(2).style
            .set_uuid( "test_pandas_" )
            .set_table_attributes('class="dbtests sysinfo layout-fill-width"') \
            #.format( { 'Gantry':'{0:.1f}', 'Kollimator':'{0:.1f}', 'delta':'{0:.3f}'} )
            .hide_index()
            #.highlight_max(subset=["delta"], color='yellow', axis=0)
            .render()
        )

        style = '''
            table.dbtests{
                margin-bottom: 5px;
                border-collapse: collapse;
            }
            table.dbtests, table.dbtests th, table.dbtests td{
                border: 1px solid silver;
            }
            table.dbtests tr:nth-child(even) {
        		background-color: #f2f2f2;
        	}
            table.dbtests th.level0 {
            	min-width: 50px;
        	}

        '''
        html = '''

          <div class="_sysinfo">
          {}
          </div>

        <style>{}</style>

        '''.format(
            table_html.replace("style", "div"),
            style

        )
        #print( data_frame )

        return Response( html , mimetype=' application/javascript') #mimetype='text/html'

        #return cls._int_json_response( _result )
        
    @classmethod
    @jsonapi_rpc( http_methods=['GET'] )
    def test( cls, **kwargs ):
        """
            description : Testdaten ausgabe
            parameters:
                - name : _ispcp
                  default : {}
                  description : zusätzliche parameter
                  type: object
                - name: art
                  description : bestimmt die Art des Tests
                  required : true
                - name: filter
                  description : rql Filterbedingung
            ----
            
        """
        
        _result = {}

        if kwargs["art"] == 'AppDialog':
            cls.appDialog("Test AppDialog", {
                "content": "Einfach nur ein Dialog",
                "dimensions" : [ 200, 200]
            } )
        elif kwargs["art"] == 'AppDialog403':
            cls.appDialog("Test AppDialog", {
                "content": "AppDialog mit AppError und code 403",
                "dimensions" : [ 200, 200]
            }, 403 )
            

        elif kwargs["art"] == 'AppError':
            cls.appError("Test AppError", "App-Error ohne code" )
        elif kwargs["art"] == 'AppError403':
            cls.appError("Test AppError", "App-Error mit code 403", 403 )

        elif kwargs["art"] == 'AppInfo':
            cls.appInfo("Test AppInfo", "App-Info ohne code" )
        elif kwargs["art"] == 'AppInfo203':
            cls.appInfo("Test AppInfo", "App-Info mit code 203", 203 )
            
        elif kwargs["art"] == 'rqlFilter':
            pass
        
        elif kwargs["art"] == 'query':
            # wird in query abgelegt
            cls._log_query( None, True )
            
            cls._log_query( cls.query.with_entities( cls.string ), True )
            
        else:

            _result = {
                "data" : [
                    {"attributes": {"Geraet": "AL", "hasChildren": 1, "label": "AL"}, "type": "Ersatz"},
                    {"attributes": {"Geraet": "la", "hasChildren": 1, "label": "LA20"}, "type": "Ersatz"},
                    {"attributes": {"Geraet": "vb", "hasChildren": 1, "label": "VitalBeam"}, "type": "Ersatz"},
                    {"attributes": {"Geraet": "tb", "hasChildren": 1, "label": "TrueBeam"}, "type": "Ersatz"}
                ]
            }
        return cls._int_json_response( _result )
    
