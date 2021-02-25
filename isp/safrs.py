# -*- coding: utf-8 -*-

"""
safrs
=====

swagger yaml definition
-----------------------

Die Definition steht am Anfang des docstring und beginnt für sphinx mit ``.. restdoc::``

Sie kann mit ``----`` abgeschlossen werden, um weitere Dokumentation für sphinx anzuschließen 

Beispiel::
    
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

Hilfen und snippets::

    from flask import current_app
    print( current_app.config )
 
    import safrs
    print( safrs.SAFRS.config )      
    
Beispiele::
    
    /api/<modul>/?fields[<modul>]=<feld1,feld2>&_ispcp={"Test":"Hallo"}&filter=eq(aktiv,true),in(<modul>,(Rapp,SA43))
    /api/<modul>/groupby?fields[<modul>]=<feld1,feld2>&groups=Geraet&filter=eq(aktiv,true)
    
    /api/<modul>/groupby?fields[<modul>]=<feld1,feld2>&groups=Geraet&filter=eq(aktiv,true)
    /api/<modul>/groupby?fields[<modul>]=<feld1,feld2>&groups[Ersatz]=Geraet&filter=eq(aktiv,true)
    
"""

__author__ = "R. Bauer"
__copyright__ = "MedPhyDO - Machbarkeitsstudien des Instituts für Medizinische Strahlenphysik und Strahlenschutz am Klinikum Dortmund im Rahmen von Bachelor und Masterarbeiten an der TU-Dortmund / FH-Dortmund"
__credits__ = ["R. Bauer", "K.Loot"]
__license__ = "MIT"
__version__ = "0.1.0"
__status__ = "Prototype"

import json
import re

from functools import wraps

from flask_sqlalchemy import SQLAlchemy
from flask import Response, request, current_app

import sqlalchemy
from sqlalchemy import func, text # , case, or_, inspect

from safrs import SAFRSBase  # db Mixin
from safrs.config import get_request_param
from safrs.errors import ValidationError, GenericError, NotFoundError 
import werkzeug


from safrs import SAFRSFormattedResponse, jsonapi_format_response, log #, paginate, SAFRSResponse
from safrs import jsonapi_rpc # rpc decorator

from flask_restful_swagger_2.swagger import get_parser
from flask import jsonify

from safrs.util import classproperty
from sqlalchemy.ext.hybrid import hybrid_property

db = SQLAlchemy()
    
from sqlalchemy.orm import Query as BaseQuery
from rqlalchemy import RQLQueryMixIn
from pyrql import RQLSyntaxError
from pyrql import parse
import sqlalchemy.types as types

from datetime import datetime

# ------------ Typen Umwandlungen

def iso2date( value:str=None, toDate:bool=False ):
    """Wandelt über fromisoformat oder strptime einen String in ein ``datetime`` oder ``date`` Object um.
    
    Versucht zuerst eine Umwandlung über fromisoformat
    Bei Fehlern wird versucht es mit strptime umzuwandeln umzuwandeln
    
    Beispiele für Value::
        2018-04-15 - datetime.datetime(2018, 4, 15, 0, 0)
        2018-04-15 14:36 - datetime.datetime(2018, 4, 15, 14, 36)
        2018-04-15 14:36:25 - datetime.datetime(2018, 4, 15, 14, 36, 25)
        
        20180415 - datetime.datetime(2018, 4, 15, 0, 0)
        20180415 14:36:25 - datetime.datetime(2018, 4, 15, 14, 36, 25)
        20180415 14:36 - datetime.datetime(2018, 4, 15, 14, 36)
        20180415 14 - datetime.datetime(2018, 4, 15)
        
        mit toDate=True
        
        2018-04-15 14:36:25 - datetime.date(2018, 4, 15)
        20180415 14:36:25 - datetime.date(2018, 4, 15)
        
    Parameters
    ----------
    value : str
        String mit Datumsangaben.
    toDate : bool
        Gibt bei true ein date Object statt datetime zurück. Default is False.    
    
    Returns
    -------
    datetime|None
        Umgewandelter ISO String oder None

    """
    result = None
    if value and isinstance(value, str):
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
        if result and toDate:
            result = result.date()
            
    return result
     

# ------------ Typen Erweiterungen

class isoDateType( types.TypeDecorator ):
    """TypeDecorator für ISO-8601 Datum.
    
    Verwendet iso2date() für die Umwandlung.
    
    """
    
    impl = types.Date          
    def process_bind_param(self, value, dialect):		
        return iso2date( value, True)


class isoDateTimeType( types.TypeDecorator ):
    """TypeDecorator für ISO-8601 Datum Zeit.
    
    Verwendet iso2date() für die Umwandlung.
    
    """
    
    impl = types.DateTime
    def process_bind_param(self, value, dialect):		
        return iso2date( value, False)
  
    
# Filter abfrage für rql
class RQLQuery(BaseQuery, RQLQueryMixIn):
    _rql_default_limit = 10
    _rql_max_limit = 100
    
    def rql_parse(self, rql, limit=None):
        """Wie rql, es wird aber nur ausgewertet und nicht die query geändert.

        Parameters
        ----------
        rql : string
            rql query string.
        limit : int, optional
            Limit Angabe, wird hier aber nicht verwendet. The default is None.

        Raises
        ------
        NotImplementedError
            
        Returns
        -------
        _rql_where_clause

        """
        if len(self._entities) > 1: # pragma: no cover
            raise NotImplementedError("Query must have a single entity")
        
        # rql = 'eq(link_sid,22) and eq(link_art,haus)'
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
    """Api Aufrufe vorbereiten und durchführen.
    
    Im decorator wird wrapped_fn() aufgerufen um die Anfrage zu verarbeiten
    
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
        """Funktion zum verarbeiten eine API Anfrage.
        
        Arten von fn - safrs/jsonapi.py
        
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
        
            das Vorhandensein einer _s_object_id unterscheidet zwischen dem holen eines Datensatzes oder einer Liste
            id = kwargs.get( fn.SAFRSObject._s_object_id , None)
                 
        Parameters
        ----------
        *args : tuple 
            mit einem object
            .. code::
            
                /api/gqadb/?zahl=12 - ( safrs._api.gqadb_API, ) - {}
                /api/gqadb/2020?zahl=12 - ( safrs._api.gqadb_API, ) - {'gqadbId': '2020'}
                /api/gqadb/test?zahl=12 - ( safrs._api.method_gqadb_test, ) - {}
                /api/gqa?zahl=12 -  ( safrs._api.gqa_API, ) - {}
                /api/gqa/2020?zahl=12 - ( safrs._api.gqa_API, ) - {'gqaId': '2020'}
                /api/gqa/test?zahl=12 - ( safrs._api.gqa_API, ) - {'gqaId': 'test'}
            
        **kwargs : dict
            beliebige Parameter.

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
                  
                #print( "wrapped_fn", swagger_path, safrs_obj._s_object_id, kwargs )
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
                        # objectId merken
                        objectId = kwargs[ safrs_obj._s_object_id ]
                        swagger_path = "/{}/{}/".format( name, "{" + safrs_obj._s_object_id + "}" )
                    elif variante == "c":
                        swagger_path = "/{}/{}".format(name, func_name )
                else:
                    # es gibt keine passende Funktion also Fehler anzeigen
                    status_code = 400
                    message = "Funktion nicht gefunden"
                    
                    safrs_obj.appError( 
                        "{}".format( message ),
                        str( status_code )
                    )
                    result = jsonify( {} ) 
                    result.status_code = status_code
                    
                    return result

           
            elif q[0] == "SAFRSJSONRPCAPI":
                
                # dieser Bereich wird in db bei groupby, undefined oder funktionen aufgerufen 
                doArgParse = True
                # den request endpoint bestimmen - wird benötigt um Swagger parameter zu prüfen
                # der erste teil ist immer api der letzte Teil die aufzurufende Funktion
                ep_list = request.endpoint.split(".")
                func_name = ep_list[-1]
                # bei diesem 
                swagger_path = "/{}/{}".format(name, ep_list[-1]) 
                                
            else:
                
                # einfach durchlaufen ohne die Argumente zu prüfen
                # SAFRSRestRelationshipAPI - get - dbtestsrelId - {"dbtestsId": "2"}
                doArgParse = False
            
            # nur in swagger abgelegte paramter verwenden und ggf umwandeln
            # in safrs methoden selbst wird args = dict(request.args) verwendet
            # _int_parse_args entfernt _s_object_id
            if doArgParse: 
                kwargs = safrs_obj._int_parse_args( kwargs, method, swagger_path )
                #  gemerkte objectId wieder einfügen
                if objectId:
                    kwargs[ safrs_obj._s_object_id ] = objectId       

        request.groups = {}
        # Parse the jsonapi groups and groups[] args
        for arg, val in request.args.items():
                
            # https://jsonapi.org/format/#fetching-sparse-fieldsets
            groups_attr = re.search(r"groups\[(\w+)\]", arg)
            
            if groups_attr:
                group_type = groups_attr.group(1)
                request.groups[group_type] = val.split(",")
            elif arg == "groups":
                # groups ohne andere tabelle verwendet die aktuelle tabelle
                request.groups[ safrs_obj.__name__ ] = val.split(",")
       
        # funktion in der Klasse ausführen sonst fn selbst
        if func_name:
            # gewünschte Funktion in fn.SAFRSObject aufrufen
            meth = fn.SAFRSObject
            meth.appInfo( "safrs", "Funktion: {}.{}.{}()".format( meth.__module__, meth.__name__, func_name ) )
            
            if hasattr(meth, func_name):
                if func_name[:4] == "api_":
                    # api_ Funktionen benötigen die Klasse selbst als ersten parameter
                    result = getattr( meth, func_name )( meth, **kwargs )
                else:
                    result = getattr( meth, func_name )( **kwargs )
            else: # pragma: no cover
                # kann eigentlich nicht passieren da oberhalb gestetet wird
                meth.appError( "ispSAFRSDummy", "Fehlende Funktion: {}.{}.{}()".format( meth.__module__, meth.__name__, func_name ) )
                result = meth._int_json_response( {} ) 

            # abfangen das result auch etwas anderes als ein dict sein kann (z.b. html, pdf ...)
            if not type( result ) in [dict, list, SAFRSFormattedResponse]:     
                return result
            
            try:
                result = jsonify( result )
            except Exception as exc:  # pragma: no cover
                status_code = getattr(exc, "status_code", 500)
                message = getattr(exc, "message", "unbekannter Fehler") 
                safrs_obj.appError( 
                        "{} - {}".format( func_name, message ),
                        str( status_code )
                )
                result = jsonify( {} )
                
        else:    
            #
            # die ursprüngliche Funktion aufrufen
            #
            status_code = 200
            try:
                result = fn(*args, **kwargs) 
            except (ValidationError, GenericError, NotFoundError) as exc: # pragma: no cover
                status_code = getattr(exc, "status_code", 500)
                message = getattr(exc, "message", "")
            except werkzeug.exceptions.NotFound:
                status_code = 404
                message = "Not Found"   
            except Exception as exc:  # pragma: no cover
                status_code = getattr(exc, "status_code", 500)
                message = getattr(exc, "message", "unbekannter Fehler") 
                
            # gab es einen Fehler dann in appError setzen
            if not status_code == 200:
                safrs_obj.appError( 
                    "{} - {}".format(method, message ),
                    str( status_code )
                )
                result = jsonify( {} ) 
                result.status_code = status_code
                
                    
        #----------------------------------------------------------------------
        # Auswertung der Ergebnisse
        #

        # result holen und zusätzliche informationen einfügen 
        _data = { }

        _data = result.get_json()
        
        # _data muss immer ein dict sein (dict, list, SAFRSFormattedResponse)
        
        if not type( _data ) == dict:
            # ist _data list dann als data verwenden, sonst in _wrongdatatype einfügen
            if type( _data ) == list:
                _data = {"data": _data}
             
        # data bereich in data muss immer list sein
        if not 'data' in _data or _data['data'] is None:
            _data['data'] = []
            
        if not 'meta' in _data:
            # ohne meta mind. count mitgeben
            _data['meta'] = {
                "count": len( _data.get("data", [] ) )
            }
         
        if not 'count' in _data['meta'] or _data['meta']['count'] is None:
            _data['meta']['count'] = 0
            
        # offset für die Bestimmung des letzten im Grid
        try:
            _data['meta']["offset"] = int( get_request_param("page_offset") )
        except ValueError: # pragma: no cover
            _data['meta']["offset"] = 0
            #raise ValidationError("Pagination Value Error")
        
        # die Angaben aus _resultUpdate (App-Error, App-Info,...) des Datenbankobjects hinzufügen  
        #
        _data.update( safrs_obj._resultUpdate )
        
        try:
            result.set_data( json.dumps( _data ) ) 
        except : # pragma: no cover
            result.status_code = 500
            log.error("wrapped_fun data error")
        
        # http statuscode auswerten
        if "status_code" in result.json:
            result.status_code = result.json["status_code"]
            

        return result

    return wrapped_fn        
    

# ----------- ispSAFRS ohne db.Model 
class ispSAFRS(SAFRSBase, RQLQueryMixIn):
    
    __abstract__ = True
        
    custom_decorators = [ispSAFRS_decorator]
    
    _resultUpdate = {
        "App-Info": [],
        "App-Error": [],
        "App-Dialog": []
    }

    exclude_attrs = []  # list of attribute names that should not be serialized
    exclude_rels = []  # list of relationship names that should not be serialized

    _config: None
    _configOverlay: {}
        
    @classmethod
    def access_cls(cls, key:str=""):
        """Versucht das mit key angegebene Model zu bestimmen.

        Parameters
        ----------
        key : str
            Bezeichnung des gesuchten model.

        Returns
        -------
        None|model
            Das gefundene model oder None.

        """       
        if hasattr(cls, "_decl_class_registry") and key in cls._decl_class_registry:
            return cls._decl_class_registry[key]
        elif hasattr(cls, "metadata") and key in cls.metadata.tables: # pragma: no cover
            return cls.metadata.tables[key]
        else:
            if key in sqlalchemy.__dict__:
                return sqlalchemy.__dict__[key]
        return None
    
    @classproperty
    def _s_column_names(cls):
        """
            :return: list of column names
        """
        return [c.name for c in cls._s_columns]    
    
    @classmethod
    def _int_init( cls ):
        """Initialisierung vor jedem Aufruf.
        
        Setzt _resultUpdate vor jedem Aufruf::
            
            {
                "App-Error" : [],
                "App-Info" : [],
                "App-Dialog" : [],
                "errors" : []
            }
            
        Stellt _config und _configOverlay des Flask Servers bereit
        
        Diese Funktion wird von ispSAFRS_decorator aufgerufen

        Returns
        -------
        None.

        """
        cls._resultUpdate = {
            "App-Error" : [],
            "App-Info" : [],
            "App-Dialog" : [],
            "errors" : []
        }
        cls._config = current_app._config
        cls._configOverlay = current_app._configOverlay
        # die Argumente über swagger bestimmen 
        #kwargs = cls._int_parse_args( kwargs )  
        
    @classmethod   
    def _int_parse_args(cls, kwargs:dict={}, method=None, swagger_path=None ):
        """Parsed die request parameter mit den Angaben aus cls._swagger_paths.
 
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
            Alle request Parameter. The default is {}.
        method : str, optional
            The request method. (For example ``'GET'`` or ``'POST'``). The default is None.
        swagger_path : str, optional
            Der zum request passende Pfad der swagger Beschreibung. The default is None.

        Returns
        -------
        has_args : dict
            Die überprüften Parameter.

       RequestParser kann auch so bestimmt werden::
            
            from flask_restplus import RequestParser
            parser = RequestParser()
            
        """
        if not method:
            method=request.method.lower()
         
        paths = cls._api.get_swagger_doc().get("paths", {}) 
        
        # parameter für swagger_path holen (cls._swagger_paths)
        parameters = paths.get(swagger_path, {}).get( method, {} ).get("parameters", {} )
                
        parser = get_parser( parameters )
        # alle fehler sammeln (TypeError in value)
        parser.bundle_errors = True
        # request parsen
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
    def _int_add_meta( cls, meta:str="App-Info", message:str="", info:str="", status_code:int=None ):  
        """App-Info, App-Error, App-Dialog, errors Informationen anfügen.
        
        Parameters
        ----------
        meta: str
            der Bereich in dem angefügt wird
        message : str, optional
            Message Bereich. The default is "".
        info : str, optional
            Info Bereich. The default is "".
        status_code: int, optional
            Wenn gesetzt der http statuscode
            
        Returns
        -------
        None.

        """       
        # Versuchen in json umzuwandeln 
        try:
            json_data = json.loads( info )
            if type(json_data) is dict:
                info = json_data
        except:  # includes simplejson.decoder.JSONDecodeError
            
            pass
    
        if meta in ["App-Info", "App-Error"]:  
            cls._resultUpdate[ meta ].append( { 'message':message, 'info': info } )
        elif meta in ["App-Dialog"]: 
            cls._resultUpdate[ meta ].append( info )
        if status_code:
            cls._resultUpdate[ "status_code" ] = status_code
                        
    @classmethod        
    def appInfo(cls, message:str="", info:str="", status_code:int=None):
        """App-Info Informationen anfügen.
        
        Parameters
        ----------
        message : str, optional
            Message Bereich. The default is "".
        info : str, optional
            Info Bereich. The default is "".
        status_code: int, optional
            Wenn gesetzt der http statuscode
            
        Returns
        -------
        None.

        """    
        cls._int_add_meta( "App-Info", message, info, status_code ) 
     
    @classmethod
    def appError(cls, message:str="", info:str="", status_code:int=None):
        """App-Error Informationen anfügen.
        
        diese werden z.b. bei einer Form im status icon angezeigt
         
        Parameters
        ----------
        message : str, optional
            Message Bereich. The default is "".
        info : str, optional
            Info Bereich. The default is "".
        status_code: int, optional
            Wenn gesetzt der http statuscode
            
        Returns
        -------
        None.

        """    
        cls._int_add_meta( "App-Error", message, info, status_code ) 
        
    @classmethod
    def appDialog(cls, message:str="", info:dict={}):
        """App-Dialog Informationen für den client anfügen.
        
        Diese Informationen führen zu einer Dialog Anzeige im client::
        
            appDialog("Fehler beim anlegen", { "content" : message, "dimensions" : [ 500, 200] })
            
            Übergabe für den client Dialog
            {
                "title" => "Fehler beim anlegen",
    			"content" : message,
    			"dimensions" : [ 500, 200]
    		}
        
        Parameters
        ----------
        message : str, optional
            title Bereich. The default is "".
        info : str, optional
            Info Bereich. The default is "".
            ist title hier nicht angegeben wird message verwendet
            
        Returns
        -------
        None.

        """    
        if not "title" in info:
            info[ "title" ] = message
            
        cls._int_add_meta( "App-Dialog", '', info ) 
                
    @classmethod       
    def _int_query( cls, query=None, **kwargs):
        """Eine query ohne paginate durchführen.

        Parameters
        ----------
        query : obj
            Das bisherige query Object
        **kwargs : dict
            Beliebige weitere Argumente.

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
        data = []
        if query:
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
                        "type": cls.__name__
                    })
                else:
                    data.append( row )

        # Anzahl aus query
        count = len( data )
        result = {
             "data" : data,
             "count" : count,
             "meta": {},
             "errors": [],
        }
        cls.appInfo("sql-lastquery", str( query ) )
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
        # RQLQuery bereitstellen die eigene Klasse muss mit _set_entities angegeben werden
        rql = RQLQuery( cls )
        rql._set_entities( cls )
        
        # rql_filter auswerten
        try:
            rql.rql_parse( qs )
        except Exception as exc:
            #log.error("rql_filter {}".format( exc ) )
            cls.appError("_int_filter",  str( exc ) )
            query = query.filter( text("1=2") ) 
            return query
                
        # die Bedingung an die query anfügen
        if rql._rql_where_clause is not None:
            query = query.filter( rql._rql_where_clause )    
                                
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
        cls.appInfo("_int_groupby", _params )
        
        try:
            
            # ist groups angegeben worden dann verwenden
            if len( _params["groups"].items() ) > 0:
                for name, fields in _params["groups"].items():
                    for field in fields:
                        
                        # das passende Model bestimmen
                        model = cls.access_cls( name )
                        
                        # und daraus mit getattr die richtige column holen
                        column = getattr( model, field, None )
                        if column:
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
                for field in fields:
                    # das passende Model bestimmen
                    model = cls.access_cls( name )
                    # und daraus mit getattr die richtige column  
                    column = getattr( model, field, None )
                    if column:
                        if "{}.{}".format(name, field) in _params["labels"]:        
                            labels = _params["labels"]["{}.{}".format(name, field)]
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
            
            log.exception(exc)
            ok = False
        
        # die in fields angegebenen Felder als Anzeigefelder verwenden
        query = query.with_entities( 
            *field_entities
        )
        
        return query, group_entities, ok

    @classmethod
    def _int_groupby_query(cls, query, params:dict={} ):            
        """Führt eine group query aus und gibt das Abfrage Ergebnis zurück.
        
        Wird delimiter angegeben, wird nur das erste group Feld mit delimiter gesplittet zurückgegeben
        
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
                    "filter": "",
                    "delimiter": ""
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
                "filter": "",
                "delimiter": ""
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
            
        # die query durchführen
        _result = cls._int_query( query )
        
        # wenn angegeben nach delimter splitten
        if _params["delimiter"] and not _params["delimiter"] == "":
            words = {}
            if len(group_entities) > 0:
                # das erste feld bestimmen
                s_field = str( group_entities[0] )
                field = s_field.split(".")
                for item in _result["data"]:             
                    if field[0] == item["type"] and field[1] in item["attributes"]:
                        # den feldinhalt spliten und anfügen
                        val = item["attributes"][ field[1] ]
                        if type(val) is str:
                            p = val.split( _params[ "delimiter" ])
                            for s in p:
                                words[ s.strip() ] = s.strip()

            data = [] 
            for d in sorted( words.keys() ):
                if not d == None and not d=="" and not d=="None":
                    data.append( { "attributes":{ field[1]:d } } )
                            
            _result["data"] = data
            _result["count"] = len( data )

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
            key = column.key
            # nur in attributes ablegen id ist mit undefined vorbelegt
            if not key == "id":                
                if key in defaults:
                    empty_record["attributes"][ name ] = defaults[ key ]
                else:
                    empty_record["attributes"][ name ] = None # c.server_default
        return empty_record    
    
    
    # -------------------------------------------------------------------------
    @classmethod
    @jsonapi_rpc( http_methods=['GET'] )
    def groupby( cls, **kwargs):
        """.. restdoc::
        description : Gruppiert die Daten und gibt zusätzlichdie Anzahl in hasChildren zurück
        summary : mit filter und gruppierung
        pageable : false
        parameters:
            - name : groups
              default : 
              description : Gruppierungsfelder mit , getrennt ohne Angabe wird fields verwendet
            - name : delimiter
              description : den Feldinhalt des ersten Feld (fields|group) zusätzlich mit delimiter trennen
              type: string
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
        
        * mit groups und delimiter::
            
            /api/<modul>/groupby?fields[<modul>]=<feld1,feld2>&groups[<modul>]=<feld1,feld2>
        
        * mit filter::
            
            /api/<modul>/groupby?fields[<modul>]=<feld1,feld2>&filter=eq(aktiv,true)
        
        * mit labels::
            
            /api/<modul>/groupby?groups=<feld1,feld2>&labels=
        
        JSON:API Response formatting follows filter -> sort -> paginate
        
        
        """
        # die Gruppierung durchführen
        # 
        
        # wenn labels angegeben wurden versuchen sie zu verwenden
        labels = {}
        if "labels" in kwargs:  
            labels = kwargs.get('labels')
        
            try:
                labels = json.loads( labels )
            except: 
                labels = {}
                pass
            
        args = {
            "fields" : request.fields,
            "groups" : request.groups,
            "labels" : labels,
            "filter" : kwargs.get('filter', ""),
            "delimiter" :  kwargs.get('delimiter', "")
        }
        
        _result = cls._int_groupby_query( cls._s_query, args )
        return cls._int_json_response( _result )
    
        
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
            "data" : [
                cls._int_get_empty_record(  )
            ]
        }        
        return cls._int_json_response( _result )
    
# ----------- ispSAFRS mit db.Model
class ispSAFRSModel( ispSAFRS, db.Model ):
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

    # id des records
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
       
        # log.warning("ispSAFRSDummy._s_jsonapi_attrs")
        return {}
   
    @classproperty
    def _s_columns(cls):
        """Dummy function for swagger doc.

        Returns
        -------
        list
            list of columns that are exposed by the api
        """
        # log.warning("ispSAFRSDummy._s_columns")
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
            sqla query object
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

        #q.attribute
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
            "kwargs" : kwargs,
            "python" : sys.version,
            "modules" : {}
         }
        
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
        # print( sys.executable )
        
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
    
