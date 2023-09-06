# -*- coding: utf-8 -*-

'''

config
======


logging
-------

logging verwenden::

    import logging
    logger = logging.getLogger( "MQTT" )

debug Meldungen ausgeben::

    logger.setLevel( logging.DEBUG )

logging level:

* CRITICAL - 50
* ERROR - 40
* WARNING - 30
* INFO - 20
* DEBUG - 10
* NOTSET - 0


CHANGELOG
=========

0.1.3 / 2023-04-17
------------------
- use merge.mergedeep instead function with colletions
- change _configLoad() for better error handling 

0.1.2 / 2022-05-16
------------------
- add scheme parameter to server.webserver 
- remove webserver from use_as_variables

0.1.1 / 2022-03-28
------------------
- add jinja Filter: fromisoformat, datetimeformat and jsondumps
- use secrets.token_hex() instead of os.urandom(16) for SECRET_KEY

0.1.0 / 2021-01-16
------------------
- First Release

'''

__author__ = "R. Bauer"
__copyright__ = "MedPhyDO - Machbarkeitsstudien des Instituts für Medizinische Strahlenphysik und Strahlenschutz am Klinikum Dortmund im Rahmen von Bachelor und Masterarbeiten an der TU-Dortmund / FH-Dortmund"
__credits__ = ["R. Bauer", "K.Loot"]
__license__ = "MIT"
__version__ = "0.1.3"
__status__ = "Prototype"

import sys
import json
import os.path as osp
from dotmap import DotMap
from mergedeep import merge

from jinja2 import Environment, FileSystemLoader

from datetime import datetime
import glob
import re
import threading

import secrets

import logging

from isp.mqtt import MQTTclass

default_config = {
    "server" : {
        "webserver" : {
            "scheme": "http",
            "host": "127.0.0.1",
            "port": 8085,
            "name": "webapp",
            "title": "webapp",
            "resources" : "{{BASE_DIR}}/resources/",
            "globals" : "{{BASE_DIR}}/resources/",
            "ui" : "{{BASE_DIR}}/ui/",
            "debug": True,
            "reloader": True,
            "TESTING": False,
            "resources_test" : "{{BASE_DIR}}/tests/",
            "checkNetarea": True,
            "SECRET_KEY": secrets.token_hex()
        },
        "api": {
            "prefix" : "/api",
            "models" : [ ],
            "DBADMIN": False,
            "COVERAGE" : False
        }
    },
    "use_as_variables":{
     #   "webserver" : "server.webserver",
        "api" : "server.api",
        "mqtt" : "server.mqtt",
        "title" : "server.webserver.title",
        "resources" : "server.webserver.resources"
    }
}

class ispConfig( object ):
    """Konfiguaration aus config/config.json einlesen und bereitstellen.

    Die config ist immer im development Mode außer im Pfad kommt production vor
    dann wird production Mode gesetzt


    Aufbau der config.json zugriff über ._config::

        {
             "config": {
                 <haupt konfig bereich : zugriff über .config>
             }
        }


    Attributes
    ----------

    _config: Dot
        Die aktuelle Konfiguration
    _configs: list
        Eingebundene Konfigurationen (filename oder angegeben bei der intialisierung )
    _lastOverlay: str
        Gibt an bis zu welcher config Datei eingelesen wurde
    _rootlevel:int
        Fehlerlevel für das root logging (console). Default logging.WARNING

    _mqttlevel:int
        Fehlerlevel für das MQTT logging. Default logging.ERROR

    _basedir: str
        Verzeichniss des aufgerufenen Programms

    _name : str
        name des aufgerufenen Programms

    _development : bool
        Entwicklungszweig verwenden (True) oder nicht (False)

    _loadErrors: list
        listet die Dateien auf bei denen es zu einem Fehler beim einlesen kam

    _mqtthdlr: None|cls
        logger für mqtt zugriff über self._mqtthdlr

    """

    def __init__( self, lastOverlay:int=None, development:bool=True,
                 rootlevel:int=logging.ERROR,
                 mqttlevel:int=logging.NOTSET,
                 cleanup:bool=False,
                 config:dict=None
                 ):
        """Konfiguration initialisieren und laden.

        Zuerst wird die Konfiguration config.json eingelesen
        und anschließend sortiert von allen passenden config-*.json Dateien überlagert

        Parameters
        ----------
        lastOverlay : int
            Gibt an bis zu welcher config Datei eingelesen wird.Default = 99999999 (config-99999999.json).

        development : bool
            Entwicklungszweig verwenden oder nicht. Default is True.
            Wird die App in einem Unterverzeichnis mit dem Namen production/ oder development/ abgelegt,
            so wird development autom. je nach Name gesetzt.

        rootlevel: int - logging.ERROR
            NOTSET=0, DEBUG=10, INFO=20, WARN=30, ERROR=40, and CRITICAL=50. Default: ERROR

        mqttlevel: int - logging.NOTSET
            NOTSET=0, DEBUG=10, INFO=20, WARN=30, ERROR=40, and CRITICAL=50. Default: NOTSET

        cleanup: bool
            MQTT Cleanup vor dem initialisieren durchführen. Default = False

        config: dict
            mit dieser Angabe wird keine Konfiguration geladen, sondern die angegebenen Daten verwendet

        """
        
        # _basedir festlegen mit __file__ damit ein testaufruf von hier funktioniert
        self._basedir = osp.abspath( osp.join( osp.dirname( osp.abspath( __file__ ) ) , "../" ) )
        # name des startenden programms
        self._name = osp.basename( sys.argv[0] )

        # test auf Entwicklungsumgebung
        self._development = development
        if self._basedir.find( '/production/' ) > -1: # pragma: no cover
            self._development = False
        elif self._basedir.find( '/development/' ) > -1:
            self._development = True

        # lastOverlay auf das aktuelle Datum
        if lastOverlay == None:
            # ohne lastOverlay zuerst den Zahlenwert für das aktuelle Datum
            lastOverlay = datetime.now().strftime("%Y%m%d")

        # listet die Dateien auf bei denen es zu einem Fehler beim einlesen kam
        self._loadErrors = []

        # default werte setzen
        self._config = DotMap( default_config )
        self._configs = ["default"]

        if config:
            # config in self._config merken
            self.update( config )
            self._configs.append( "init" )
        else:
            # Konfiguration einlesen und in self._config merken
            self._configLoad( int(lastOverlay) )

        self._lastOverlay = lastOverlay

        # die Konfiguration um BASE_DIR erweitern
        self._config[ "BASE_DIR" ] = self._basedir

        # default logger
        self.rootInitLogger( rootlevel )

        # logger für mqtt zugriff über self._mqtthdlr
        self._mqtthdlr = None

        # mqtt Logger bereitstellen oder initialisieren
        self.mqttInitLogger( mqttlevel, cleanup )

        # variables vorbelegen
        self.setVariables()

        # Jinja Environment bereitstellen
        self._env = self.jinjaEnv()

    def update(self, config:dict={} ):
        """Führt ein update wie bei dict.update aber mit dict_merge aus.

        Parameters
        ----------
        config : dict
            In die config zu mischendes dict.

        Returns
        -------
        self

        """
        self._config = dict_merge(self._config, DotMap( config ) )
        return self

    def merge(self, name:str=None, config:dict={}):
        """Führt ein update in einem angegebenen config Zweig aus.

        Gibt es name nicht wird er angelegt

        Parameters
        ----------
        name : str
            Bezeichner dessen Inhalt ausgelesen wird . operator für die tiefe
        config : dict
            In den config Zweig zu mischendes dict.

        Returns
        -------
        self

        """
        branch = self.get(name, {} )

        self.set( name, dict_merge(branch, DotMap( config ) ) )

        return self

    def _configLoad( self, lastOverlay:int=99999999 ):
        """Konfiguration aus config.json einlesen.

        Die Datei muss sich ab _basedir im Verzeichniss config befinden

        Alle config Dateien bis zu der durch _overlayLast gebildeten einlesen

        Parameters
        ----------
        lastOverlay : int
            Default is 99999999

        """
        
        def readConfig( filename:str ):
            """
            Read config from filename

            Parameters
            ----------
            filename : str
                Config filename to read.

            Returns
            -------
            loadOK : bool
                true if config loaded

            """
            loadOK = True
            if osp.isfile( filename ):
                # zuerst die normale config Datei einlesen
                with open( filename, 'r') as f:
                    try:
                        config = json.load( f )
                    except:
                        # Fehler auch hier anzeigen, da noch kein logger bereitsteht
                        self._loadErrors.append( filename )
                        self._configs.append( osp.basename( filename ) + " - ERROR" )
                        print( "CONFIG: Fehler bei json.load", filename )
                        loadOK = False
                        pass
                    if loadOK:
                        try:
                            self._config = dict_merge(self._config, DotMap( config ) )
                            self._configs.append( osp.basename( filename ) )
                        except:
                            # Fehler auch hier anzeigen, da noch kein logger bereitsteht
                            self._loadErrors.append( filename )
                            self._configs.append( osp.basename( filename ) + " - ERROR" )
                            print( "CONFIG: Fehler bei DotMap( config )", self._config )
                            loadOK = False
                            pass
            return loadOK
        
        # den pfad zur konfiguration festlegen
        configPath = osp.join( self._basedir, "config")

        # zuerst die normale config Datei einlesen
        readConfig( osp.join( configPath, "config.json") )

        # jetzt alle anderen overlay dateien sortiert einlesen und überlagern
        configs = glob.glob(osp.join( configPath, 'config-*.json') )
        if len(configs) > 0:
            configs.sort()
            # alle config Dateien mit Zahlen nach dem - zusammenstellen
            for name in configs:
                res = re.search('config-([0-9]*)\.json', name )
                # jahr und monat als zahl umwandeln, ein jahr allein wird mit 00 ergänzt
                ym = 99999999
                if res:
                    ym = int( res.group(1) )
                    if ym <= lastOverlay:
                        readConfig( name )


    def setVariables( self ):
        """Setzt Defaults und Angaben aus use_as_variables in variables.

        setzt immer::

            - BASE_DIR
            - version
            - serverHost
            - alles aus use_as_variables

        Returns
        -------
        variables : dict
            variables Bereich aus der config

        """
        variables = self._config.get("variables", DotMap() ).toDict()
        use_as_variables = self._config.get("use_as_variables", DotMap() ).toDict()

        variables["BASE_DIR"] = self._basedir
        variables["version"] = self.get( "version", __version__)
        variables["serverHost"] = "{}://{}:{}".format(
            self.get("server.webserver.scheme", ""),
            self.get("server.webserver.host", ""),
            self.get("server.webserver.port", "")
        )

        for config_name, config_key in use_as_variables.items():
            value = self.get( config_key )
            if isinstance( value, DotMap ):
                variables[ config_name ] = self.get( config_key ).toDict()
            else:
                variables[ config_name ] = self.get( config_key )

        self._config["variables"] = variables

        return variables


    def __setitem__(self, k, v):
        """Defines behavior for when an item is assigned to.

        using the notation self[nkey] = value.
        This is part of the mutable container protocol.
        Again, you should raise KeyError and TypeError where appropriate.

        Parameters
        ----------
        k : str
            Name des Attributs aus dem Object oder der _config.
        v :
            Zu setzender Inhalt.

        """
        if k[0] == "_":
            super().__setattr__(k, v)
        else:
            self._config[k] = v

    def __getitem__(self, k):
        """Zugriff auf die Klassenattribute mit _.

        sonst wird aus self._config geholt

        Defines behavior for when an item is accessed, using the notation self[key].
        This is also part of both the mutable and immutable container protocols.
        It should also raise appropriate exceptions::

            TypeError if the type of the key is wrong and KeyError if there is no corresponding value for the key.

        Parameters
        ----------
        k : str
            Name des gesuchten Attributs aus dem dict des Object oder der _config.

        Returns
        -------
        Wert des Attributs

        """
        if k[0] == "_":
            return self.__dict__[k]
        else:
            return self._config[k]

    def __setattr__(self, k, v):
        """Zugriff auf die Klassenattribute mit _.

        sonst wird in self._config gesetzt

        Unlike __getattr__, __setattr__ is an encapsulation solution.
        It allows you to define behavior for assignment to an attribute regardless
        of whether or not that attribute exists,
        meaning you can define custom rules for any changes in the values of attributes.
        However, you have to be careful with how you use __setattr__.

        Parameters
        ----------
        k : str
            Name des Attributs aus dem Object oder der _config.
        v :
            Zu setzender Inhalt.

        """
        if k[0] == "_":
            self.__dict__[k] = v
        else:
            self._config[k] = v

    def __getattr__(self, k):
        """Access nonexistent attribute.

        Gibt bei _ None und sonst aus config zu bestimmen.

        * Nicht Vorhanden im object bei _ : None
        * Nicht vorhanden in config: DotMap bzw. DotMap mit inhalt

        self.name # name doesn't exist

        Parameters
        ----------
        k : str
            Name des gesuchten Attributs aus dem Object oder der _config.

        Returns
        -------
        Wert des Attributs oder None.

        """
        if k[0] == "_":
            return None
        else:
            return self._config[k]

    def __repr__(self):
        """Define behavior for when repr() is called on an instance of your class.

        The major difference between str() and repr() is intended audience.
        repr() is intended to produce output that is mostly machine-readable (in many cases, it could be valid Python code even),
        whereas str() is intended to be human-readable.

        Returns
        -------
        str
            Inhalt der config.

        """
        return str(self._config)

    def get(self, name:str=None, default=None, replaceVariables:bool=False):
        """Read from configuration. 

         without specifying complete config returned 

        Parameters
        ----------
        name : str|list
            Identifier whose content is read out. Dot operator for depth 
        default :
            Return if name not found 
        replaceVariables: bool
            Replace variable information in strings. Default is False

        """
        
        # without specifying complete config returned 
        if not name:
            return self._config.toDict()

        keys = []
        if isinstance(name, str):
            keys = name.split(".")
        elif isinstance(name, list):
            keys = name

        val = None

        for key in keys:
            if val == None:
                # try first level 
                val = self._config.get( key )
                # undefined : always use DotMap 
                if not val:
                    self._config[ key ] = DotMap()
            else:
                if isinstance( val, DotMap):
                    try:
                        val = val.get(key, default)
                    except Exception as e: # pragma: no cover
                        # occurs when a non-existent sub key is searched for, a.b = 12 but search for a.b.c
                        print("CONFIG: config.get error on get", keys, key, type(val), e )
                        val = default
                        pass

        if val == None:
            val = default

        # replace variables if desired 
        if isinstance(val, str) and replaceVariables==True:
            val = self.render_template( val )

        return val

    def set(self, setkeys:str=None, value=None):
        """set a value in the configuration. 

        Parameters
        ----------
        setkeys : str|list
            Identifier whose content is set use dot operator for the depth.
        value :
            Content to set 

        """
        # starting point is the config itself 
        here = self._config

        # convert setkeys to list 
        keys = []
        if isinstance(setkeys, str):
            keys = setkeys.split(".")
        elif isinstance(setkeys, list):
            keys = setkeys

        # For every key *before* the last one, we concentrate on navigating through the dictionary.
        for key in keys[:-1]:
            # Try to find here[key]. If it doesn't exist, create it with an empty DotMap.
            # Then, update our `here` pointer to refer to the thing we just found (or created).
            here = here.setdefault(key, DotMap() )

        # Finally, set the final key to the given value
        here[keys[-1]] = value

    def rootInitLogger( self, level:int=None ):
        """Initializes the root logger 

        Parameters
        ----------
        level : int, optional
            Logging Level. The default is None.

        Returns
        -------
        None.

        """
        baselogger = logging.getLogger(  )

        # set level if specified 
        if level:
            baselogger.setLevel( level  )

    # ---- Jinja Environment
    #
    def jinjaEnv(self):
        """Create Jinja Environment.

        to add more extensions read:

        - https://github.com/jpsca/jinja-markdown

        Returns
        -------
        env: Environment

        """
        # 
        # since the template system is not yet ready, simply replace BASE_DIR 
        #
        tpl_dir = self.server.webserver.get("resources", ".").replace("{{BASE_DIR}}",  self.BASE_DIR )
        from jinja2 import select_autoescape
        env = Environment(
            extensions=[ 'jinja_markdown.MarkdownExtension'],
            loader=FileSystemLoader(tpl_dir),
            autoescape=select_autoescape(
                disabled_extensions=('tmpl',),
                default_for_string=False,
                default=True,
            )
        )
        def fromisoformat(value):
            try:
                value = datetime.fromisoformat( value )
            except Exception:
                pass
            return value
            
        def datetimeformat(value, format="%Y-%m-%d"):
            try:
                value = value.strftime(format)
            except Exception:
                pass
            return value
        
        def jsondumps(value):
            try:
                value = json.dumps(value, indent=2)
            except Exception:
                pass                
            return value
        
        env.filters["fromisoformat"]  = fromisoformat
        env.filters["datetimeformat"]  = datetimeformat
        env.filters["jsondumps"]  = jsondumps
        return env

    def render_template( self, tpl:str="", variables:dict=None, deep_replace:bool=False ):
        """Replaces all variables from variables in tpl. 

        If variables are not specified, _config["variables"] is used 

        Parameters
        ----------
        tpl : str, optional
            Jinja template string. The default is "".
        variables : dict, optional
            Variable information to be replaced. The default is _config["variables"].
        deep_replace: bool, optional
            Executes render twice to also replace statements in variables. The default is False

        Returns
        -------
        tpl: str
            rendered template

        """
        if not variables:
            variables = self._config["variables"]
            
        # always give now with the current time 
        variables["now"] = datetime.now()
        # depending on deep_replace single or multiple runs
        n = range(1)
        if deep_replace:
            n = range(3)

        for i in n:
            try:
                _tpl = self._env.from_string( tpl )
                tpl = _tpl.render( **variables )
            except Exception as e: # pragma: no cover
                print("CONFIG: config.render_template error on _tpl.render", e)
        return tpl


    # ---- MQTT Logging
    #
    def mqttInitLogger( self, level:int=None, cleanup:bool=False  ):
        """Turn on logging via MQTT. 

        Parameters
        ----------
        level : int, optional
            NOTSET=0, DEBUG=10, INFO=20, WARN=30, ERROR=40, and CRITICAL=50. Default: NOTSET
        cleanup : bool, optional
            Perform MQTT cleanup before initializing. Default = False

        Returns
        -------
        None.

        """
        # root logger first 
        self.logger_name = "root"

        # set up a new handler if desired 
        if cleanup:
            self.mqttCleanup()

        if self._config.server.mqtt:
            # Set MQTT logger 
            logger = logging.getLogger( "MQTT" )

            # Handler for MQTT
            mqtthdlr = self.mqttGetHandler( )

            if not mqtthdlr:

                #
                # if something is changed here, the kernel must be restarted or mqttCleanup called 
                #

                mqtt_init_ready = threading.Event()

                self._thread_mqtthdlr = None

                def signalStartup( msg ):

                    mqtt_init_ready.set()

                def startMQTTclass():
                    """Start MQTTclass via threading and wait for signalStartup. 

                    Returns
                    -------
                    None.

                    """
                    self._thread_mqtthdlr = MQTTclass( self._config.server.mqtt.toDict() )
                    # wait for signal
                    self._thread_mqtthdlr.signalStartup.connect( signalStartup )

                # Call as a thread,via mq.get() to get the return of _retrieve 
                thread = threading.Thread( target=startMQTTclass )
                thread.start()

                # wait for 2 seconds or mqtt_init_ready signalStartup 
                while not mqtt_init_ready.wait( timeout=2 ):
                    mqtt_init_ready.set()

                # if mqtt handler has been initialized set logging and _mqtthdlr 
                if self._thread_mqtthdlr and self._thread_mqtthdlr._mqttc:
                    _mqtthdlr = self._thread_mqtthdlr
                    # Initialize the logging handler with the MQTTclass class 
                    logging.Handler.__init__( _mqtthdlr )
                    logger.addHandler( _mqtthdlr )

                    # put _mqtthdlr reference and send to logger
                    logger._mqtthdlr = _mqtthdlr
                    logger.send = _mqtthdlr.send

                    # provide progress 
                    logger.progressStart = _mqtthdlr.progress_start
                    logger.progress = _mqtthdlr.progress_run
                    logger.progressReady = _mqtthdlr.progress_ready

                    # when everything is ready put reference to _mqtthdlr 
                    self._mqtthdlr = _mqtthdlr

                    # remember logger name 
                    self.logger_name = logger.name

            else:
                # logger is available put reference to _mqtthdlr 
                self._mqtthdlr = mqtthdlr
                # remember logger name 
                self.logger_name = logger.name

            # set level if specified 
            if level:
                logger.setLevel( level )

    def mqttGetHandler(self):
        """Specifies the mqtt handler when initialized. 

        Returns
        -------
        mqtthdlr.

        """
        mqtthdlr = None
        # If there is no logger in self._mqtthdlr, use logging to determine it 
        if self._mqtthdlr:
            mqtthdlr = self._mqtthdlr
        else:
            logger = logging.getLogger( "MQTT" )
            if hasattr(logger, '_mqtthdlr'):
                mqtthdlr = logger._mqtthdlr
        return mqtthdlr

    def mqttCleanup( self ):
        """shutdown mqtt and remove the logger. 

        """
        if self._mqtthdlr:
            # shutdown mqtt 
            self._mqtthdlr.shutdown()
            logger = logging.getLogger( "MQTT" )
            # remove connection to _mqtthdlr in logger 
            del( logger._mqtthdlr )

            for h in logger.handlers:
                logger.removeHandler(h)

            self._mqtthdlr = None

# ----  

def dict_merge(dct, merge_dct):
    """Recursive dict merge.

    The ``merge_dct`` is merged into ``dct``.
    Return a copy of the dct and leave the original untouched.

    Args:
        dct (dict): onto which the merge is executed
        merge_dct (dict): dct merged into dcts

    Returns:
        dict: updated dict
    """
    
    dct = dct.copy()
    merge( dct, merge_dct )
    return dct
    