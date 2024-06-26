# -*- coding: utf-8 -*-

"""

webapp
======


CHANGELOG
=========

0.1.8 / 2023-09-01
------------------
- change __init__ to set/get db_bind in config
- use javascript openapi-exploer instead python based flask_swagger_ui

0.1.7 / 2023-01-11
------------------
- change api swagger info object version to use config server.api.version 

0.1.6 / 2022-05-16
------------------
- add scheme parameter to server.webserver 

0.1.5 / 2022-04-04
------------------
- add file route for query with parameter vuejs and change jinja start / end to {! !} for this and vuejs files

0.1.4 / 2022-04-04
------------------
- add file route for doc/ query with parameter raw or raw.vue

0.1.3 / 2022-03-28
------------------
- add route for tests
- change start message

0.1.2 / 2021-12-08
------------------
- changes for Python 3.8
- use add_extension for jinja extensions

0.1.1 / 2021-05-19
------------------
- change cors header

0.1.0 / 2021-01-16
------------------
- First Release

"""

__author__ = "R. Bauer"
__copyright__ = "MedPhyDO - Machbarkeitsstudien des Instituts für Medizinische Strahlenphysik und Strahlenschutz am Klinikum Dortmund im Rahmen von Bachelor und Masterarbeiten an der TU-Dortmund / FH-Dortmund"
__credits__ = ["R. Bauer", "K.Loot"]
__license__ = "MIT"
__version__ = "0.1.8"
__status__ = "Prototype"

import uuid
import os
import os.path as osp
import json
from shutil import copytree, rmtree

from isp.config import ispConfig
from isp.safrs import __version__ as safrsVersion

from safrs import log  # , paginate, SAFRSResponse
from flask import Flask, send_file
from safrs import SAFRSAPI  # , SAFRSRestAPI  # api factory
from flask import render_template, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

from isp.logging import loggingHandlerClass
from isp.socket import WebSocketClass

import connexion

import logging
logger = logging.getLogger( "ISP" )

import safrs
from safrs.swagger_doc import parse_object_doc

def expose_object( self, safrs_object, url_prefix="", **properties):
    """Eine eigene expose_object Funktion um swagger doc zu erzeugen.

    Wird bei Klassen ohne Datanbankanbindung verwendet

    .. code::

        paths: {
            <__qualname__> : {
                <__http_method> : <__rest_doc>
            }
        }

        In <__rest_doc>.tags wird wenn nicht angegeben __qualname__ abgelegt
        In <__rest_doc>.type wird wenn nicht angegeben "string" abgelegt

         creates a class of the form

        @api_decorator
        class Class_API(SAFRSRestAPI):
            SAFRSObject = safrs_object

        add the class as an api resource to /SAFRSObject and /SAFRSObject/{id}

        tablename/collectionname: safrs_object._s_collection_name, e.g. "Users"
        classname: safrs_object.__name__, e.g. "User"

        Möglichkeiten:
            a) /class/ : api_list in class aufrufen
            b) /class/{objectId} : keine Funktion objectId vorhanden also api_get aufrufen
            c) /class/test : Vorhandene Funktion test in class aufrufen

    Parameters
    ----------
    safrs_object : SAFSBase
        FSBase subclass that we would like to expose.
    url_prefix : str, optional
        url prefix. The default is "".
    **properties :
        additional flask-restful properties.

    Returns
    -------
    None.

    """
    # alle methoden der klasse durchgehen und nach __rest_doc suchen

    docs = {  }
    # alle methoden von safrs_object durchsuchen und bei eigenen methoden mit __rest_doc merken
    for method_name in dir(safrs_object):
        # die method selbst bestimmen
        try:
            method = getattr(safrs_object, method_name, None)
        except Exception as exc:
            # method_name query gibt gibt einen fehler
            # SQL expression, column, or mapped entity expected - got '<class 'xxxxx'>'
            pass

        if method and hasattr(method, '__qualname__') and hasattr(method, '__rest_doc'):
            # full_name bestimmt die eigentliche Funktion
            full_name = "{}.{}".format(safrs_object.__qualname__, method_name)
            if method_name == "api_list":
                # variante a)
                path_name = "/{}/".format( safrs_object.__qualname__ )
            elif method_name == "api_get":
                # variante b)
                path_name = "/{}/{}/".format( safrs_object.__qualname__, "{" + safrs_object._s_object_id + "}" )
            else:
                # variante c)
                path_name = "/{}".format( full_name )

            if method and method.__qualname__ == full_name :
                # für swagger . durch / ersetzen
                path_name = path_name.replace(".", "/")

                docs[ path_name ] = {}
                for hm in getattr(method, "__http_method", [] ):
                    method_doc = getattr( method, '__rest_doc', {} )
                    if not "tags" in method_doc:
                        method_doc["tags"] = [ safrs_object.__qualname__ ]
                    if not "type" in method_doc:
                        method_doc["type"] = "string"
                    # in docs ablegen
                    docs[ path_name ][ hm.lower() ] = method_doc

    # wenn in docs was ist dann die Klasse selbst in _swagger_object einfügen
    if len(docs) > 0:
        object_doc = parse_object_doc(safrs_object)
        object_doc["name"] = safrs_object.__qualname__
        self._swagger_object["tags"].append(object_doc)
        custom_swagger = {
            "paths": docs
        }
        # doc im object selbst in _swagger_paths merken
        safrs_object._swagger_paths = docs

        _swagger_doc = self.get_swagger_doc()
        safrs.dict_merge(_swagger_doc, custom_swagger)

class ispBaseWebApp():
    """Eine Flask Webapplication mit API bereitstellen.

    Attributes
    ----------
    _config: Dot
        geladene config

    _urlContentParamsKey : str
        querykey für einen jsonstring, der andere query parameter überschreibt
        default = "_ispcp"

    response_headers : dict

    app: Flask
        initialisierte Flask app

    api: SAFRSAPI
        initialisierte SAFRSAPI

    apiurl: string
        url zur api

    webSocket: WebSocketClass
        initialisierte WebSocketClass
    """

    def __init__(self, config=None, db:SQLAlchemy=None, name:str=None, webconfig=None, apiconfig=None, overlay:dict={}):
        """Erzeugt die Flask App.

        ruft _create_app auf um die Datenbank Api bereitzustellen.

        Parameters
        ----------
        config : ispConfig
            geladene config mit server.webserver und server.api
        db: SQLAlchemy
            Initialisiertes SQLAlchemy Object - db=SQLAlchemy()
        name: str
            Name der connection aus config.database.<name>.connection
        webconfig : dot|dict
            überschreibt ggf. die Inhalte aus config.server.webserver
        apiconfig : dot|dict
            überschreibt ggf. die Inhalte aus config.server.api
        overlay : dict
            überschreibt die Inhalte der config z.B. für unittest
            Verwenden von Overlay::

                from flask import current_app
                print( current_app._configOverlay )

        Returns
        -------
        None.
        """
        if config == None:
            config = ispConfig( config={
                "server": {
                    "webserver": {
                        "TESTING": True,
                        "SECRET_KEY": os.urandom(16)
                    }
                }
            })
        elif not isinstance(config, ispConfig):
            # config immer als ispConfig, dies lädt keine config daten sondern verwendet die angegebenen
            config = ispConfig( config=config )

        # overlay merken und config updaten
        self._configOverlay = overlay
        config.update( overlay )

        # in self._config merken
        self._config = config

        # keys für contentparameter
        self._urlContentParamsKey = '_ispcp'

        self._headerContentParamsKey = 'X-ISP-CONTENT-PARAMS'

        # default status code für templates (routeIndex)
        self.status_code = 200

        # default status code für templates (routeIndex)
        self.default_header = {'Content-Type': 'text/html; charset=utf-8'}

        self.webSocket = None
        #
        # webserver konfiguration aus config.server erweitern
        #
        if webconfig:
            self._config.merge( "server.webserver", webconfig )
        #
        # api konfiguration aus config.server erweitern
        #
        if apiconfig:
            self._config.merge( "server.api", apiconfig )

        #
        # Hauptdatenbank festlegen
        #
        db_names = []
        db_binds = {}
        # name für die Main Datenbank
        if not name:
            name = self._config.get("database.main", [] )

            if type( name ) == str:
                db_names.append( name )
            elif type( name ) == list:
                db_names = name

            if len(db_names) > 0:
                for name in db_names:
                    # versuchen eine passende datenbank config zu finden, wenn ja diese verwenden
                    db_uri = self._config.get("database." + name + ".connection", "", replaceVariables=True)
                    if db_uri != "":
                        db_binds[name] = db_uri
            else:
                name = "db"
                
            # without uri use memory database
            if len(db_binds) == 0:
                db_binds[name] = "sqlite:///"

        self._config.set("database.db_binds", db_binds)
        #
        # App erzeugen mit SQLAlchemy() und DatabaseUri
        #
        app = self._create_app( db, db_binds )

        # logger für safrs
        log.setLevel( self._config.get("server.logging.safrs", logging.WARNING ) ) # logging.DEBUG

        # logger für sqlalchemy
        sql_logger = logging.getLogger( "sqlalchemy" )
        sql_logger.setLevel(  self._config.get("server.logging.sqlalchemy", logging.WARNING ) )

        # app starten
        if app:
            # template_folder auf ui setzen wird bei routeRender verwendet
            app.template_folder = osp.join( self._config.BASE_DIR, "ui" )

            # wenn gewünscht dbadmin interface bereitstellen
            #
            # wird in der klasse no_flask_admin=True angegeben wird für diese admin Interface eingebunden
            if self._config.get("server.api.DBADMIN", False):

                # see if we can add the flask-admin views
                try:
                    from flask_admin import Admin
                    from flask_admin.contrib import sqla
                except Exception as exc: # pragma: no cover
                    print(f"flask-admin import failed {exc}")
                models = self._config.get( "server.api.models", [] )
                try:
                    admin = Admin(app, url="/dbadmin")
                    for model in models:
                        if hasattr( model, "no_flask_admin") and model.no_flask_admin == True:
                            pass
                        else:
                            admin.add_view(sqla.ModelView(model, db.session))
                except Exception as exc: # pragma: no cover
                    print(f"Failed to add flask-admin view {exc}")

            # app.logger für flask
            app.logger.setLevel( self._config.get("server.logging.webapp", logging.WARNING ) )

            # Modus festlegen
            mode = "APP"
            if self._config.get("server.webserver.TESTING"):
                mode = "TESTING"

            self.apiurl = "{}://{}:{}{}".format(
                self._config.get("server.webserver.scheme", "http"),
                self._config.get("server.webserver.host"),
                self._config.get("server.webserver.port"),
                self._config.get("server.api.prefix", "")
            )
            print( "Starting '{}' with BASE_DIR={}".format( 
                self._config.get("server.webserver.name", "" ), 
                self._config.get("BASE_DIR", "")
            ))
            
            # Webserver startparameter anzeigen
            print("use apiurl:'{}' in '{}' Mode".format(
                self.apiurl,
                mode
            ))
            
            #return
            if mode == "TESTING":
                # im testing mode  starten
                self.app = self.app.test_client()

            else: # pragma: no cover
                # add CORS support
                # Content-Range wird von dstore ausgewertet um die max Anzahl zu bestimmen
                CORS( self.app,
                     expose_headers='Content-Range, Content-Newitem, X-Query, X-Rquery, X_Error, X_Info'
                )

                # dieser abschnitt wird bei coverage nicht berücksichtigt, da er im testmode nicht ausgeführt wird
                # nach dem starten der app wird folgender code erst nach dem beenden ausgeführt
                if self.webSocket and self.webSocket._handler:
                    self.webSocket._handler.run(
                        app,
                        host=self._config.get("server.webserver.host"),
                        port=self._config.get("server.webserver.port"),
                        use_reloader=self._config.get("server.webserver.reloader"),
                        debug=self._config.get("server.webserver.debug"),
                        log_output=True
                    #  async_mode='eventlet'
                    )
                else:
                    app.run(
                        host=self._config.get("server.webserver.host"),
                        port=self._config.get("server.webserver.port"),
                        use_reloader=self._config.get("server.webserver.reloader"),
                        threaded=False,
                        debug=self._config.get("server.webserver.debug")
                    )    
            

    def _create_app(self, db:SQLAlchemy=None, binds:dict={} ):
        """Erzeugt die Flask App.

        Ruft create_api auf um die Datenbank api bereitzustellen

        Parameters
        ----------
        db: SQLAlchemy
            Initialisiertes SQLAlchemy Object - db=SQLAlchemy()

        """
        self.app = Flask( self._config.get("server.webserver.name", "webapp" ) )
        #SECRET_KEY
        #self.app.config['SESSION_TYPE'] = 'memcached'
        self.app.config['SECRET_KEY'] = self._config.get("server.webserver.SECRET_KEY", os.urandom(16) )

        # config und overlay in app._config merken
        self.app._config = self._config
        self.app._configOverlay = self._configOverlay

        #
        # add WebSocket 
        #
        if self._config.server.logging.handler.get("websocket", False):
            self.webSocket = WebSocketClass(
                self.app, 
                self._config.get("server.webserver").toDict(),
                {
                    "logLevel": self._config.server.logging.get( "isp", logging.NOTSET )
                }
            )
        else:
            # default isp logger aktivieren
            if self._config.webserver.get( "logging", False):
                loggingHandlerClass( {}, {
                    "logLevel": self._config.server.logging.get( "isp", logging.NOTSET )
                })
        
        #
        # extend jinja options
        #

        # markdown in templates auch für flask
        self.app.jinja_env.add_extension('jinja_markdown.MarkdownExtension')
        #self.app.jinja_options['extensions'].append('jinja_markdown.MarkdownExtension')

        # Konfigurationen für SQLAlchemy setzen
        self.app.config.update( SQLALCHEMY_BINDS=binds )

        # debug modus
        #self.app.config.update( DEBUG=True )
        self.app.config.update( SQLALCHEMY_TRACK_MODIFICATIONS=False)

        if db:
            # SQLAlchemy mit app initialisieren
            db.init_app( self.app )

            # Datenbank und Datenbank Api
            with self.app.app_context( ):
                try:
                    db.create_all( bind_key=binds.keys() )
                except Exception as exc: # pragma: no cover
                    print( "[webapp] _create_app error" , exc)
                self._create_api( )

        @self.app.before_request
        def before_request_func( ):
            """Wird vor jedem request aufgerufen.

            hier wird _checkNetarea aufgerufen

            Returns
            -------
            None.

            """
            # Zugangsbeschränkung prüfen
            return ( self._checkNetarea() )

        # zusätzliche routen ermöglichen
        self.addRoutes(  )

        # zusätzliche default routen
        @self.app.route('/')
        @self.app.route('/<path:filepath>')
        def home( filepath:str='' ):
            self.status_code = 200
            self.default_header = None # auto default based on extension
            return self.routeIndex( filepath ), self.status_code, self.default_header

        return self.app

    def _create_api(self):
        """Generate SAFRSAPI.

        with additional swagger Doc for classes without a database connection

        Returns
        -------
        None.

        """
        # load additional swagger configuration if required
        custom_swagger = {
            "info" : {
                "title" : self._config.get("server.webserver.name", "webapp"),
                "description" : self._config.get("server.webserver.title", "webapp"),
                "version" : self._config.get("server.api.version", safrsVersion )
            },
            "parameters" : {
                "validatorUrl" : False
            },
            "validatorUrl" : False
        }
        if self._config.get("server.api.custom_swagger_config", False):
            swaggerPath = osp.join( self._config.BASE_DIR, "config", self._config.get("server.api.custom_swagger_config", "") )
            # load the specified swagger config
            if osp.isfile( swaggerPath ):
                with open( swaggerPath, 'r') as f:
                    custom_swagger = json.load( f )

        prefix = self._config.get("server.api.prefix")
        self.api = SAFRSAPI(self.app,
            host=self._config.get("server.webserver.host"),
            port=self._config.get("server.webserver.port"),
            prefix=prefix,
            swaggerui_blueprint=False,
            custom_swagger=custom_swagger
        )

        # go through all models and add a pointer to api
        for model in self._config.get("server.api.models"):
            # model bekannt machen 
            self.api.expose_object( model )
            
            # create swagger docu for extensions without a database
            if hasattr( model, "no_flask_admin") and model.no_flask_admin == True:
                expose_object(self.api, model)
            model._api = self.api

    def _checkNetarea( self ): # pragma: no cover
        """Simple check whether the access is from the same subnetwork.

        Skip on localhost and TESTING=True in config.server.webserver

        """
        # is TESTING mode on: do nothing
        if self._config.get("server.webserver.TESTING", False):
             return

        # prüfen auf checkNetarea in config webserver
        if not self._config.get("server.webserver.checkNetarea", True):
             return

        # with unittest there is no REMOTE_ADDR or it is a local call
        if request.remote_addr == None or request.remote_addr == "127.0.0.1":
            return

        # check access
        remote_area = ".".join( request.environ.get('REMOTE_ADDR').split(".")[:3] )
        netarea = ".".join( request.environ.get('SERVER_NAME').split(".")[:3] )

        if not remote_area == netarea:
            # Error 401 access not allowed
            return "Der Zugriff ist für ihre IP verboten", 401

        return

    def addRoutes( self ):
        """Überschreibbare Funktion um zusätzliche routen einzubinden.

        Sample::
            def addRoutes( self ):
                @self.app.route('/test/<path:filepath>')
                def test_route( filepath:str='' ):
                    return "testroute"
        """
        pass

    def parseRequestParams( self, queryParams:dict={}, defaults:dict={} ):
        """Parsed zusätzliche query parameter für routeRender.

        Parameters
        ----------
        queryParams: dict
            { '_ispcp': '{"jahr":2018}'}

        defaults: dict
            vorgaben, die durch angegebene Parameter erweitert bzw. überschrieben werden

        Returns
        -------
        dict:
            Überprüfte und zusammengefasste Parameter

        """
        # params mit defaults vorbelegen
        params = defaults.copy()

        #logger.debug( "parseRequestParams: bei json parse in url content" )
        #
        # Vorarbeiten <_urlContentParamsKey> auswerten und aus queryParams entfernen
        #

        urlContentParams = None

        if self._urlContentParamsKey in queryParams:
            urlContentParams = queryParams[ self._urlContentParamsKey ]
            del queryParams[ self._urlContentParamsKey ]

        #
        # 1. alle url parameter (queryParams) außer <_urlContentParamsKey> einfach verwenden
        #
        params.update( queryParams )

        #
        # 2. wenn ein valider jsonstring oder ein dict in <_urlContentParamsKey>
        #
        if urlContentParams:
            if type( urlContentParams ) == str:
                try:
                    rparams = json.loads( urlContentParams )
                    params.update( rparams )
                except:
                    logger.debug( "parseRequestParams: bei json parse in url content" )
                    pass
            elif type( urlContentParams ) == dict: # pragma: no cover
                # kann nur passieren wenn render nicht über den Webserver aufgerufen wird
                params.update( urlContentParams )

        return params

    def routeIndex(self, filepath="" ):
        """Verarbeitet normale Aufrufe.

        Umgeleitete filepath Pfade:

        * resources/ nach server.webserver.resources
        * fonts/ nach server.webserver.resources/fonts
        * globals/ nach server.webserver.globals
        * dbadminframe/ iframe für dbadmin erstellen
        * docs nach docs/build/html/
        * htmlcov nach docs/
        * render/ rendert .phtml in ui/

        alles andere wird auch aus ui/ geholt

        ohne filepath wird index.html aufgerufen

        Parameters
        ----------
        filepath : str, optional
            file und path zu einer datei. The default is "".

        Returns
        -------
        output :
            Inhalt der geladenen Datei

        """

        # alles normalerweise aus ui verwenden
        root = self._config.get("server.webserver.ui", "", replaceVariables = True)
  
        # connexion verwendet FirstValueURIParser collectionFormat: csv
        # ?letters=a,b,c&letters=d,e,f wird letters = ['a', 'b', 'c']
        params = self.parseRequestParams( connexion.request.args.copy() ) 

        if filepath[:10] == "resources/":
            root = self._config.get("server.webserver.resources", "", replaceVariables = True)
            filepath = filepath[10:]
        elif filepath[:6] == "fonts/":
            root = self._config.get("server.webserver.resources", "", replaceVariables = True)
        elif filepath[:8] == "globals/":
            root = self._config.get("server.webserver.globals", "", replaceVariables = True)
        elif filepath[:8] == "apiframe":
            return self.routeIFrame( "/api" )
        elif filepath[-3:] == "api" or filepath[-4:] == "api/":
            return self.routeApi( self.apiurl )
        elif filepath[:12] == "dbadminframe":
            return self.routeIFrame( "/dbadmin" )
        elif filepath[:4] == "docs":
            if "raw" in params or "raw.vue" in params:
                return self.routeFile( filepath, osp.join( self._config.get( "BASE_DIR", "docs")  ) )
            else:
                return self.routeDocs( filepath )
        elif filepath[:8] == "coverage":
            return self.routeCoverage( filepath )
        elif filepath[:7] == "render/":
            return self.routeRender( filepath[7:] )
        elif "vuejs" in params or filepath[-4:] == ".vue" or filepath[:6] == "views/" :
            self.default_header = {'Content-Type': 'application/javascript; charset=utf-8'}
            return self.routeRender( filepath, True )
        elif filepath[:9] == "unittest_":
            # Spezielle render aufruf für unittest
            return self.routeRender( filepath )
        elif filepath[:6] == "tests/":
            # Spezieller aufruf für Dateien in tests
            root = self._config.get("server.webserver.resources_test", "{{BASE_DIR}}/tests/", replaceVariables = True)
            filepath = filepath[6:]
        else:
            # alles andere - ohne Angaben index aufrufen
            if filepath == "" or filepath == "index.html" or filepath == "index.phtml":
                filepath = "index"
                return self.routeRender( filepath  )

        return self.routeFile( filepath, root )

    def routeApi( self, apiurl:str="", spec="swagger.json" ):
        return """
            <!doctype html>
            <html>
            <head>
                <script type="module" src="/resources/vendor/openapi/rapidoc-min.js"></script>
            </head>
            <body>    
                <rapi-doc
                    id="openapi-doc"
                    spec-url="{}/{}"
                    server-url="{}/"
                    load-fonts="false"
                    show-info="true" 
                    theme="light"
                    render-style="read"
                > </rapi-doc>  
            </body>
            </html>
            """.format( apiurl, spec, apiurl )

    def routeFile( self, filepath:str="", root="" ):
        """Eine normale Datei laden.

        Parameters
        ----------
        filepath : str, optional
            file und path einer datei aus root. The default is "".
        root : str, optional
            Basispfad für filepath

        Returns
        -------
        output :
            Inhalt der geladenen Datei

        """
        
   
        try:
            _filepath = osp.join( root, filepath ) # .format( **{"BASE_DIR": self._config.BASE_DIR} )
            output = send_file( _filepath )
        except:
            output = "<h1>Datei '{}' wurde nicht gefunden</h1>".format( filepath )
            self.status_code = 404
            pass
        return output

    def routeRender( self, filepath:str="", is_vue:bool=False ):
        """Ein Template in ui oder template_folder rendern.

        if is_vue 
        
        Parameters
        ----------
        filepath : str, optional
            file und path einer datei aus ui. The default is "".
        is_vue: bool,optional
            Render with jinja start / end {! / !} The default is false.
        Returns
        -------
        output : str
            Das gerenderte Template.


        """

        # .vue as default in views
        if is_vue or filepath[-4:] == ".vue" or filepath[:6] == "views/":
            if filepath.find(".vue") == -1 and filepath.find(".js") == -1:
                filepath = "{}.vue".format( filepath )
        else:
            # otherwise default is .phtml
            if filepath.find(".phtml") == -1:
                filepath = "{}.phtml".format( filepath )

        uuidstr = str( uuid.uuid1() )
        params = {
             "uuid" : uuidstr,
             "id" : "uuid_" + uuidstr
        }

        # defaults mit requestParams überschreiben
  
        # connexion verwendet FirstValueURIParser collectionFormat: csv
        # ?letters=a,b,c&letters=d,e,f wird letters = ['a', 'b', 'c']
        params.update( self.parseRequestParams( connexion.request.args.copy() ) )

        # value bestimmen
        value = params.get("value", None )
        variables = self._config.get("variables", {}, replaceVariables=True ).toDict()
        
        v = {
            "params": params,
            "value": value,
            "id": params["id"],
            "uuid": uuidstr,
            "variables": variables
        }
        
        if is_vue:
            
            # change variable_start_string and variable_end_string for vue files
            variable_start_string = self.app.jinja_env.variable_start_string
            variable_end_string = self.app.jinja_env.variable_end_string
            
            self.app.jinja_env.variable_start_string = "{!"
            self.app.jinja_env.variable_end_string = "!}"
        
        try:
            output = render_template(
                filepath,
                v = v,
                params = json.dumps( params ),
                value = value,
                id = params["id"],
                uuid = uuidstr,
                **self._config.get("variables", {}, replaceVariables=True ).toDict()
                
            )
        except Exception as err:
            output = "<h1>Das Template {} wurde nicht gefunden oder ein parser error [ {} ] liegt vor.</h1>".format( filepath, err )
            self.status_code = 404
            pass
        if is_vue:
            self.app.jinja_env.variable_start_string = variable_start_string 
            self.app.jinja_env.variable_end_string = variable_end_string 
        return output

    def routeIFrame( self, src:str="" ):
        """Filepath in iframe anzeigen.

        Aufrufe::

            /apiframe - api im iframe anzeigen. Mit src="/api"
            /dbadminframe - dbadmin im iframe anzeigen. Mit src="/dbadmin"

        Parameters
        ----------
        src : str, optional
            src Angabe des iframe. The default is "".

        Returns
        -------
        str
            div mit iframe

        """
        return '<div class="iframe-container overflow-hidden flex-1"><iframe src="{}" ></iframe></div>'.format( src )

    def routeDocs( self, filepath:str="" ):
        """Die Dokumentation anzeigen oder erzeugen.

        Aufruf::
            /docs/index.html - Dokumentation anzeigen
            /docs - Dokumentation im iframe anzeigen. Mit src="docs/index.html"
            /docs/build - Dokumentation erzeugen
            /docs/rebuild - Dokumentation komplett erneuern (ui-docs)

        """
        
        # wenn nur docs angegeben wurde iframe erstellen
        if len(filepath) == 4:
            return '<div class="iframe-container overflow-hidden flex-1"><iframe src="/docs/index.html" ></iframe></div>'
        
        # Ausführungspfad für docs festlegen
        docs_root = osp.join( self._config.get( "BASE_DIR", "") , '.docs' )
        docs_path = docs_root

        # docs/ nicht verwenden
        filepath = filepath[5:]

        # prüfen ob es docs_path gibt, sonst zuerst die dokumentation erzeugen
        if not osp.isdir( docs_path ) or not osp.isfile( osp.join( docs_path, "build", "index.html" ) ): # pragma: no cover
            filepath = "build"

        if filepath == "build" or filepath == "rebuild": # pragma: no cover
            # Dokumentation erzeugen filepath als mode mitgeben
            if not self.createDocs( docs_path, filepath ):
                return "<h1>Eine Dokumentation ist nicht vorhanden.</h1>"

            filepath = "index.html"

        return self.routeFile( filepath, osp.join( docs_root, "build" ) )

    def createDocs( self, docs_path:str="", mode:str="build" ): # pragma: no cover
        """Dokumentation erzeugen oder erneuern.

        Parameters
        ----------
        docs_path : str, optional
            Pfad nach ui-docs. The default is "".
        mode : str, optional
            Mit rebuild komplett neu erzeugen sonst nur erneuern. The default is "build".

        Returns
        -------
        bool
            ``True`` wenn erzeugt wurde, sonst ``False``.

        """
        import sphinx.ext.apidoc as apidoc
        import sphinx.cmd.build as build

        if mode == "rebuild" and osp.isdir( docs_path ):
            try:
                rmtree( docs_path )
            except:
                return False

        # ohne docs_path vorlage aus helper/docs kopieren
        if not osp.isdir( docs_path ) or not osp.isdir( osp.join( docs_path, "build" ) ):
            # conf und _static kopieren
                
            # vorlage kopieren
            #
            from_path = osp.join( osp.dirname(osp.abspath( __file__ )), "helper", "sphinx" )
        
            try:
                copytree( from_path, docs_path, dirs_exist_ok=True )
            except Exception as e:
                logger.debug( "ERROR copytree {} {}".format( from_path, docs_path ) )
                print( "ERROR copytree {} {}".format( from_path, docs_path ), e )
                return False

            # original docs auch kopieren
            #
            org_docs_from_path = osp.join( self._config.get( "BASE_DIR", "") , 'docs' )

            if osp.isdir( org_docs_from_path ):
                org_docs_to = osp.join( docs_path, "source", "docs" )
                try:
                    copytree( org_docs_from_path, org_docs_to, dirs_exist_ok=True )
                except Exception as e:
                    logger.debug( "ERROR copytree {} {}".format( org_docs_from_path, org_docs_to ) )
                    print( "ERROR copytree {} {}".format( org_docs_from_path, org_docs_to ), e )

        # es wurde nichts angelegt - Fehlermeldung ausgeben
        if not osp.isdir( org_docs_to ):
            logger.debug( "ERROR createDocs no path {} {}".format( org_docs_to ) )
            print("### createDocs no path", org_docs_to )
            return False


        # ausführungs Pfad auf docs_path ändern
        os.chdir( docs_path )

        # ---- 1. rst Dateien in source erzeugen
        api_cmd = [
             '--force',       # force
             '-osource/',     # destdir
             '../',           # module_path
             '../tests*',     # exclude_pattern tests
             '../ui*'       # weitere exclude_pattern
        ]

        apidoc.main( api_cmd )

        # ---- 2. html aus rst Dateien in build erzeugen
        #

        # get project information from main version file
        import version as v

        build_cmd = [
            'source',
            'build',
            '-Dcopyright={}'.format( v.__copyright__ ),
            '-Dauthor={}'.format( v.__author__ ),
            '-Dproject={}'.format( self._config.get("server.webserver.title", v.__project__) ),
            '-Dversion={}'.format( v.__version__ ),
            '-Drelease={}'.format( v.__version__ )
        ]

        build.main( build_cmd )

        return True

    def routeCoverage( self, filepath:str="" ): # pragma: no cover
        """Ein template in htmlcov rendern.

        Die Pfade in den .html Dateien werden angepasst,
        da der Aufruf sonst nur im Verzeichnis selbst fuktioniert

        Parameters
        ----------
        filepath : str, optional
            Pfad zum template. The default is "".

        Returns
        -------
        str|mixed
            Ruckgabe von flask send_file oder geänderter html Inhalt.

        """
        # wenn nur coverage angegeben wurde iframe erstellen
        if len(filepath) == 8:
            return '<div class="overflow-hidden flex-1"><iframe src="/coverage/index.html" ></iframe></div>'
        else:
            filepath = filepath[9:]


        htmlcov_root = osp.join( self._config.get( "BASE_DIR", "") , '.htmlcov' )

        # Ausführungspfad für docs festlegen
        root = htmlcov_root #.format( **{"BASE_DIR": self._config.BASE_DIR} )

        if filepath == "":
            filepath = "index.html"

        if not osp.isfile( osp.join( root, filepath ) ):
            return """
            <h1>Coverage wurde noch nicht erzeugt.</h1>
            Starte <b>python {}/tests/all_unittest.py</b> von der Kommandozeile
            """.format( self._config.get( "BASE_DIR", "") )

        # Sonderbehandlung für html dateien dort muss src=" und href=" um /coverage/ erweitert werden
        if filepath[-5:] == ".html":
            from bs4 import BeautifulSoup
            data = ""

            with open( osp.join( root, filepath ) , 'r') as myfile:
                data = myfile.read()
                soup = BeautifulSoup(data, "html.parser")
                # alle href suchen
                href_tags = soup.find_all(href=True)
                for tag in href_tags:
                    if not tag["href"][:4] == "http":
                        tag["href"] = "/coverage/" + tag["href"]

                src_tags = soup.find_all(src=True)
                for tag in src_tags:
                    tag["src"] = "/coverage/" + tag["src"]

                data = str( soup )
            return data


        return send_file( osp.join( root, filepath ) ) #.format( **{"BASE_DIR": self._config.BASE_DIR} ) )
