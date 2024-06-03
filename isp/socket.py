'''

- flask_sockets
    veraltet 
- flaskws
    veraltet
- flask_socketio
    spezielles protokoll benötigt socket.io.js 
    einfach zu implementieren
    - https://socket.io/
    - https://flask-socketio.readthedocs.io/
- websockets
    - https://github.com/python-websockets/websockets

- simple-websocket

- flask_sock
    verwendet simple-websocket
- ws4py 

  

'''
from flask_socketio import SocketIO, emit
import sys
import os.path as osp
import os
import json
import logging
import time

from blinker import signal

from isp.logging import loggingHandlerClass

class WebSocketClass( loggingHandlerClass ):

    def __init__( self, app, config:dict={}, defaults:dict={} ):
        """_summary_

        Parameters
        ----------
        app: app
            initialized app

        """
        
        self.app = app 
        
        _defaults = { 
            "handlerName" : "SOCKET",
            "basetopic" : config["name"]
        } | defaults
        # loggingHandlerClass initialisieren
        loggingHandlerClass.__init__( self, config, _defaults )
        # signal bereitstellen
        self.signal = signal('socket')
        self.signalStartup = signal('socket-startup')


    def startup( self ):
        # self.socketio = SocketIO(async_mode="gevent", cors_allowed_origins='*')
        print( "startup websocket" )

        self._handler = SocketIO(
            self.app,
      #      manage_session=False,
      #      cors_allowed_origins='*',
      #      logger=True, 
      #      engineio_logger=True,
      #      namespace="/",
      #      path="sock"
            
        )
        
        self._handler.on_event( "connect", self.onConnect)
        self._handler.on_event( "disconnect", self.onDisconnect)
        self._handler.on_event( "publish", self.onMessage)

    def shutdown(self):
        """_handler stoppen.

        Stoppt den _handler und schließt die Verbindung
        """
        pass
    
    # --- Nachricht senden
    #
    def doPublish(self, msg:dict=None, qos=0, retain=False):
        """Stub function - stop logging
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
            msg["topic"] = "{}/{}".format( self.defaults["basetopic"], msg["topic"] )
            self._handler.emit( 'publish', msg )
        return True

    # --- event callbacks
    #
    #
    def _onDisconnect(self, *args, **kwargs):
        #print('socketio onDisconnect', args, kwargs)
        self._handler.emit('publish', {
            'topic': '{basetopic}/{stat}/connected'.format( **self.defaults ), 
            'payload': json.dumps(self.defaults["shutdown"] )
        })

    def onMessage(self, msgObj, *args, **kwargs ):
        """Eingehende Nachrichten verarbeiten.

            topic immer im format <base>/cmnd/<topic>

        """
        # msgObj prüfen und baseTopic entfernen
        msg = self.decodeMsgObj( msgObj )
        self.doMessage( msg )
