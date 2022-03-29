# -*- coding: utf-8 -*-

"""
safrs
=====

swagger yaml definition
-----------------------

The definition is at the beginning of the docstring and starts with ``.. restdoc::`` for sphinx 

It can be terminated with ``----`` to add further documentation for sphinx 

example ::

    description -
    summary -
    args - jsonapi_rpc "POST" method arguments
    parameters - query string parameters
        - name:
          description:
          type:
          format:
          default:
          in: query - default: query
          required: false|true - default: false

    pageable -
    filterable - fields mit anzeigen

help und snippets::

    from flask import current_app
    print( current_app.config )

    import safrs
    print( safrs.SAFRS.config )

examples ::

    /api/<modul>/?fields[<modul>]=<feld1,feld2>&_ispcp={"Test":"Hallo"}&filter=eq(aktiv,true),in(<modul>,(Rapp,SA43))
    /api/<modul>/groupby?fields[<modul>]=<feld1,feld2>&groups=Geraet&filter=eq(aktiv,true)

    /api/<modul>/groupby?fields[<modul>]=<feld1,feld2>&groups=Geraet&filter=eq(aktiv,true)
    /api/<modul>/groupby?fields[<modul>]=<feld1,feld2>&groups[Ersatz]=Geraet&filter=eq(aktiv,true)


CHANGELOG
=========

0.1.4 / 2022-03-28
- remove error check in wrapped_fn() use original abort()
- add check for empty String in iso2date()
- add method _as_dict() to ispSAFRS
- change ispSAFRS classmethod getConnection() to _get_connection()
- change ispSAFRS.undefined() change array to object as result in data
- change result info from list to dict  
- add python_type to isoDateType and isoDateTimeType to avoid "Failed to get python type for column" message
- change find column in _int_groupby() 
- remove delimiter from groupby() and create seperate function groupsplit()

0.1.3 / 2022-01-03
- remove entities check in RQLQuery.rql_parse()

0.1.2 / 2021-12-28
------------------
- changes for Python 3.8
- add count check in _int_json_response and __abstract__ in ispSAFRSModel

0.1.1 / 2021-05-19
------------------
- changes in additional api results, add _extendedSystemCheck

0.1.0 / 2021-01-16
------------------
- First Release

"""

__author__ = "R. Bauer"
__copyright__ = "MedPhyDO - Machbarkeitsstudien des Instituts für Medizinische Strahlenphysik und Strahlenschutz am Klinikum Dortmund im Rahmen von Bachelor und Masterarbeiten an der TU-Dortmund / FH-Dortmund"
__credits__ = ["R. Bauer", "K.Loot"]
__license__ = "MIT"
__version__ = "0.1.4"
__status__ = "Prototype"

import json
import re

from functools import wraps

from flask_sqlalchemy import SQLAlchemy
from flask import Response, request, current_app

import sqlalchemy
from sqlalchemy import func, text # , case, or_, inspect
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.orm import Query as BaseQuery
import sqlalchemy.types as types

from safrs import SAFRSBase  # db Mixin
from safrs.config import get_request_param

from safrs import SAFRSFormattedResponse, jsonapi_format_response, log #, paginate, SAFRSResponse
from safrs import jsonapi_rpc # rpc decorator

from flask_restful_swagger_2.swagger import get_parser
from flask import jsonify

from safrs.util import classproperty
from sqlalchemy.ext.hybrid import hybrid_property

db = SQLAlchemy()

from rqlalchemy import RQLQueryMixIn
from pyrql import RQLSyntaxError
from pyrql import parse

from datetime import datetime, date

# ------------ Typen Umwandlungen

def iso2date( value:str=None, toDate:bool=False ):
    """Converts a string to a ``datetime`` or ``date`` object via fromisoformat or strptime. 

    First try a conversion via fromisoformat 
    In case of errors it tries to convert it with strptime 

    Value examples::
        2018-04-15 - datetime.datetime(2018, 4, 15, 0, 0)
        2018-04-15 14:36 - datetime.datetime(2018, 4, 15, 14, 36)
        2018-04-15 14:36:25 - datetime.datetime(2018, 4, 15, 14, 36, 25)

        20180415 - datetime.datetime(2018, 4, 15, 0, 0)
        20180415 14:36:25 - datetime.datetime(2018, 4, 15, 14, 36, 25)
        20180415 14:36 - datetime.datetime(2018, 4, 15, 14, 36)
        20180415 14 - datetime.datetime(2018, 4, 15)

        with toDate=True

        2018-04-15 14:36:25 - datetime.date(2018, 4, 15)
        20180415 14:36:25 - datetime.date(2018, 4, 15)

    Parameters
    ----------
    value : str
        String with dates .
    toDate : bool
        If true, returns a date object instead of datetime. Default is False.

    Returns
    -------
    datetime|None
        Converted ISO String or None 

    """
    result = None
    
    if value and isinstance(value, str) and not value == "":
        try:
            result = datetime.fromisoformat( value )
        except ValueError:
            
            pass
             
        if not result:
            if len(value) >= 17:
                try:
                    result = datetime.strptime(value[:17], "%Y%m%d %H:%M:%S")
                except ValueError:
                    pass
            if not result and len(value) >= 14:
                try:
                    result = datetime.strptime(value[:14], "%Y%m%d %H:%M")
                except ValueError:
                    pass
            if not result and len(value) >= 8:
                try:
                    result = datetime.strptime(value[:8], "%Y%m%d")
                except ValueError:
                    pass
        
    else:
        result = value
        
    if result and toDate:
        result = result.date()
            
    return result


# ------------ Typen Erweiterungen

class isoDateType( types.TypeDecorator ):
    """TypeDecorator for ISO-8601 date.

    Uses iso2date() for conversion.

    """

    impl = types.Date
    
    @property
    def python_type(self):
        return date
    
    def __init__(self, *arg, **kw):
        types.TypeDecorator.__init__(self, *arg, **kw)
            
    def process_bind_param(self, value, dialect):
        return iso2date( value, True)



class isoDateTimeType( types.TypeDecorator ):
    """TypeDecorator for ISO-8601 datetime.

    Uses iso2date() for conversion.

    """

    impl = types.DateTime
    
    @property
    def python_type(self):
        return datetime
    
    def process_bind_param(self, value, dialect):
        return iso2date( value, False)


# Filter abfrage für rql
class RQLQuery(BaseQuery, RQLQueryMixIn):
    _rql_default_limit = 10
    _rql_max_limit = 100

    def rql_parse(self, rql, limit=None):
        """Like rql, but it is only evaluated and the query is not changed .

        Parameters
        ----------
        rql : string
            rql query string.
        limit : int, optional
            Limit specification, but not used here . The default is None.

        Raises
        ------
        NotImplementedError

        Returns
        -------
        _rql_where_clause

        """
        
        expr = rql

        if not expr:
            self.rql_parsed = None
            self.rql_expr = ""

        else:
            self.rql_expr = expr

            try:
                self.rql_parsed = parse(expr)
            except RQLSyntaxError as exc:
                raise self._rql_error_cls("RQL Syntax error: %r" % (exc.args,))

        self._rql_select_clause = []
        self._rql_values_clause = None
        self._rql_scalar_clause = None
        self._rql_where_clause = None
        self._rql_order_by_clause = None
        self._rql_limit_clause = None
        self._rql_offset_clause = None
        self._rql_one_clause = None
        self._rql_distinct_clause = None
        self._rql_group_by_clause = None
        self._rql_joins = []

        # rql auswerten
        self._rql_walk(self.rql_parsed)

        return self._rql_where_clause


def ispSAFRS_decorator( fn ):
    """Prepare and execute API calls.

    Note: In decorator, wrapped_fn() is called to process the request 

    JSON:API Response formatting follows filter -> sort -> paginate

    Parameters
    ----------
    fn : safrs/jsonapi.py|SAFRSRestAPI

    Returns
    -------
    wrapped_fn : func

    """

    @wraps(fn)
    def wrapped_fn(*args, **kwargs):
        """Function to process an API request.

        types of fn - safrs/jsonapi.py

             GET /api/<modul> - SAFRSRestAPI.get
             GET /api/<modul>/11 - SAFRSRestAPI.get
             GET /api/<modul>/groupby/? - SAFRSJSONRPCAPI
             GET /api/<modul>/items_geraet/? - SAFRSJSONRPCAPI

             SAFRSRestAPI - results - __qualname__
                 .get - jsonify(result)
                 .post - response
                 .patch - response
                 .delete - {}, HTTPStatus.NO_CONTENT

             SAFRSJSONRPCAPI - safrs/jsonapi.py - __qualname__
                 .get - jsonify(result)
                 .post - response

             SAFRSRestRelationshipAPI - safrs/jsonapi.py - __qualname__
                 .get - jsonify(result)
                 .patch - response
                 .post - {}, HTTPStatus.NO_CONTENT - we can return result too but it's not necessary per the spec
                 .delete - {}, HTTPStatus.NO_CONTENT

        SAFRSRestAPI::

            if _s_object_id is available, only one record object is fetched, otherwise a list of record objects 
            
            id = kwargs.get( fn.SAFRSObject._s_object_id , None)

        Parameters
        ----------
        *args : tuple
            with an object.
            .. code::

                /api/gqadb/?zahl=12 - ( safrs._api.gqadb_API, ) - {}
                /api/gqadb/2020?zahl=12 - ( safrs._api.gqadb_API, ) - {'gqadbId': '2020'}
                /api/gqadb/test?zahl=12 - ( safrs._api.method_gqadb_test, ) - {}
                /api/gqa?zahl=12 -  ( safrs._api.gqa_API, ) - {}
                /api/gqa/2020?zahl=12 - ( safrs._api.gqa_API, ) - {'gqaId': '2020'}
                /api/gqa/test?zahl=12 - ( safrs._api.gqa_API, ) - {'gqaId': 'test'}

        **kwargs : dict
            any parameters. 

        Returns
        -------
        result : result
            ResultObject.

        Tests::

            log - q, request.endpoint, safrs_obj._s_object_id, json.dumps(kwargs)
            /api/gqadb - ['SAFRSRestAPI', 'get'] - api.gqadb - gqadbId - {}
            /api/gqadb/2020 - ['SAFRSRestAPI', 'get'] - api.gqadbId - gqadbId - {"gqadbId": "2020"}
            /api/gqadb/test - ['SAFRSJSONRPCAPI', 'get'] - api.gqadb.test - gqadbId - {}

            /api/gqa - ['SAFRSRestAPI', 'get'] - api.gqa - gqaId - {}
            /api/gqa/2020 - ['SAFRSRestAPI', 'get'] - api.gqaId - gqaId - {"gqaId": "2020"}
            /api/gqa/test - ['SAFRSRestAPI', 'get'] - api.gqaId - gqaId - {"gqaId": "test"}

            bei /api/gqadb/test

            fn.__name__ - get
            fn.__module__ - safrs.jsonapi
            request.endpoint - api.gqadb.test
            safrs_obj.__module__ - app.db
            safrs_obj.__name__ - gqadb
            safrs_obj._api.prefix - /api
        """


        # das verwendete Object bestimmen um SAFRSRestRelationshipAPI zu erkennen
        q = fn.__qualname__.split(".")
        # die Aufruf Methode: get,post,patch,delete
        method = q[1]


        # mit SAFRSRestRelationshipAPI dessen target verwenden
        if q[0] == "SAFRSRestRelationshipAPI":
            # eine SAFRSRestRelationshipAPI hat keine _int_init funktion
            result = fn(*args, **kwargs)

            # zum weiterarbeiten das _target Object verwenden
            safrs_obj = fn.SAFRSObject._target

        else:
            safrs_obj = fn.SAFRSObject

        #
        # Das SAFRSObject vor jedem Aufruf Vorbereiten
        #
        safrs_obj._int_init( )

        # func_name wird für den _int_call aufruf benötigt
        # - da ein Aufruf von fn() request parameter
        #   und nicht kwargs an die Aufzurufende Funktion weitergibt
        #   wird bei Angabe von func_name die Funktion mit kwargs uber _int_call aufgerufen
        func_name = None

        swagger_path = ""

        # nur bei get parameter prüfen
        if method == "get":

            # Merker für Variante b: objectId wird später wieder eingefügt
            objectId = None
            # Argumente parsen
            doArgParse = False
            # sonderbehandlung bei request.endpoint /api/gqa/<func>
            #  ist api.gqaId - sollte aber api.gqa.<func> sein
            #  der letzte Teil von request.path ist safrs_obj._s_object_id in kwargs und eine funktion
            name = safrs_obj.__name__.lower()

            # nur bei einer eigener Erweiterung ohne Datenbank
            if hasattr( fn.SAFRSObject, "no_flask_admin") and fn.SAFRSObject.no_flask_admin == True:
                '''
                Möglichkeiten:
                    a) /class/ : api_list in class aufrufen
                    b) /class/{objectId}/ : keine Funktion objectId vorhanden also api_get aufrufen
                    c) /class/test : Vorhandene Funktion test in class aufrufen, objectId (test) aus den Parametern entfernen

                '''
                doArgParse = True
                variante = ""
                # swagger_path zuerst nur der Modulname
                swagger_path = "/{}".format(name)

                func = None
                # b, c) gibt es eine passende jsonapi_rpc methode
                if safrs_obj._s_object_id in kwargs:
                    #log.warning("safrs_obj.object_id in kwargs")
                    # auf möglichkeit c) testen
                    try:
                        func = getattr(safrs_obj, kwargs[ safrs_obj._s_object_id ], None)
                        variante = "c"
                    except: # pragma: no cover
                        # getattr gibt einen Fehler bei query
                        log.warning("keine func: getattr gibt einen Fehler bei query")
                        pass

                    # also b) verwenden
                    if not func:
                        try:
                            func = getattr(safrs_obj, 'api_get', None)
                            if func:
                                variante = "b"
                        except: # pragma: no cover
                            # getattr gibt einen Fehler bei query
                            log.warning("no func: getattr gibt einen Fehler bei query")
                            pass
                else:
                    # ohne object_id Möglichkeit a)
                    try:
                        func = getattr(safrs_obj, "api_list", None)
                        if func:
                            variante = "a"
                    except: # pragma: no cover
                        # getattr gibt einen Fehler bei query
                        log.warning("no func: getattr gibt einen Fehler bei query")
                        pass

                #log.warning("{} and __rest_doc variante: {}".format(func, variante) )
                # wurde eine Funktion gefunden und hat sie ein __rest_doc dann auswerten
                if func and hasattr(func, '__rest_doc'):
                    func_name = func.__name__

                    if variante == "a":
                        swagger_path = "/{}/".format( name )
                    elif variante == "b":
                        # Remember objectId for later insertion 
                        objectId = kwargs[ safrs_obj._s_object_id ]
                        swagger_path = "/{}/{}/".format( name, "{" + safrs_obj._s_object_id + "}" )
                    elif variante == "c":
                        swagger_path = "/{}/{}".format(name, func_name )
                else:
                    # there is no matching function so show error 
                    status_code = 400
                    message = "funktion not found"

                    safrs_obj.appError(
                        "{}".format( message ),
                        str( status_code )
                    )
                    result = jsonify( {} )
                    result.status_code = status_code

                    return result


            elif q[0] == "SAFRSJSONRPCAPI":

                # this area is called in db for groupby, undefined or functions 
                doArgParse = True
                # Determine the request endpoint - needed to check Swagger parameters 
                # the first part is always api the last part is the function to be called 
                ep_list = request.endpoint.split(".")
                func_name = ep_list[-1]
                swagger_path = "/{}/{}".format(name, ep_list[-1])

            else:

                # einfach durchlaufen ohne die Argumente zu prüfen
                # SAFRSRestRelationshipAPI - get - dbtestsrelId - {"dbtestsId": "2"}
                doArgParse = False

            # only use parameters stored in swagger and convert them if necessary 
            # args = dict(request.args) is used in safr's methods 
            # Note: function _int_parse_args() removes _s_object_id
            if doArgParse:
                kwargs = safrs_obj._int_parse_args( kwargs, method, swagger_path )
                # insert remembered objectId 
                if objectId:
                    kwargs[ safrs_obj._s_object_id ] = objectId

        elif method == "post":

            pass

        request.groups = {}
        # Parse the jsonapi groups and groups[] args
        for arg, val in request.args.items():

            # https://jsonapi.org/format/#fetching-sparse-fieldsets
            groups_attr = re.search(r"groups\[(\w+)\]", arg)

            if groups_attr:
                group_type = groups_attr.group(1)
                request.groups[group_type] = val.split(",")
            elif arg == "groups":
                # groups without a other table use the current table
                request.groups[ safrs_obj.__name__ ] = val.split(",")

        # execute function in class else call fn itself 
        if func_name:
            # call function in fn.SAFRSObject
            meth = fn.SAFRSObject
            meth.appInfo( "wrapped_fn", "function: {}.{}.{}()".format( meth.__module__, meth.__name__, func_name ) , area="safrs")

            if hasattr(meth, func_name):
                if func_name[:4] == "api_":
                    # api_ functions require the class itself as the first parameter 
                    result = getattr( meth, func_name )( meth, **kwargs )
                else:
                    result = getattr( meth, func_name )( **kwargs )
            else: # pragma: no cover
                # can not actually happen because above is tested 
                meth.appError( "ispSAFRSDummy", "missing function: {}.{}.{}()".format( meth.__module__, meth.__name__, func_name ) )
                result = meth._int_json_response( {} )

            # if not dict, list or SAFRSFormattedResponse stop here. Result maybe html, pdf, ...
            if not type( result ) in [dict, list, SAFRSFormattedResponse]:
                return result

            try:
                result = jsonify( result )
            except Exception as exc:  # pragma: no cover
                status_code = getattr(exc, "status_code", 500)
                message = getattr(exc, "message", "unknown error")
               
                safrs_obj.appError(
                        "{} - {}".format( func_name, message ),
                        str( status_code )
                )
                result = jsonify( {} )

        else:
            #
            # call the original function 
            
            # Note: this calls on errors :
            #   errors = dict(title=title, detail=detail, code=api_code)
            #   abort(status_code, errors=[errors])
            
            result = fn(*args, **kwargs)
            
            
        #----------------------------------------------------------------------
        # evaluation of results 
        #

        # fetch result and insert additional information 
        _data = { }

        _data = result.get_json()

        # _data must always be a dict (dict, list, SAFRSFormattedResponse)
        if not type( _data ) == dict:
            # is _data a list use as data
            if type( _data ) == list:
                _data = {"data": _data}

        # data area in _data must always be list 
        if not 'data' in _data or _data['data'] is None:
            _data['data'] = []

        if not 'meta' in _data:
            # without meta insert count
            _data['meta'] = {
                "count": len( _data.get("data", [] ) )
            }

        if not 'count' in _data['meta'] or _data['meta']['count'] is None:
            _data['meta']['count'] = 0

        # offset for determining the last one in the grid 
        try:
            _data['meta']["offset"] = int( get_request_param("page_offset") )
        except ValueError: # pragma: no cover
            _data['meta']["offset"] = 0
           

        # add the information from _resultUpdate (App-Error, App-Info,...) from databaseobject
        #
        _data.update( safrs_obj._resultUpdate )

        try:
            result.set_data( json.dumps( _data ) )
        except : # pragma: no cover
            result.status_code = 500
            log.error("wrapped_fun data error")

        # set http status code if given
        if "status_code" in result.json:
            result.status_code = result.json["status_code"]

        return result

    return wrapped_fn


# ----------- ispSAFRS without db.Model
class ispSAFRS(SAFRSBase, RQLQueryMixIn):

    __abstract__ = True

    custom_decorators = [ispSAFRS_decorator]

    _resultUpdate = {
        "infos": {}
    }

    exclude_attrs = []  # list of attribute names that should not be serialized
    exclude_rels = []  # list of relationship names that should not be serialized

    _config: None
    _configOverlay: {}

    @classmethod
    def access_cls(cls, key:str=""):
        """try to determine the model specified by key

        Parameters
        ----------
        key : str
            name of searched model .

        Returns
        -------
        None|model
            the found model or None.

        """
        if hasattr(cls, "_decl_class_registry") and key in cls._decl_class_registry:
            return cls._decl_class_registry[key]
        elif hasattr(cls, "metadata") and key in cls.metadata.tables: # pragma: no cover
            return cls.metadata.tables[key]
        else:
            if key in sqlalchemy.__dict__:
                return sqlalchemy.__dict__[key]
        return None
    
    def _as_dict(self):
       """.. restdoc::
       summary : gives record as dict
        
       """
       return {c.name: getattr(self, c.name) for c in self.__table__.columns}
   
    @classmethod
    def _get_connection(cls):
        """Get connetion string from session bind or config binds.
        Returns
        -------
        connection: str
            connetion string
        """
        query = cls.query
        if hasattr(cls, "__bind_key__"):
            binds = query.session.app.config.get("SQLALCHEMY_BINDS")
            connection = binds[cls.__bind_key__]
        else:
            connection = query.session.bind
        return connection

    @classmethod
    def _get_session(cls):
        """Get session of query class.
        Returns
        -------
        connection: object
            session object
        """
        return cls.query.session
      
    @classproperty
    def _s_column_names(cls):
        """
            :return: list of column names
        """
        return [c.name for c in cls._s_columns]

    @classmethod
    def _s_column_by_name(cls, name, model=None):
        """Get column by name. If model then get from model instead cls
            :return: get column with name
        """
        column = None
        if model == None:
            # use __mapper__ from class
            if hasattr(cls, "__mapper__"):
                column = cls.__mapper__.columns.get( name )
        if isinstance(model, sqlalchemy.sql.schema.Table):
            column = model.columns.get( name )  
        else:
            column = getattr( model, name, None )
       
        return column

    @classmethod
    def _int_init( cls ):
        """Initialization before each call.

        Sets _resultUpdate before each call::

            {
                "infos" : {}
                "errors" : []
            }

        Provides Flask Server's _config and _configOverlay 

        Note: This function is called from ispSAFRS_decorator 

        Returns
        -------
        None.

        """
        cls._resultUpdate = {
            "infos" : {},
            "errors" : []
        }
        cls._config = current_app._config
        cls._configOverlay = current_app._configOverlay
   

    @classmethod
    def _int_parse_args(cls, kwargs:dict={}, method=None, swagger_path=None ):
        """Parses the request parameters with the information from cls._swagger_paths .

        Swagger datatypes::

            string
            number
            integer
            boolean
            array
            object

        Parameters
        ----------
        kwargs : dict, optional
            All request parameters. The default is {}.
        method : str, optional
            The request method. (For example ``'GET'`` or ``'POST'``). The default is None.
        swagger_path : str, optional
            The swagger description path matching the request. The default is None.

        Returns
        -------
        has_args : dict
            The checked parameters .

       Note: RequestParser can also be specified in this way::

            from flask_restplus import RequestParser
            parser = RequestParser()

        """
        if not method:
            method=request.method.lower()

        paths = cls._api.get_swagger_doc().get("paths", {})

        # get parameters for swagger_path (cls._swagger_paths)
        parameters = paths.get(swagger_path, {}).get( method, {} ).get("parameters", {} )

        parser = get_parser( parameters )
        # collect all errors  (TypeError in value)
        parser.bundle_errors = True
        # parse request
        args = parser.parse_args( )

        has_args = {}
        # alle args druchgehen und fehlerhafte rauswerfen
        for key, value in args.items():
            if not type(value) == TypeError:
                # ohne Fehler sofort verwenden
                has_args[key] = value
            else:

                # value aus request nehmen
                value = request.args.get(key, "")

                check_type = ""
                # Versuchen den parameter selbst umzuwandeln (object)
                # parameter suchen - immer defaults type=string
                for parameter in parameters:
                    #log.warning("_int_parse_args parameter {}".format( json.dumps(parameter) ) )
                    if parameter.get( "name", "") == key:
                        check_type = parameter.get("type", "string" )
                        break # schleife abbrechen

                # umwandlung versuchen
                if not check_type: # pragma: no cover
                    # Fehlermeldung in appError - sollte auber nicht vorkommen siehe parameter suchen
                    cls.appError( "swagger Parameter Error", "{}={}".format( key, value ) )
                elif check_type == "object":
                    # swagger freeform object (arbitrary property/value pairs)
                    try:
                        has_args[key] = json.loads( value )
                    except:  # includes simplejson.decoder.JSONDecodeError
                        cls.appError( "swagger Parameter Json Error", "{}={}".format( key, value ) )
                    pass
                elif check_type == "number":
                    has_args[key] = float( value )

                else:
                    has_args[key] = value

        return has_args

    @classmethod
    def _int_add_meta( cls, meta:str="App-Info", title:str="", detail:str="", status_code:int=None, area:str="general" ):
        """Insert App-Info, App-Error, App-Dialog, errors information.

        Parameters
        ----------
        meta: str
           type of inserted message
        title : str, optional
            Title of message. The default is "".
        detail : str, optional
            ddetailed message. The default is "".
        status_code: int, optional
            set http status code if given. The default is None.

        Returns
        -------
        None.

        """
        # Versuchen in json umzuwandeln
        
        if type(detail) is str:
          try:
              json_data = json.loads( detail )
              if type(json_data) is dict:
                  detail = json_data
          except:  # includes simplejson.decoder.JSONDecodeError
              
              pass 
        
        if meta in ["App-Dialog", "App-Info"]:
            if meta == "App-Dialog":
                # always use dialog as area
                area = "dialog"
            
            if not area in cls._resultUpdate[ "infos" ]:
                cls._resultUpdate[ "infos" ][area] = []
            cls._resultUpdate[ "infos" ][area].append( { 'title':str(title), 'detail': detail, 'code': status_code } )                
        else:
            cls._resultUpdate[ "errors" ].append( { 'title':str(title), 'detail': detail, 'code': status_code } )
        if status_code:
            cls._resultUpdate[ "status_code" ] = status_code

    @classmethod
    def appInfo(cls, title:str="", detail:str="", status_code:int=None, area:str="general"):
        """Insert App-Info information into infos.

        Parameters
        ----------
        title : str, optional
            Title of Information. The default is "".
        detail : str, optional
            detailed info message. The default is "".
        status_code: int, optional
            set http status code if given. The default is None.
        area: str, optional
            area to insert info. The default is "general".
            
        Returns
        -------
        None.

        """
        cls._int_add_meta( "App-Info", title, detail, status_code, area )

    @classmethod
    def appError(cls, title:str="", detail:str="", status_code:int=None):
        """Insert App-Error information into errors.

        
        Parameters
        ----------
        title : str, optional
            Title of Information. The default is "".
        detail : str, optional
            detailed error message. The default is "".
        status_code: int, optional
            set http status code if given. The default is None.

        Returns
        -------
        None.

        """
        cls._int_add_meta( "App-Error", title, detail, status_code )

    @classmethod
    def appDialog(cls, title:str="", detail:dict={}, status_code:int=None):
        """Insert App-Dialog information for client.

        This information can be used for a dialog display in the client::

            appDialog("Error on insert", { "message" : message, "class" : "myClassname" })

            gives parameters for client Dialog
            {
                "title" => "Error on insert",
    			"message" : message,
    			"class" : "myClassname"
                ... other parameter
    		}

        Parameters
        ----------
        title : str, optional
            Title of Dialog. The default is "".
        detail : str, optional
            detailed dialog message. The default is "".
            If no titel in detail use title parameter
        status_code: int, optional
            set http status code if given. The default is None.  
            
        Returns
        -------
        None.

        """
        if not "title" in detail:
            detail[ "title" ] = title

        cls._int_add_meta( "App-Dialog", title, detail, status_code )

            
    @classmethod
    def _log_query( cls, query=None, always:bool()=False):  
        """log last query informations.
        Only log if sever.logging.safrs higher or equal 10 (info) 
        """
                
        if cls._config.server.logging.get("safrs", 0) >= 10 or always:
            if query:   
                # add query information 
                full_query = query.statement.compile( query.session.bind, compile_kwargs={"literal_binds": True} ) 
                query_info = { 
                    "query": str(full_query), 
                    "params": full_query.params 
                } 
            else:
                query_info = "query is None" 
                
            cls.appInfo("sql-lastquery",  query_info, area="query" )

            
    @classmethod
    def _int_query( cls, query=None, **kwargs):
        """Eine query ohne paginate durchführen.

        Parameters
        ----------
        query : obj
            Das bisherige query Object
        **kwargs : dict
            Beliebige weitere Argumente.
            verwendet wird type

        Returns
        -------
        result : dict::

            - data
            - count
            - meta
            - errors

        _asdict ist in row bei der zusätzlichen Columns durch add_columns
        ohne dies wird die row so verwendet

        """

        cls._log_query( query )
        
        _type = cls.__name__
        if 'type' in kwargs:
            _type = kwargs['type']

        data = []
        if query:
            try:
                for row in query:
                    # dies geht nur wenn in row _asdict vorhanden ist (z.B. group)
                    if "_asdict" in dir(row):
                        _row = row._asdict()
                        _id = None
                        if "id" in _row:
                            _id = _row["id"]
                            del _row["id"]
                       # _id =
                        data.append({
                            "attributes" : _row,
                            "id": _id,
                            "type": _type
                        })
                    else:
                        data.append( row )
            except Exception as exc:
                print( "_int_query", exc )
                cls.appError( "_int_query", str(exc) )
                
        # Anzahl aus query
        count = len( data )
        result = {
             "data" : data,
             "count" : count,
             "meta": {},
             "errors": [],
        }
        
        return result

    @classmethod
    def _int_json_response( cls, result:dict={} ):
        """Interne Json response Funktion.

        Parameters
        ----------
        result : dict, optional
           Beinhaltet: data=None, meta=None, links=None, errors=None, count=None, include=None. The default is {}.

        Returns
        -------
        response : SAFRSFormattedResponse
            Der response mit json formatiertem Result

        """
        response = SAFRSFormattedResponse()
        try:
            # data=None, meta=None, links=None, errors=None, count=None, include=None
            if not "count" in result and "meta" in result and "count" in result["meta"]:
                result["count"] = result["meta"]["count"]
            response.response = jsonapi_format_response( **result )

        except Exception as exc:
            cls.appError( "_int_json_response", str(exc) )

        return response

    @classmethod
    def filter(cls, filter ):
        """Filterangabe im rql format ausgewerten.

        immer wenn filter= angegeben wurde wird diese Funktion aufgerufen
        es wird eine komplexe Filterangabe im rql format ausgewertet

        Parameters
        ----------
        filter : str
            RQL Querystring

        Returns
        -------
        query
            die query mit zusätzlichem Filter

        """
        # interne Filterfunktion aufrufen
        return cls._int_filter( cls.query, filter )


    @classmethod
    def _int_filter(cls, query, qs:str="" ):
        """Die in qs angegebene RQL Filterbedingung auswerten und an query anhängen.

        Parameters
        ----------
        query : obj
            Das bisherige query Object
        qs : str, optional
            RQL Querystring. The default is "".

        Returns
        -------
        query
            die query mit zusätzlichem Filter

        """
        
        cls.appInfo("filter", qs, area="rql" )
        
        # RQLQuery bereitstellen die eigene Klasse muss mit _set_entities angegeben werden
        rql = RQLQuery( cls )
        rql._set_entities( cls )
       
        # rql_filter auswerten
        try:
            rql.rql_parse( qs )
        except NotImplementedError as exc:
            cls.appError("_int_filter", "NotImplementedError: {}".format( exc ) )
            query = query.filter( text("1=2") )
            return query
        except Exception as exc:
            cls.appError("_int_filter", "rql-error: {}".format( exc ) )
            query = query.filter( text("1=2") )
            return query

        # die Bedingung an die query anfügen
        if rql._rql_where_clause is not None:
            query = query.filter( rql._rql_where_clause )
            cls.appInfo("_rql_where_clause", {
               "where": str(rql._rql_where_clause),
               "params" :  query.statement.compile().params
            }, area="rql" )

        return query

    @classmethod
    def _int_groupby(cls, query, params:dict={} ):
        """Internes durchführen einer group query

        Bei einer Angabe von fields werden nur diese für den select bereich verwendet

        Parameters
        ----------
        query : obj
            Das bisherige query Object
        params : dict, optional
            The default is::

            {
                "groups": {},
                "fields": { "<tablename>": ["field1","FieldX"] },
                "labels": { "<tablename>.<fieldname1>": [ "<label1>","<label2>" ], ... }
            }

        Returns
        -------
        query : query
            Die um group ergänzte query
        group_entities: list
            Eine Liste mit den für die Gruppierung verwendeten Feldern::

            {
                "fields[<modul>]": "<feld1,feld2>",
                "group": "<feld1,feld2>",
                "filter": "eq(aktiv,true)"
            }

        ok: bool
            gruppierung konnte erstellt werden

        """
        group_entities = []
        field_entities = []
        _params = {
            "groups": {},
            "fields": {},
            "labels": {},
        }

        _params.update( params )

        #
        cls.appInfo("_int_groupby", _params, area="query" )

        try:

            # ist groups angegeben worden dann verwenden
            if len( _params["groups"].items() ) > 0:
                for name, fields in _params["groups"].items():
                    # das passende Model bestimmen
                    model = cls.access_cls( name )
                    for field in fields:

                        #column = getattr( model, field, None )
                        # und daraus die richtige column holen
                        #column = model.columns.get( field )
                        column = cls._s_column_by_name(field, model) 
                        if not column is None:
                            #
                            if "{}.{}".format(name, field) in _params["labels"]:
                                labels = _params["labels"]["{}.{}".format(name, field)]
                                if type(labels) is list:
                                     for labelname in labels:
                                         group_entities.append( column.label( labelname ) )
                                else:
                                    group_entities.append( column.label( labels ) )
                            else:
                                group_entities.append( column )

            # alle felder aus request verwenden
            for name, fields in _params["fields"].items():
                # das passende Model bestimmen
                model = cls.access_cls( name )
                for field in fields:
                    # und daraus die richtige column
                    column = cls._s_column_by_name(field, model)  
                    if not column is None:
                        column_name = str( column )
                        if column_name in _params["labels"].keys():
                            labels = _params["labels"][column_name]
                            if type(labels) is list:
                                for labelname in labels:
                                    field_entities.append( column.label( labelname ) )
                            else:
                                field_entities.append( column.label( labels ) )
                        else:
                            field_entities.append( column )
            
            # ohne gruppenfelder die in fields angegebenen Verwenden
            if len(group_entities) == 0:
                group_entities = field_entities
            # oder ohne fields die gruppenfelder verwenden
            if len(field_entities) == 0:
                field_entities = group_entities

            # gruppen felder als Gruppierung verwenden
            query = query.group_by( *group_entities )
            
            # bisher alles ok
            ok = True
        except Exception as exc: # pragma: no cover
            cls.appError( "Fehler bei _int_group", str( exc ) )

            #log.exception(exc)
            ok = False

        # die in fields angegebenen Felder als Anzeigefelder verwenden
        query = query.with_entities(
            *field_entities
        )

        return query, group_entities, ok
    
    @classmethod
    def _int_groupby_query(cls, query, params:dict={} ):
        """Führt eine group query aus und gibt das Abfrage Ergebnis zurück.

       
        Parameters
        ----------
        query : obj
            Das bisherige query Object
        params : dict, optional
            The default is::

                {
                    "groups": {},
                    "fields": { "<tablename>":[ <fieldname1...fieldnameX>] },
                    "labels": {"<tablename>.<fieldname1>":"<label1>", ... },
                    "filter": ""
                }

        Returns
        -------
        result : dict
            data
        """
        _params = {
                "groups": {},
                "fields": {},
                "labels": {},
                "filter": ""
        }
        _params.update( params )

        query, group_entities, ok = cls._int_groupby( query, _params )

        if ok == False: # pragma: no cover
            _result = {
                'errors' : [ "Fehler in _int_group" ]
            }
            return _result
        # zusätzlich noch die Anzahl mitgeben
        query = query.add_columns( func.count( cls.id ).label('hasChildren')  )

        # filter berücksichtigen
        if not _params["filter"] == "":
            query = cls._int_filter( query, _params["filter"] )
        
        # full_query = query.statement.compile( compile_kwargs={"literal_binds": True} ) 
        cls.appInfo( "groupsplit", {
            "query": str(query)
        })
        # die query durchführen
        _result = cls._int_query( query )

        return _result

    @classmethod
    def _int_get_empty_record( cls, defaults:dict={} ):
        """Holt einen leeren Datensatz, ggf mit default Werten belegt.

        Eine safrs Klasse hat immer eine id, entweder als Datenbankfeld ober autom. generiert

        Parameters
        ----------
        defaults: dict
            Defaultwerte für die angegebenen Felder

        Result
        ------
        empty_record : dict
            * attributes : {},
            * id : undefined,
            * type : ""

            Alle Spalten von table mit null oder defaults vorbelegt
        """
        empty_record = {
            "attributes" : {},
            "id" : "undefined",
            "type" : cls.__name__
        }

        # alle durchgehen
        for name in cls._s_column_names:
            column = getattr(cls, name, None )
            if column:

                key = column.key
                # nur in attributes ablegen id ist mit undefined vorbelegt
                if not key == "id":
                    if key in defaults:
                        empty_record["attributes"][ name ] = defaults[ key ]
                    else:
                        empty_record["attributes"][ name ] = None # c.server_default
            else:
                 empty_record["attributes"][ name ] = None

        return empty_record


    # -------------------------------------------------------------------------
    @classmethod
    @jsonapi_rpc( http_methods=['GET'] )
    def groupby( cls, **kwargs):
        """.. restdoc::
        description : Gruppiert die Daten und gibt zusätzlich die Anzahl in hasChildren zurück
        summary : mit filter und gruppierung
        pageable : false
        parameters:
            - name : groups
              default :
              description : Gruppierungsfelder mit , getrennt ohne Angabe wird fields verwendet
            - name : filter
              description : RQL Filter
              type: string
            - name : labels
              description : andere Feldnamen zurückgeben
              type: OrderedMap
              default : {}
        ----
        Gruppiert die Daten.

        Parameters
        ----------
        **kwargs : dict
            named arguments from restdoc parameters

        * ohne groups angabe wird fields verwendet::

            /api/<modul>/groupby?fields[<modul>]=<feld1>

        * mit groups::

            /api/<modul>/groupby?fields[<modul>]=<feld1,feld2>&groups=<feld1,feld2>

        * mit groups::

            /api/<modul>/groupby?fields[<modul>]=<feld1,feld2>&groups[<modul>]=<feld1,feld2>

        * mit filter::

            /api/<modul>/groupby?fields[<modul>]=<feld1,feld2>&filter=eq(aktiv,true)

        * mit labels::

            /api/<modul>/groupby?groups=<feld1,feld2>&labels={"dbtests.gruppe": ["lGruppeA", "lGruppeB"]}

        JSON:API Response formatting follows filter -> sort -> paginate


        """
        # die Gruppierung durchführen
        #

        # wenn labels angegeben wurden versuchen sie zu verwenden
        labels = {}
        if "labels" in kwargs :
            labels = kwargs['labels']  or "{}"
            try:
                labels = json.loads( labels )
            except Exception as exc:
                cls.appError( "Fehler bei groupby json.loads lables", str( exc ) )
                labels = {}
                pass

        args = {
            "fields" : request.fields,
            "groups" : request.groups,
            "labels" : labels,
            "filter" : kwargs.get('filter', "")
        }

        _result = cls._int_groupby_query( cls._s_query, args )
        return cls._int_json_response( _result )

    @classmethod
    @jsonapi_rpc( http_methods=['GET'] )
    def groupsplit( cls, **kwargs ):
        """
        description: creates result by splitting group contents by delimiter
        parameters:
            - name : group
              default :
              description : Gruppierungsfeld 
            - name : delimiter
              description : split group field on delimiter. Default is ' '
              type: string
            - name : filter
              description : RQL Filter
              type: string
        ----
                 
        /api/<db>/groupsplit?group=<fieldname>&delimiter=,
       
        WITH split(word, str) AS (
            -- alternatively put your query here
            -- SELECT '', category||',' FROM categories
            -- SELECT '', 'Auto,A,1234444'||','
        	SELECT '', wofuer||',' FROM ersatz
            UNION ALL SELECT
            substr(str, 0, instr(str, ',')),
            substr(str, instr(str, ',')+1)
            FROM split WHERE str!=''
        ) SELECT word, count(*) FROM split WHERE word!='' GROUP BY word 
       
        """
        _result = []
         
        con = cls._get_connection()
        engine = sqlalchemy.create_engine(con)
        Session = scoped_session(sessionmaker(bind=engine))
        db_session = Session()
        
        cls.appInfo( "kwargs", kwargs )
        
        field = kwargs["group"] 
        if not field:
            return cls._int_json_response( { "data" : _result } )
            
        column = getattr(cls, field, None )
        delimiter = kwargs[ 'delimiter' ] or " "
       
        # TODO: sub_query erstellung besser lösen 
        if kwargs[ 'filter' ]:
            sub_query = text("""
                '',{field}||'{delimiter}'
            """.format( **{"field":str(column), "delimiter":delimiter, "table": cls.__table__  } ) ) 
        else:
             # withot filter set table in query
           sub_query = text("""
                '',{field}||'{delimiter}' FROM {table}
            """.format( **{"field": str(column), "delimiter":delimiter, "table": cls.__table__  } ) ) 
        
        if sqlalchemy.__version__ == '1.3.23':
             query = cls.query.with_entities( str(sub_query ) ) # py37
        else:
            query = cls.query.with_entities( text(str(sub_query )) ) # py38
        
        if kwargs[ 'filter' ]:
            query = cls._int_filter(query, kwargs[ 'filter' ] )
        
        full_sub_query = query.statement.compile( compile_kwargs={"literal_binds": True} ) 
        
        
        # https://stackoverflow.com/questions/31620469/sqlalchemy-select-with-clause-statement-pgsql
        statement = text("""
            WITH split(word, str) AS (
            	{qs}
                UNION ALL SELECT
                    substr(str, 0, instr(str, '{delimiter}')),
                    substr(str, instr(str, '{delimiter}')+1)
                FROM split WHERE str!=''
            ) 
            SELECT word as {field}, count(*) AS hasChildren FROM split WHERE word!='' GROUP BY word                          
        """.format( **{ "qs":str(full_sub_query), "field": field, "delimiter":delimiter } ) )
            
        #print( "statement", str(statement) )
        
        info = {
            "sub_query" : str(full_sub_query),
            "query" : str(statement)
        }
        query_result = []
        try:
            query_result = db_session.execute( statement )
            cls.appInfo( "groupsplit", info )
        except Exception as exc:       
            info[ {"Exception": exc } ]
            cls.appError( "groupsplit", info )
        
        
        for row in query_result:
            #print( dict(row) )
            _result.append( {
                "attributes":  dict(row), #row._asdict(),
                "id": None,
                "type": cls.__tablename__
            })
        
        return cls._int_json_response( { "data" : _result } )
        
    @classmethod
    @jsonapi_rpc( http_methods=['GET'] )
    def undefined( cls, **kwargs):
        """.. restdoc::
        summary : Einen leeren Datensatz zurückgeben ggf. mit parametern füllen
        pageable: False
        filterable: False
        parameters:
            - name : _ispcp
              default : {}
              description : zusätzliche parameter
        ---
        
        Einen leeren Datensatz zurückgeben ggf. mit parametern füllen.

        Parameters
        ----------
        **kwargs : dict
            named arguments from restdoc parameters
        """
        _result = {
            "data" : cls._int_get_empty_record(  )
        }
        return cls._int_json_response( _result )

# ----------- ispSAFRS mit db.Model
class ispSAFRSModel( ispSAFRS, db.Model ):
    __abstract__ = True
    pass


# ----------- ispSAFRS dummy klasse ohne autom. SQLAlchemy model
class ispSAFRSDummy( ispSAFRS ):
    """hier werden safrs und sqlalchemy Funktionen überschrieben.

    So kann eine einfache Klasse ohne autom. Datenbankanbindung erstellt werden.

    Api Erstellung in webapp über expose_object()

    * _s_type - cls.__name__ wird zu <name>_API
    * _s_collection_name - tags entweder ( __tablename__ oder cls.__name__)

    ruft auf expose_methods(url_prefix, tags=tags)

    erstellt über parse_object_doc() die Dokumentation

    * aufruf mit id - api_get::

         def api_get(cls, **kwargs):
             /class/{objectId}

    * aufruf ohne id - api_list::

         def api_list(cls, **kwargs):
             /class
    """

    # unterbindet die Möglichkeit Flask Admin zu verwenden
    no_flask_admin = True

    # keine automatischen get|post|put|delete usw. erlauben
    http_methods = ["get"]

    # id of record
    id = None

    #
    # Following methods are used to create the swagger2 API documentation
    #
    @classmethod
    def _s_sample_id(cls):
        """
        :return: a sample id for the API documentation
        """
        return "0" # jsonapi ids must always be strings

    @classproperty
    def _s_object_id(cls):
        """
        :return: the Flask url parameter name of the object, e.g. UserId
        :rtype: string
        """
        # pylint: disable=no-member
        return cls.__name__ + 'Id' # get_config("OBJECT_ID_SUFFIX")

    @classproperty
    def _s_column_names(cls):
        """
            :return: list of column names
        """
        return []

    @classmethod
    def _s_sample_dict(cls):
        """
        :return: a sample to be used as an example "attributes" payload in the swagger example
        """
        return ""

    @hybrid_property
    def _s_relationships(self):
        """Dummy function for swagger doc.

        Returns
        -------
        list
            the relationships used for jsonapi (de/)serialization
        """
        return {} # []

    @hybrid_property
    def _s_jsonapi_attrs(self):
        """Dummy function for swagger doc.

        Returns
        -------
        dict
            dictionary of exposed attribute names and values
        """
        return {}

    @classproperty
    def _s_columns(cls):
        """Dummy function for swagger doc.

        Returns
        -------
        list
            list of columns that are exposed by the api
        """
        return []

    @classmethod
    def _s_get_jsonapi_rpc_methods(cls):
        """Dummy function for swagger doc.

        Returns
        -------
        list
            a list of jsonapi_rpc methods for this class
        """
        return []

    @classproperty
    def _s_query(cls):
        """Dummy function for swagger doc.

        Returns
        -------
        obj
            sql query object
        """
        class dummyQuery(object):
            def __init__(cls):
                cls._index = -1
            def with_entities(cls):
                return cls
            def group_by(cls):
                return cls
            def add_columns(cls, cols=None ):
                return cls
            def __iter__(self):
                return self
            def __next__(self):
                raise StopIteration


        dobj = dummyQuery(  )
        return dobj

    @hybrid_property
    def _s_url(self, url_prefix=""):
        """Dummy function for swagger doc.

        Parameters
        ----------
        url_prefix : str, optional
            The default is "".

        Returns
        -------
        str
            endpoint url of this instance.
        """
        return ""

    @classproperty
    def class_(cls):
        """Get class object.

        Returns
        -------
        cls
            class object.

        """
        return cls


class system( ispSAFRSDummy ):
    """.. restdoc::

    description: Systeminformation abrufen

    ----
    Systeminformation abrufen.

    """
    http_methods = ["get"]

    @classmethod
    def _extendedSystemCheck(cls):
        """Stub Function for api_list (Systeminformationen)

        Returns
        -------
        dict, string

        """
        return {}, ""

    @jsonapi_rpc( http_methods=['GET'] )
    def api_get(cls, **kwargs):
        """.. restdoc::

        summary : Systeminformationen zurückgeben
        description: Einige Systeminformationen zurückgeben
        parameters:
            - name : info
              in : query
              required : false
              default : kwargs
              description : Art der Informationen [ kwargs ]
            - name : format
              in : query
              required : false
              default : html
              description : Format der Ausgabe [ json, html ]

        ----
        Systeminformationen zurückgeben.

        Parameters
        ----------
        **kwargs : dict
            named arguments from restdoc parameters

        """
        cls.appInfo("kwargs", kwargs )

        return cls._int_json_response( {"data" : {"kwargs": kwargs } } )

    @jsonapi_rpc( http_methods=['GET'] )
    def api_list(cls, **kwargs):
        """.. restdoc::

        summary : Systeminformationen zurückgeben
        description: Einige Systeminformationen zurückgeben
        parameters:
            - name : format
              in : query
              required : false
              default : json
              description : Format der Ausgabe [ json, html ]
            - name : show_latest
              in : query
              type: boolean
              required : false
              default : false
              description : die höchste Version jedes Moduls bestimmen
        ----

        Parameters
        ----------
        **kwargs : dict
            named arguments from restdoc parameters

        Returns
        -------
        None.

        """

        cls.appInfo("kwargs", kwargs )

        import sys

        sysinfo = {
            "config_webserver" : cls._config.server.webserver.toDict(),
            "kwargs" : kwargs,
            "python" : sys.version,
            "modules" : {}
        }

        # add extended informations
        extended, extended_html = cls._extendedSystemCheck()
        sysinfo["extended"] = extended

        import logging
        level = {
            50:"CRITICAL",
            40:"ERROR",
            30:"WARNING",
            20:"INFO",
            10:"DEBUG",
            0 :"NOTSET"
        }
        # root logger
        logger = logging.getLogger(  )
        sysinfo["logger.level"] = {}
        if logger.level in level:
            sysinfo["logger.level"]["ROOT"] = "{} - {}".format(logger.level, level[logger.level] )
        else: # pragma: no cover
            sysinfo["logger.level"]["ROOT"] = level

        # mqtt logger
        logger = logging.getLogger( "MQTT" )
        if logger.level in level:
            sysinfo["logger.level"]["MQTT"] = "{} - {}".format(logger.level, level[logger.level] )
        else: # pragma: no cover
            sysinfo["logger.level"]["MQTT"] = level

        import psutil, datetime
        p = psutil.Process()
        sysinfo["process"] = p.as_dict(attrs=[
            'pid', 'exe', 'username', 'memory_percent', 'num_threads', 'cwd', 'cmdline'
        ])
        sysinfo["memory"] = "{} MB".format( round(psutil.virtual_memory().total / (1024*1024) ) )
        sysinfo["process"]["memory"] = '{} MB'.format(int(p.memory_info().vms /(1024*1024) ) )
        sysinfo["process"]["create_time"] = datetime.datetime.fromtimestamp(p.create_time()).strftime("%Y-%m-%d %H:%M:%S")


        # testet die vorhandenen fonts auf: Material Design Icons
        #
        sysinfo["fonts"] = {
            "Material Design Icons" : "not checked"
        }
        sysinfo["fonts_msg"] = ""
        import subprocess
        from os import path as osp
        if osp.isfile( "/usr/bin/fc-list" ):

            cmd = '/usr/bin/fc-list --format="%{family[0]}\n" | sort | uniq'
            #args = shlex.split(cmd)
            output = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE ).communicate()[0]
            check_fonts = [
                "Material Design Icons",
                "DejaVu Serif"
            ]
            has_mdi = False

            for fontname in check_fonts:
                msg = ""
                info = ""
                if str(output).find( fontname ) > -1:
                    sysinfo["fonts"][fontname] = "OK";
                    msg = "vorhanden"
                    bage = "badge-success"
                    if fontname == "Material Design Icons":
                        has_mdi = True
                   # sysinfo["fonts_msg"] += '<div class="badge badge-pill badge-info mr-1">vorhanden</div><br/>'
                else: # pragma: no cover
                    sysinfo["fonts"][fontname] = "MISSING";
                    msg = "fehlt"
                    bage = "badge-danger"
                    info = "Dieser Font muss im System installiert werden."
                    #sysinfo["fonts_msg"] += '<div class="badge badge-pill {} mr-1">fehlt</div><br/>';

                sysinfo["fonts_msg"] += '<div class="badge badge-pill {} mr-1">{} - {}</div>{}<br/>'.format(bage, fontname, msg, info)
            if has_mdi:
                sysinfo["fonts_msg"] += '<i class="mdi mdi-check-outline green-text white resultIcon"></i>'
        else:
             sysinfo["fonts_msg"] += '<span class="orange-text">Fonts not checked</span>'

        # module bestimmen
        import sys
        import pkg_resources

        cmnd = [sys.executable, '-m', 'pip', 'list', '--format=json', '--disable-pip-version-check']
        columns = ['name', 'version', 'license']

        if  kwargs["show_latest"] == True: # pragma: no cover
            cmnd.append( '--outdated' )
            columns = ['name', 'version', 'latest_version', 'license']

        reqs = subprocess.check_output( cmnd )
        pkgs = json.loads( reqs )

        # add pkgs license
        for pkg in pkgs:
            if pkg["name"][0] != "-":
                modul = pkg
                pkg['license'] = "missing license"

                if pkg["name"] in pkg_resources.working_set.by_key:

                    _pkg = pkg_resources.working_set.by_key[ pkg["name"] ]

                    metadata_lines = None
                    try:
                        metadata_lines = _pkg.get_metadata_lines('METADATA')
                    except:
                        pass
                    if not metadata_lines:
                        try:
                            metadata_lines = _pkg.get_metadata_lines('PKG-INFO')
                        except:
                            metadata_lines = []

                    for line in metadata_lines:
                        if line.startswith('License:'):
                            modul["license"] = line[9:]
                            break
                sysinfo["modules"][ pkg["name"] ] = modul

        # Art der Ausgabe
        _format = "html"
        if 'format' in kwargs:
            _format = kwargs[ 'format' ]

        if _format == "json":
            return cls._int_json_response( {"data" : {"sysinfo": sysinfo } } )

        import pandas as pd
        df = pd.DataFrame( sysinfo["modules"].values(), columns=columns )

        style = '''
            .sysinfo h4, .sysinfo h5{
                color: #fff;
                padding: .25rem;
                background-color: #6c757d;
                margin-top: 0px;
            }
            .sysinfo table{
                margin-bottom: 5px;
                border-collapse: collapse;
            }
            .sysinfo table, .sysinfo table th, .sysinfo table td{
                border: 1px solid silver;
            }
            .sysinfo tr:nth-child(even) {
        		background-color: #f2f2f2;
        	}
            .sysinfo th.level0 {
            	min-width: 50px;
        	}
            .sysinfo pre{
                background-color: #f2f2f2;
            }
            .sysinfo missing {

            }
        '''
        html = '''
        <style>{}</style>
        <div class="sysinfo">
        <h4>python: {}</h4>
        <h5>Memory: {}</h5>
        {}
        <br>
        <h5 class="m-0 p-1 text-white bg-secondary">process</h5>
        <pre >{}</pre>
        <h5 class="m-0 p-1 text-white bg-secondary">logger.level</h5>
        <pre >{}</pre>
        <h5 class="m-0 p-1 text-white bg-secondary">System-Fonts</h5>
        {}
        <h5 class="m-0 p-1 text-white bg-secondary">Module</h5>
        {}
        </div>
        '''.format(
            style,
            sysinfo["python"],
            sysinfo["memory"],
            extended_html,
            json.dumps( sysinfo["process"], indent=4),
            json.dumps( sysinfo["logger.level"], indent=4),
            sysinfo["fonts_msg"],
            df.style.render()
        )

        return Response( html , mimetype='text/html')


    @classmethod
    @jsonapi_rpc( http_methods=['GET'] )
    def test( cls, **kwargs ):
        """.. restdoc::

        description: Einfacher test von api Funktionen und Parametern
        parameters:
            - name : _ispcp
              in : query
              default : {}
              description : zusätzliche parameter
              type: object
            - name : zahl
              in : query
              required : true
              description : Eine Zahl
              type: number
            - name : bool
              in : query
              required : false
              default : false
              description : Eine boolean Wert
              type: boolean
            - name : text
              in : query
              required : false
              default : typenlos
              description : Eine typenloser Wert mit default

        ----
        Test von api Funktionen und Parametern

        Parameters
        ----------
        **kwargs : dict
            named arguments from restdoc parameters
        """
        cls.appInfo("kwargs", kwargs )
        _result = kwargs
        return cls._int_json_response( { "data": _result } )

