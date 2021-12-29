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

0.1.0 / 2021-01-16
------------------
- First Release

'''

__author__ = "R. Bauer"
__copyright__ = "MedPhyDO - Machbarkeitsstudien des Instituts für Medizinische Strahlenphysik und Strahlenschutz am Klinikum Dortmund im Rahmen von Bachelor und Masterarbeiten an der TU-Dortmund / FH-Dortmund"
__credits__ = ["R. Bauer", "K.Loot"]
__license__ = "MIT"
__version__ = "0.1.0"
__status__ = "Prototype"

import sys
import json
import os.path as osp
from dotmap import DotMap

from jinja2 import Environment, FileSystemLoader

from datetime import datetime
import glob
import re
import threading
import os

import logging

from isp.mqtt import MQTTclass

default_config = {
    "server" : {
        "webserver" : {
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
            "checkNetarea": True,
            "SECRET_KEY": os.urandom(16)
        },
        "api": {
            "prefix" : "/api",
            "models" : [ ],
            "DBADMIN": False,
            "COVERAGE" : False
        }
    },
    "use_as_variables":{
        "webserver" : "server.webserver",
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
            if osp.isfile( filename ):
                # zuerst die normale config Datei einlesen
                with open( filename, 'r') as f:
                    try:
                        config = json.load( f )
                        self._config = dict_merge(self._config, DotMap( config ) )
                        self._configs.append( osp.basename( filename ) )
                    except:
                        # Fehler auch hier anzeigen, da noch kein logger bereitsteht
                        self._loadErrors.append( filename )
                        self._configs.append( osp.basename( filename ) + " - ERROR" )
                        print( "CONFIG: Fehler bei json.load", filename )
                        pass

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
        variables["serverHost"] = "{}:{}".format(
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
        """Konfiguration auslesen.

        ohne Angaben wird die komplette Konfiguration zurückgegeben

        Parameters
        ----------
        name : str|list
            Bezeichner dessen Inhalt ausgelesen wird . operator für die tiefe
        default :
            Rückgabe wenn name nicht gefunden wurde
        replaceVariables: bool
            Bei strings variables Angaben ersetzen. Default is False


        """
        # ohne Angabe komplette config zurückgegeben
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
                # erste ebene versuchen
                val = self._config.get( key )
                # undefined : immer DotMap verwenden
                if not val:
                    self._config[ key ] = DotMap()
            else:
                if isinstance( val, DotMap):
                    try:
                        val = val.get(key, default)
                    except Exception as e: # pragma: no cover
                        # kommt vor wenn ein nicht vorhandener sub key gesucht wird, a.b = 12 aber a.b.c gesucht wird
                        print("CONFIG: config.get error bei get", keys, key, type(val), e )
                        val = default
                        pass

        if val == None:
            val = default

        # wenn gewünscht variables ersetzen
        if isinstance(val, str) and replaceVariables==True:
            val = self.render_template( val )

        return val

    def set(self, setkeys:str=None, value=None):
        """Einen Wert in der Konfiguration ablegen.

        Parameters
        ----------
        setkeys : str|list
            Bezeichner dessen Inhalt gesetzt wird . operator für die tiefe
        value :
            Zu setzener Inhalt

        """
        # Startpunkt ist die config selbst
        here = self._config

        # setkeys in list umwandeln
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
        """Initialisiert den root logger

        Parameters
        ----------
        level : int, optional
            Logging Level. The default is None.

        Returns
        -------
        None.

        """
        baselogger = logging.getLogger(  )

        # level wenn angegeben neu setzen
        if level:
            baselogger.setLevel( level  )

    # ---- Jinja Environment
    #
    def jinjaEnv(self):
        """Jinja Environment erzeugen.

        Weitere Extensions hinzufügen:

        - https://github.com/jpsca/jinja-markdown

        Returns
        -------
        env: Environment

        """
        # template Ort bestimmen,
        # da das templatesystem noch nicht bereit steht BASE_DIR einfach ersetzen
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

        return env

    def render_template( self, tpl:str="", variables:dict=None, deep_replace:bool=False ):
        """Ersetzt in tmp alle variablen aus variables.

        Wird variables nicht angegeben wird _config["variables"] verwendet

        Parameters
        ----------
        tpl : str, optional
            Jinja template string. The default is "".
        variables : dict, optional
            Zu ersetzende variables Angaben. The default is _config["variables"].
        deep_replace: bool, optional
            Führt render zweimal aus um in variables liegende Anweisungen auch zu ersetzen. The default is False

        Returns
        -------
        None.

        """
        if not variables:
            variables = self._config["variables"]
        # immer now mit der aktuellen Zeit mitgeben
        variables["now"] = datetime.now()
        # je nach deep_replace einfacher Durchlauf oder mehrere
        n = range(1)
        if deep_replace:
            n = range(3)

        for i in n:
            _tpl = self._env.from_string( tpl )
            try:
                tpl = _tpl.render( **variables )
            except Exception as e: # pragma: no cover
                print("CONFIG: config.render_template error bei _tpl.render", e)
        return tpl


    # ---- MQTT Logging
    #
    def mqttInitLogger( self, level:int=None, cleanup:bool=False  ):
        """Logging über MQTT einschalten.

        Parameters
        ----------
        level : int, optional
            NOTSET=0, DEBUG=10, INFO=20, WARN=30, ERROR=40, and CRITICAL=50. Default: NOTSET
        cleanup : bool, optional
            MQTT Cleanup vor dem initialisieren durchführen. Default = False

        Returns
        -------
        None.

        """
        # zuerst root logger
        self.logger_name = "root"

        # wenn gewünscht handler neu aufsetzen
        if cleanup:
            self.mqttCleanup()

        if self._config.server.mqtt:
            # MQTT Logger seltezn
            logger = logging.getLogger( "MQTT" )

            # Handler auf MQTT
            mqtthdlr = self.mqttGetHandler( )

            if not mqtthdlr:

                #
                # wenn hier was geändert wird muss der kernel neu gestartet bzw. mqttCleanup aufgerufen werden
                #

                mqtt_init_ready = threading.Event()

                self._thread_mqtthdlr = None

                def signalStartup( msg ):
                    #print( "MQTT signalStartup", msg)
                    #print( time.strftime("%Y%m%d %H:%M:%S", time.localtime(time.time()) ) )
                    mqtt_init_ready.set()

                def startMQTTclass():
                    """MQTTclass über threading starten und auf signalStartup warten.

                    Returns
                    -------
                    None.

                    """
                    self._thread_mqtthdlr = MQTTclass( self._config.server.mqtt.toDict() )
                    # auf eine signalisierung
                    self._thread_mqtthdlr.signalStartup.connect( signalStartup )

                # Als Thread aufrufen, über mq.get() wird die Rückgabe von  _retrieve abgerufen
                thread = threading.Thread( target=startMQTTclass )
                thread.start()

                # max 2 sekunden oder auf mqtt_init_ready signalStartup warten
                while not mqtt_init_ready.wait( timeout=2 ):
                    mqtt_init_ready.set()

                # wenn der mqtt handler initialisiert wurde logging und _mqtthdlr setzen
                if self._thread_mqtthdlr and self._thread_mqtthdlr._mqttc:
                    _mqtthdlr = self._thread_mqtthdlr
                    # logging Handler mit der MQTTclass Klasse initialisieren
                    logging.Handler.__init__( _mqtthdlr )
                    logger.addHandler( _mqtthdlr )

                    # einen Verweis auf _mqtthdlr sowie send bereitstellen
                    logger._mqtthdlr = _mqtthdlr
                    logger.send = _mqtthdlr.send

                    # progress bereitstellen
                    logger.progressStart = _mqtthdlr.progress_start
                    logger.progress = _mqtthdlr.progress_run
                    logger.progressReady = _mqtthdlr.progress_ready

                    # wenn alles fertig ist _mqtthdlr in self merken
                    self._mqtthdlr = _mqtthdlr

                    # logger name merken
                    self.logger_name = logger.name

            else:
                # logger ist vorhanden verweis wieder in _mqtthdlr ablegen
                self._mqtthdlr = mqtthdlr
                # logger name merken
                self.logger_name = logger.name

            # level wenn angegeben neu setzen
            if level:
                logger.setLevel( level )


    def mqttGetHandler(self):
        """Bestimmt den mqtt Handler wenn er initialisiert wurde.

        Returns
        -------
        mqtthdlr.

        """
        mqtthdlr = None
        # gibt es noch keinen logger in self._mqtthdlr, dann über logging bestimmen
        if self._mqtthdlr:
            mqtthdlr = self._mqtthdlr
        else:
            logger = logging.getLogger( "MQTT" )
            if hasattr(logger, '_mqtthdlr'):
                mqtthdlr = logger._mqtthdlr
        # Handler zurückgeben
        return mqtthdlr


    def mqttCleanup( self ):
        """Schließt mqtt und entfernt den logger.

        """
        if self._mqtthdlr:
            # mqtt beenden
            self._mqtthdlr.shutdown()
            #print( "config.cleanup _mqtthdlr" )
            logger = logging.getLogger( "MQTT" )
            # verbindung zu _mqtthdlr im logger entfernen
            del( logger._mqtthdlr )

            for h in logger.handlers:
                logger.removeHandler(h)

            self._mqtthdlr = None

# ----  Hilfsfunktionen
import collections
def dict_merge(dct, merge_dct, add_keys=True):
    """Recursive dict merge.

    Inspired by ``dict.update()``, instead of
    updating only top-level keys, dict_merge recurses down into dicts nested
    to an arbitrary depth, updating keys. The ``merge_dct`` is merged into
    ``dct``.

    This version will return a copy of the dictionary and leave the original
    arguments untouched.

    The optional argument ``add_keys``, determines whether keys which are
    present in ``merge_dict`` but not ``dct`` should be included in the
    new dict.

    https://gist.github.com/angstwad/bf22d1822c38a92ec0a9

    Args:
        dct (dict): onto which the merge is executed
        merge_dct (dict): dct merged into dct
        add_keys (bool): whether to add new keys

    Returns:
        dict: updated dict
    """
    dct = dct.copy()
    if not add_keys:
        merge_dct = {
            k: merge_dct[k]
            for k in set(dct).intersection(set(merge_dct))
        }

    for k, v in merge_dct.items():
        if isinstance(dct.get(k), dict) and isinstance(v, collections.Mapping):
            dct[k] = dict_merge(dct[k], v, add_keys=add_keys)
        else:
            dct[k] = v
    return dct

