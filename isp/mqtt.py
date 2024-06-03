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


CHANGELOG
=========

0.2.0 / 2024-04-18
------------------
- use base class logging.py - loggingHandlerClass 

0.1.0 / 2021-01-16
------------------
- First Release

"""

__author__ = "R. Bauer"
__copyright__ = "MedPhyDO - Machbarkeitsstudien des Instituts für Medizinische Strahlenphysik und Strahlenschutz am Klinikum Dortmund im Rahmen von Bachelor und Masterarbeiten an der TU-Dortmund / FH-Dortmund"
__credits__ = ["R. Bauer", "K.Loot"]
__license__ = "MIT"
__version__ = "0.1.0"
__status__ = "Prototype"

import json
import sys
import os.path as osp
import os

import paho.mqtt.client as mqtt
from blinker import signal

from isp.logging import loggingHandlerClass

class MQTTclass( loggingHandlerClass ):
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
    _handler: mqtt.Client()
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
            - logLevel: int
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
        
        _config = {
            "host" : "localhost",
            "port": 1883,
            "webclient_port": 9001,
            "username": "",
            "password": "",
            "basetopic": "",
            "logging": False
        } | config

        _defaults = {
            "handlerName" : "MQTT",
            "basetopic" : _config["basetopic"],
            "lastwill": {
                "mode": "stopped-lastwill",
                "name" : osp.basename( sys.argv[0] )
            }
        } | defaults
        
        loggingHandlerClass.__init__( self, _config, _defaults )
        # signal bereitstellen
        self.signal = signal('mqtt')

        self.signalStartup = signal('mqtt-startup')


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
        if self._handler : # pragma: no cover
            return

        # Client bereitstellen
        self._handler = mqtt.Client()

        # Assign event callbacks
        self._handler.on_connect = self.onConnect
        self._handler.on_message = self.onMessage

        #self._handler.on_publish = self.onPublish
        #self._handler.on_subscribe = self.onSubscribe

        # Uncomment to enable debug messages
        # self._handler.on_log = self.onLog

        # onDisconnect
        self._handler.on_disconnect = self.onDisconnect

        # user und passwort setzen
        self._handler.username_pw_set( self.config["username"], self.config["password"])

        # Set the Last Will and Testament (LWT) *before* connecting /system/lastwil
        self._handler.will_set(
            "{basetopic}/{stat}/status".format( **self.defaults ),
            payload=json.dumps(self.defaults["lastwill"] ),
            qos=0,
            retain=False
        )

        # Connect
        try:
            self._handler.connect(self.config["host"], self.config["port"], 60)
        except Exception as e:
            self.error("mqtt.init Error connecting to {}:{}: {}".format( self.config["host"], self.config["port"], e ) )
            self._handler = None

        if self._handler:
            # status nachricht absetzen
            # self.doStatus( )
            #print( "MQTT", "startup" )
            # loop starten
            if forever: # pragma: no cover
                self._handler.loop_forever()
            else:
                self._handler.loop_start()


    def shutdown(self):
        """MQTT Client stoppen.

        Stoppt den MQTT Client und schließt die Verbindung
        """
        #print( "MQTT", "shutdown" )
        if self._handler:
            # connected 0 senden
            self.info("mqtt.Stopping and publish: {basetopic}/{stat}/connected : 0".format( **self.defaults ) )
            self._handler.publish( 
                "{basetopic}/{stat}/connected".format( **self.defaults ), 
                payload=json.dumps(self.defaults["shutdown"] ),  
                qos=0, 
                retain=False
            )
            # mqttc loop beenden
            try:
                self._handler.loop_stop()
                self._handler.disconnect()
            except Exception as e: # pragma: no cover
                self.error("mqtt.shutdown error: {}".format( str(e) ) )
            
            self._handler = None

    # --- Nachricht senden
    #
    def doPublish(self, msg:dict=None, qos=0, retain=False):
        """publish message with handler

        msg: dict
            Dict mit::
                - topic : str
                - payload : mixed
        qos : int, optional - used with mqtt
            Quality of Service. The default is 0.
        retain : bool, optional - used with mqtt
            Retain-Flag. The default is False.
        """
        
        if self._handler:
            topic = "{}/{}".format( self.defaults["basetopic"], msg["topic"] )
            # print( "MQTT-doPublish", topic, msg)
            self._handler.publish( 
                topic, 
                payload=msg["payload"], 
                qos=qos, 
                retain=retain
            )
        return True

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
            #self._handler.publish( "{basetopic}/{cmnd}/#".format( **self.defaults ), payload="0" )
        self.signalStartup.send( { "onConnect":  rc } )

        self.doStatus( )

    def _onDisconnect(self, client, userdata, rc):
        #print( "MQTT", "onDisconnect" )
        pass

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
        
        # msgObj prüfen und baseTopic entfernen
        msg = self.decodeMsgObj( msgObj )
        # print("MQTT:onMessage", msg )
        self.doMessage( msg )
      
