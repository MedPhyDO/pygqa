# -*- coding: utf-8 -*-
"""

mqtt
====

Klasse für eine MQTT Anbindung

Benötigt psutil::
    
    sudo pip install psutil

Aufruf::
    
    mqtt = MQTTclass( { 
        "host" : "localhost",
        "port": 1883,
        "username": "",
        "password": "",
        "basetopic": "",
        "logging": False
    })

logging::
    
    mqtt.logging = True|False(default)
    mqtt.init()

mqtt Topics:
    
- Befehle empfangen - ``<MQTT_BASE>/cmnd/``
- Ergebnisse melden - ``<MQTT_BASE>/stat/``
- Eine eigene Status Meldung zurückgeben - ``<MQTT_BASE>/cmnd/status``
- Abfragen ob ein prosess im system läuft: ``<MQTT_BASE>/cmnd/process`` mit payload: ``process Name``
            
MQTT beim starten::

    {"topic":"<basetopic>/stat/status","payload":{
         "mode": "running", 
         "name": "<main name>", 
         "path": "<path to main>", 
         "pid": 17964
     },"qos":0,"retain":false,"_msgid":"6db09cdf.064324"}

MQTT beim stoppen::
    
    {"topic":"<basetopic>/stat/status","payload":{
          "mode": "stopped-lastwill", 
          "name": "<main name>"
    },"qos":0,"retain":false,"_msgid":"c2c88bb5.57b208"}


qos
---
* 0 - at most once (die Nachricht wird einmal gesendet und kommt bei Verbindungsunterbrechung möglicherweise nicht an)
* 1 - at least once (die Nachricht wird so lange gesendet, bis der Empfang bestätigt wird, und kann beim Empfänger mehrfach ankommen) 
* 2 - exactly once (hierbei wird sichergestellt, dass die Nachricht auch bei Verbindungsunterbrechung genau einmal ankommt)

retain
------
mit dem Retain-Flag kann der Server angewiesen werden, die Nachricht zu diesem Topic zwischenzuspeichern.

Clients, die diesen Topic neu abonnieren, bekommen als erstes die zwischengespeicherte Nachricht zugestellt. 

Links
-----    

- http://www.hivemq.com/blog/mqtt-client-library-paho-python

"""

__author__ = "R. Bauer"
__copyright__ = "MedPhyDO - Machbarkeitsstudien des Instituts für Medizinische Strahlenphysik und Strahlenschutz am Klinikum Dortmund im Rahmen von Bachelor und Masterarbeiten an der TU-Dortmund / FH-Dortmund"
__credits__ = ["R. Bauer", "K.Loot"]
__license__ = "MIT"
__version__ = "0.1.0"
__status__ = "Prototype"

import psutil
import json
import sys
import os.path as osp
import os
import time
import logging

import paho.mqtt.client as mqtt
from blinker import signal

class MQTTclass( logging.Handler ):
    """Klasse für eine MQTT Anbindung.
    
    Attributes
    ----------
    server : str, optional
        Server settings. The default is "localhost".
    port : int, optional
        Server settings. The default is 1883.
    username : str, optional
        Server settings. The default is "".
    password : str, optional
        Server settings. The default is "".
    defaults : dict
        - basetopic : str, optional
            Immer diesen topic voranstellen. The default is "".  
        - status : dict
            status Informationen   
        - lastwill: dict    
            status informationen über connected/
        - connected: dict   
            status informationen
        - shutdown: dict
            status informationen
        - cmnd: str
            The default is "cmnd"
        - stat: str
            The default is "stat"
    logger: 
        The default is None
    logging: bool
        The default is False
    _progress: dict
        Bearbeitungsfortschritt ausgeben. The default is {}
    _mqttc: mqtt.Client()
        Der mqtt.Client() The default is None
    signal: blinker.signal
        Signalisierung über blinker
        
    """
    
    def __init__(self, config:dict={}, defaults:dict={}):
        """MQTT Verbindung initialisieren.
        
        Parameters
        ----------
        config: dict
            - server : str, optional
                Server settings. The default is "localhost".
            - port : int, optional
                Server settings. The default is 1883.
            - username : str, optional
                Server settings. The default is "".
            - password : str, optional
                Server settings. The default is "".
            - basetopic: str
                Immer diesen topic voranstellen. The default is "".
                
        defaults: dict
            Überschreibt oder ändert self.defaults
            - basetopic: str
                Immer diesen topic voranstellen. The default is "".    
            - status: dict
                Status Meldung 
            - connected: dict
            - lastwill: dict
            - shutdown: dict
            - cmnd: str
            - stat: str
            
        Returns
        -------
        None.

        """
        self.config = {
            "host" : "localhost",
            "port": 1883,
            "webclient_port": 9001,
            "username": "",
            "password": "",
            "basetopic": "",
            "logging": False
        }
        self.config.update( config )
        
        self.defaults = {
            "basetopic" : self.config["basetopic"],
            "status" : {
                "mode": "running",
                "name" : osp.basename( sys.argv[0] ),
                "path" : osp.abspath( sys.argv[0] ),
                "pid" : os.getpid()
                
            }, 
            "connected" : {
                "mode": "started",
                "name" : osp.basename( sys.argv[0] ),
                "path" : osp.abspath( sys.argv[0] ),
                "pid" : os.getpid()
            } ,
            "lastwill": {
                "mode": "stopped-lastwill",
                "name" : osp.basename( sys.argv[0] )
            }, 
            "shutdown": {
                "mode": "stopped-shutdown",
                "name" : osp.basename( sys.argv[0] )
            } ,
            "cmnd" : "cmnd",
            "stat" : "stat" 
        }
        self.defaults.update( defaults )
        
        self.logging = self.config["logging"]
    
        self._progress = {}
        
        self._mqttc = None
                    
        # signal bereitstellen
        self.signal = signal('mqtt')
        
        self.signalStartup = signal('mqtt-startup')
        # mqtt starten
        self.startup()
       
    # 
    #
    def info(self, msg):
        """Info über looging oder print.
        
        logging.info nur wenn self.logging=True
        
        Wenn MQTT einen handler hat dann dorthin sonst auf die console

        Parameters
        ----------
        msg : str
            Auszugebende Nachricht

        Returns
        -------
        None.

        """
        if self.logging == True:
            logger = logging.getLogger( "MQTT" ) 
            if logger.hasHandlers():
                logger.info( msg )
            else:
                print("### MQTT INFO", msg)
            
    def warning(self, msg):
        """Warnung über looging oder print.
        
        logging.warning nur wenn self.logging=True
        
        Wenn MQTT handler hat dann dorthin sonst auf die console
       
        Parameters
        ----------
        msg : str
            Auszugebende Nachricht

        Returns
        -------
        None.

        """
        if self.logging == True:
            logger = logging.getLogger( "MQTT" ) 
            if logger.hasHandlers():
                logger.warning( msg )
            else:
                print("### MQTT WARNING", msg)
    
    def error(self, msg):
        """logging.error wenn logger angegeben dorthin sonst auf die console.
        
        Parameters
        ----------
        msg : str
            Auszugebende Nachricht

        Returns
        -------
        None.

        """
        logger = logging.getLogger( "MQTT" ) 
        if logger.hasHandlers():
            logger.error( msg )
        else:
            print("### MQTT ERROR", msg)
   
    def startup( self, forever=False ):
        """Startet den mqtt Client.
        
        Parameters
        ----------
        forever : bool, optional
            Automatisch wieder starten loop_forever statt loop_start. The default is False.

        Returns
        -------
        None.

        """
        # nur einmal durchführen
        if self._mqttc : # pragma: no cover
            return
        
        # Client bereitstellen
        self._mqttc = mqtt.Client()
                
        # Assign event callbacks
        self._mqttc.on_connect = self.onConnect
        self._mqttc.on_message = self.onMessage

        #self._mqttc.on_publish = self.onPublish
        #self._mqttc.on_subscribe = self.onSubscribe

        # Uncomment to enable debug messages
        # self._mqttc.on_log = self.onLog

        # onDisconnect
        # self._mqttc.on_disconnect = self.onDisconnect

        # user und passwort setzen 
        self._mqttc.username_pw_set( self.config["username"], self.config["password"])

        # Set the Last Will and Testament (LWT) *before* connecting /system/lastwil
        self._mqttc.will_set( 
                "{basetopic}/{stat}/status".format( **self.defaults ), 
                payload=json.dumps(self.defaults["lastwill"] ), 
                qos=0, 
                retain=True
        )
        
        # Connect 
        try:
            self._mqttc.connect(self.config["host"], self.config["port"], 60)
        except Exception as e:
            self.error("mqtt.init Error connecting to {}:{}: {}".format( self.config["host"], self.config["port"], e ) )
            self._mqttc = None
    
        if self._mqttc:
            # status nachricht absetzen   
            self.doStatus( )
            # loop starten
            if forever: # pragma: no cover
                self._mqttc.loop_forever()
            else:
                self._mqttc.loop_start()
            
            
    def shutdown(self):
        """MQTT Client stoppen.
        
        Stoppt den MQTT Client und schließt die Verbindung
        """
        if self._mqttc:
            # connected 0 senden
            self.info("mqtt.Stopping and publish: {basetopic}/{stat}/connected : 0".format( **self.defaults ) )
            self._mqttc.publish( "{basetopic}/{stat}/connected".format( **self.defaults ), payload=json.dumps(self.defaults["shutdown"] ),  qos=0, retain=True)
            # mqttc loop beenden
            try:
                self._mqttc.loop_stop()
                self._mqttc.disconnect()
            except Exception as e: # pragma: no cover
                self.error("mqtt.shutdown error: {}".format( str(e) ) )
                
            self._mqttc = None
                
        
    def decodeMsgObj(self, msgObj, basetopicReplace=True ):
        """Payload des msgObj wenn möglich nach string umwandeln.
        
        wenn json im string dann nach dict umwandeln 
        
        Parameters
        ----------
        msg: MQTTMessage
            umzuwandelndes message Object
        basetopicReplace: bool
            <basetopic> aus topic entfernen    
        
        Returns
        -------
        result: dict
        
            .. code::
                
            {
                "topic"
                "payload"
                "_decodeMsgObj" # nur wenn Fehler aufgetaucht sind
            }
            
        """
        result = {
            "payload" : ""
        }
        #print( "# decodeMsgObj", msgObj.topic, type( msgObj.payload ), msgObj.payload )
        if isinstance(msgObj, (dict)):
            result["topic"] = msgObj["topic"] 
            result["payload"] = msgObj["payload"] 
        else:
            result = {
                "topic" : msgObj.topic,
                "payload" : msgObj.payload
            }
        
        if basetopicReplace:
            result["topic"] = result["topic"].replace( "{}/".format( self.defaults["basetopic"] ), "" )  
        
        if type( result["payload"] ) == bytes:
            try:
                result["payload"] = result["payload"].decode('utf-8')
            except Exception: # pragma: no cover
                result["_decodeMsgObj"] = "byte.decode error"
          
        if type( result["payload"] ) == str and len(result["payload"]) > 0 and result["payload"][0] == "{":
            try:
                result["payload"] = json.loads( result["payload"] )
            except ValueError: # pragma: no cover
                result["_decodeMsgObj"] = "json.loads error"
        
        return result
    
    # Nachricht senden
    #
    def publish(self, msg:dict=None, qos=0, retain=False):
        """Stellt einen Wrapper zu self._mqttc.publish bereit.
        
        Intern wird immer basetopic vor topic gesetzt
        
        Parameters
        ----------
        msg: dict
            Dict mit::
                
                - topic : str
                - payload : mixed
                
        qos : int, optional
            Quality of Service. The default is 0.
        retain : bool, optional
            Retain-Flag. The default is False.
        
        Returns
        -------
        bool
            True wenn ein publish möglich war
        
        """
        if not isinstance(msg, (dict)) or not "topic" in msg:
            return False
            
        if not "payload" in msg:
            msg["payload"] = ""
        
        if isinstance(msg["payload"], (dict)):
            try:
                msg["payload"] = json.dumps( msg["payload"] )
            except Exception:  # pragma: no cover
                msg["payload"] = ""
        
        if not isinstance(msg["payload"], (str, bytearray, int, float)):
            msg["payload"] = ""
 
        if self._mqttc:
            self._mqttc.publish( "{}/{}".format( self.defaults["basetopic"], msg["topic"] ) , payload=msg["payload"], qos=qos, retain=retain)
        return True

    def send( self, topic:str=None, payload=None, qos=0, retain=False ):
        """Wie publish aber mit seperater topic und payload Angabe.
        
        Parameters
        ----------
        topic : str, optional
            Der zu sendende Topic. The default is None.
        payload : TYPE, optional
            Nachrichteninhalt. The default is None.
        qos : int, optional
            Quality of Service. The default is 0.
        retain : bool, optional
            Retain-Flag. The default is False.

        Returns
        -------
        None.

        """
        if not topic:
            return
        msg = {
            "topic" : topic.replace(" ", "_"),
            "payload" : payload
        }
        self.publish( msg )
        
    # --- event callbacks
    #
    #
    def onConnect(self, client, userdata, flags, rc):
        """Nach einem erfolgreichem connect des Client ``<basetopic>/<cmnd>`` abbonieren.
        
        .. note::
            
            If you want the client to subscribe to multiple topics then you can put them in a list of tuples.
            Example::
            
                client.subscribe([(‘topicName1’, 1),(‘topicName2’, 1)])
                
            The format of the tuple is [(Topic Name, QoS Level)]
            
        Parameters
        ----------
        client:
            The Client instance that is calling the callback
        userdata:
            user data of any type and can be set when creating a new client instance
        flags : dict
            flags is a dict that contains response flags from the broker
        rc: int
            The value of rc determines success or not
            
            .. code::
                
                0: Connection successful
                1: Connection refused – incorrect protocol version
                2: Connection refused – invalid client identifier
                3: Connection refused – server unavailable
                4: Connection refused – bad username or password
                5: Connection refused – not authorised
                6-255: Currently unused.
            
        """
        if  rc != 0: # pragma: no cover
            self.info("mqtt.Connected with result code: " + str(rc))
        else:
            self.info("mqtt.Connected: {}:{}".format( self.config["host"], self.config["port"] ) )
            
            # Subscribe to <basetopic>/<cmnd> and all sub topics
            client.subscribe( "{basetopic}/{cmnd}/#".format( **self.defaults ) )
            # nach dem starten den eigenen status abrufen
            #self._mqttc.publish( "{basetopic}/{cmnd}/#".format( **self.defaults ), payload="0" )
        self.signalStartup.send( { "onConnect":  rc } )
                         
    def onMessage(self, client, userdata, msgObj:mqtt.MQTTMessage ):
        """Eingehende Nachrichten verarbeiten.
        
        Parameters
        ----------
        client: 
            the client instance for this callback
        userdata:   
            the private user data as set in Client() or userdata_set()
            
        msgObj: mqtt.MQTTMessage(object)
            
        """  
        #print("mqtt.onMessage", msgObj.topic )
              
        # topics splitten und basetopic entfernen
        topics = msgObj.topic.split("/")
        #print("mqtt.onMessage topics:", topics )
        base = topics.pop(0)
        #print("mqtt.onMessage base:", base, self.defaults["basetopic"] )
        
        # kann eigentlich nicht passieren da subscribe zwei Elemente hat
        if not base == self.defaults["basetopic"] and len(topics) <= 2: # pragma: no cover
            self.warning("onMessage:mqtt.Topic not allowed: {}".format( msgObj.topic ) )
            #print( "mqtt.warning", msgObj.topic )
            return
        
        
        # cmnd entfernen
        cmd = topics.pop(0)
        
        # und prüfen
        if cmd == self.defaults["cmnd"]:
            # ggf payload json string umwandeln
          
            # den neuen Topic zusammenstellen            
            topic = "/".join( topics )

            
            if topic == "status": #pragma: no cover
                self.doStatus( )
            elif topic == "process": #pragma: no cover
                self.doProcess( msgObj )
            else:
                self.warning("mqtt.Topic {} keine do Funktion".format( topic ) )
                self.doSignal( msgObj )
             
                
        return
 
    # ---- Bearbeitungsfortschritt 
    # 
    # 
    def progress_start( self, topic:str=None, payload={}  ):
        """Startet über mqtt einen Bearbeitungsfortschritt.
        
        setzt in self.progress den übergebenen payload 
        mit mind. count und index
        
        Parameters
        ----------
        topic: str
            der in ``{stat}/progress/{topic}/start`` eingefügte topic
            
        payload: dict
            zusätzliche payload Angaben - default: ``{"maxprogress" : 100, "progress" : 0}``
            
        """  
        self._progress = {
            "maxprogress" : 100,
            "progress" : 0
        }
        self._progress.update( payload ) 
                
        msg = {
            "topic" : "{stat}/progress/{topic}/start".format( topic=topic, **self.defaults ),
            "payload" : self._progress
        }
        self.publish( msg )
        
        #print( "progress_start", msg )
        
    def progress_run( self, topic:str=None, progress=0, payload={}  ):
        """Sendet über mqtt den Bearbeitungsfortschritt.
        
        Parameters
        ----------
        topic: str
            der in ``{stat}/progress/{topic}/run`` eingefügte topic  
            
        progress: int|float
            der aktuelle Bearbeitungsfortschritt    
        
        payload: dict
            zusätzliche payload Angaben
             
        """
        self._progress.update( payload )
        self._progress["progress"] = progress
        
        msg = {
            "topic" : "{stat}/progress/{topic}/run".format( topic=topic, **self.defaults ),
            "payload" : self._progress
        }
        self.publish( msg )
        
        
        #print( "progress_run", msg )
        
    def progress_ready( self, topic:str=None, payload={} ):   
        """Beendet über den Bearbeitungsfortschritt.
        
        Setzt progress auf maxprogress
        
        Parameters
        ----------
        topic: str
            der in ``{stat}/progress/{topic}/ready`` eingefügte topic 
            
        payload: dict
            zusätzliche payload Angaben      
            
        """
        self._progress.update( payload ) 
        self._progress["progress"] = self._progress["maxprogress"]
        msg = {
            "topic" : "{stat}/progress/{topic}/ready".format( topic=topic, **self.defaults ),
            "payload" : self._progress
        }
        self.publish( msg )
        self._progress = {}   
        
        #print( "progress_ready", msg )
        
        
    # --- durch onMessage aufgerufene methoden
    #
    # 
    #
    def doSignal(self, msgObj:dict=None):
        """Message über signal weiterleiten, <MQTT_BASE> wird dabei aus topic entfernt.
        
        .. code::
            
            <MQTT_BASE>/stat/#
        
        Parameters
        ----------
        msg : dict, optional
            dict mit payload. The default is None.
            .. code::
                
                - topic: <MQTT_BASE>/stat/#
                - payload: beliebig

        Returns
        -------
        None.

        """
        self.signal.send( self.decodeMsgObj( msgObj, basetopicReplace = True ) )

            
    def doStatus(self, msg:dict=None):
        """Status Information senden.
        
        .. code::
            
            <MQTT_BASE>/stat/status 

        Parameters
        ----------
        msg : dict, optional
            dict mit payload. The default is None.
            .. code::
            
                - topic: <MQTT_BASE>/stat/status 
                - payload: entweder wie angegeben oder self.defaults["status"]
           
        Returns
        -------
        None.

        """
        # ohne msg oder pyload defaults verwenden
        if not msg:
            msg = {}
        if not "payload" in msg:
            msg["payload"] = self.defaults["status"]
            
        msg["topic"] = self.defaults["stat"] + "/status"

        self.info("mqtt.doStatus - {} : {}".format( msg["topic"], str(1) ) )     
        self.publish( msg, qos=0, retain=False)
        
        self.doSignal( msg )
        
    def doProcess(self, msgObj=None): #pragma: no cover
        """Den in msg.payload angegebenen process abfragen.
        
        Dessen pid zurückgeben 0 wenn nicht laufend
       
        .. code::
            
            <MQTT_BASE>/stat/process { "<process>": 0 }
            <MQTT_BASE>/stat/process { "<process>": <pid> }
        
        Parameters
        ----------
        msgObj : dict, optional
            Das Nachrichten Object mit payload. The default is None.

        Returns
        -------
        None.

        """
        if not msgObj:
            return
        
        name = msgObj.payload.decode('utf-8')
        pl = { }
        
        pl[ name ] = 0;
        
        for p in psutil.process_iter(attrs=['pid', 'name']):
            if name == p.info['name']:
                pl[ name ] = p.info['pid']
                break;
            
        topic = self.defaults["stat"] + "/process"
        
        # pl als json senden
        self.info("mqtt.doProcess - {} : {}".format( topic, json.dumps( pl ) ) ) 
        
        msg = {"topic": topic, "payload":pl }
    
        self.publish( msg , qos=0, retain=False)
        
        self.doSignal( msg )

    # --- für die Nutzung als logger
    #
    level = logging.NOTSET

    def emit(self, record):
        """Die Funktion emit muss für die Verwendung als logger vorhanden sein.
        
        Do whatever it takes to actually log the specified logging record.

        This version is intended to be implemented by subclasses and so
        raises a NotImplementedError.
        
        https://docs.python.org/3/library/logging.html#logging.LogRecord
        """
        #formatter = "%(asctime)s — %(name)s — %(levelname)s — %(funcName)s:%(lineno)d — %(message)s"
        
        '''
        '<LogRecord: %s, %s, %s, %s, "%s">'%(self.name, self.levelno,
            self.pathname, self.lineno, self.msg)
        '''
        
        ts = time.strftime("%Y%m%d %H:%M:%S", time.localtime(time.time()) )
   
        # gibt es einen MQTT Handler dann über ihn loggen
        if self._mqttc:
            msg = {
                "topic" : "logging/" + record.levelname,
                "payload" : {
                    "time": ts,
                    "name" : record.name,
                    "level" : record.levelname,
                    "pathname" : record.pathname,
                    "filename" : record.filename,
                    "module" : record.module,
                    "funcName": record.funcName,
                    "lineno": record.lineno,
                    "exc_info" : record.exc_info,
                    "msg" :  record.msg,
                    "args" :  record.args,
                }
            }
            try:
                self.publish( msg )
            except:  # pragma: no cover
                print( "logging.emit: Error bei publish", msg )
                
