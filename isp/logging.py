# -*- coding: utf-8 -*-
"""

logging
=======

immer logger ISP mit mehreren handlers
- SOCKET
- MQTT

"""
import logging
import json
import sys
import os.path as osp
import os
import time
import psutil
import datetime

class loggingHandlerClass( logging.Handler ):

    def __init__(self, config:dict={}, defaults:dict={}):

        # root logger first 
        self.logger_name = "root"
         
        self._handler = None 

        self.config = { 
            "basetopic": "base",
            "logging": True
        } | config

        self.defaults = {
            "loggerName" : "ISP",
            "handlerName" : "ISP",
            "logLevel" : logging.NOTSET,
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
        } | defaults      
                 
        self.logging = self.config["logging"]
        self.loggerName = self.defaults["loggerName"]
        self.handlerName = self.defaults["handlerName"]
        self._progress = {}

        self.signal = None

        self.startup()

        if self.logging:
            self.addLoggerHandler( self.handlerName, self )


    def addLoggerHandler( self, name, handler ):
        """Add handler to logger name
        If not progress in logger add progressStart, progress, progressReady
        """
        logger = logging.getLogger( self.loggerName )
        logger.setLevel( self.defaults["logLevel"] )
        logging.Handler.__init__( handler )
        logger.addHandler( handler )

        if not hasattr(logger, "progress"): 
            # provide progress to logger
            logger.progressStart = handler.progress_start
            logger.progress = handler.progress_run
            logger.progressReady = handler.progress_ready

            # remember logger name 
            self.logger_name = logger.name
        
    def getLoggerHandler(self, handlerName):
        logger = logging.getLogger( self.loggerName )
        handler = None
        for h in logger.handlers:
            if hasattr(h, "handlerName") and h.handlerName == handlerName:
                handler = h
                break
        return handler

    def removeLoggerHandler( self, handler ):
        logger = logging.getLogger( self.loggerName )
        logger.removeHandler( handler )

    def startup( self ):
        """Stub function - start logging, set onEvent handlers

        """
        pass
    
    def shutdown(self):
        """Stub function - stop logging, disconnect handler
        """
        pass

    def doPublish(self, msg:dict=None, qos=0, retain=False):
        """Stub function - publish message with handler
        msg: dict
            Dict mit::
                - topic : str
                - payload : mixed
        qos : int, optional - used with mqtt
            Quality of Service. The default is 0.
        retain : bool, optional - used with mqtt
            Retain-Flag. The default is False.
        """
        pass

    # --- event callbacks
    #
    #
    def onConnect(self, client=None, userdata=None, flags=None, rc=None):
        """Nach einem erfolgreichem connect des Client 

        """
        self.publish({
            'topic': '{stat}/status'.format( **self.defaults ), 
            'payload': json.dumps(self.defaults["connected"] )
        })

    def onDisconnect(self, *args, **kwargs):
        """_summary_
        """
        self.publish({
            'topic': '{stat}/status'.format( **self.defaults ), 
            'payload': json.dumps(self.defaults["shutdown"] )
        })
       

    def onMessage(self, client, userdata, msgObj ):
        """Stub function - Process incoming messages

        client:
            the client instance for this callback
        userdata:
            the private user data as set in Client() or userdata_set()

        msgObj: mqtt.MQTTMessage(object)
        """
        msg = self.decodeMsgObj(msgObj)
        self.doMessage( msg )
    

    # --- Nachricht senden
    #
    #
    def publish(self, msg:dict=None, qos=0, retain=False):
        """msg aufbereiten und doPublish() aufrufen

        Intern wird immer basetopic vor topic gesetzt

        Parameters
        ----------
        msg: dict
            Dict mit::
                - topic : str
                - payload : mixed
        qos : int, optional - used with mqtt
            Quality of Service. The default is 0.
        retain : bool, optional - used with mqtt
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

        return self.doPublish(msg, qos, retain)

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


    def decodeMsgObj(self, msgObj, basetopicReplace=True ):
        """Payload des msgObj wenn möglich nach string umwandeln.

        oder wenn json im string dann nach dict umwandeln

        Parameters
        ----------
        msg: dict oder MQTTMessage
            umzuwandelndes message Object
        basetopicReplace: bool
            <basetopic> aus topic entfernen

        Returns
        -------
        result: dict

            .. code::

            {
                "topic": string
                "payload": string
                "_fulltopics": list -  mit topic Teilen aufgeteilt bei /
                "_decodeError" # nur wenn Fehler aufgetaucht sind
            }

        """
        result = {
            "topic" : "",
            "payload" : "",
            "_fulltopics": []
        }
        #print( "# decodeMsgObj", msgObj.topic, type( msgObj.payload ), msgObj.payload )
        if isinstance(msgObj, (float, int, str)):
            result["topic"] = msgObj
            
        elif isinstance(msgObj, (dict)):
            if "topic" in msgObj:
                result["topic"] = msgObj["topic"]
            if "payload" in msgObj:
                result["payload"] = msgObj["payload"]
        else:
            result = {
                "topic" : msgObj.topic,
                "payload" : msgObj.payload
            }

        result["_fulltopics"] = result["topic"].split("/")
        if basetopicReplace:
            result["topic"] = result["topic"].replace( "{}/".format( self.defaults["basetopic"] ), "" )

        if type( result["payload"] ) == bytes:
            try:
                result["payload"] = result["payload"].decode('utf-8')
            except Exception: # pragma: no cover
                result["_decodeError"] = "byte.decode error"

        if type( result["payload"] ) == str and len(result["payload"]) > 0 and result["payload"][0] == "{":
            try:
                result["payload"] = json.loads( result["payload"] )
            except ValueError: # pragma: no cover
                result["_decodeError"] = "json.loads error"

        return result
    

    # --- info, warning, error 
    #
    #
    def info(self, msg):
        """Info über looging oder print.

        logging.info nur wenn self.logging=True

        Wenn es einen handler gibt dann dorthin sonst auf die konsole

        Parameters
        ----------
        msg : str
            Auszugebende Nachricht

        Returns
        -------
        None.

        """

        if self.logging == True:
            logger = logging.getLogger( self.loggerName )
            if logger.hasHandlers():
                logger.info( msg )
            else:
                print("### {} INFO".format(self.loggerName), msg)

    def warning(self, msg):
        """Warnung über logging oder print.

        logging.warning nur wenn self.logging=True

        Wenn es einen handler gibt dann dorthin sonst auf die Konsole

        Parameters
        ----------
        msg : str
            Auszugebende Nachricht

        Returns
        -------
        None.

        """
        if self.logging == True:
            logger = logging.getLogger( self.loggerName )
            if logger.hasHandlers():
                logger.warning( msg )
            else:
                print("### {} WARNING".format(self.loggerName), msg)

    def error(self, msg):
        """error über logging oder print.
        
        Wenn es einen handler gibt dann dorthin sonst auf die konsole
        
        Parameters
        ----------
        msg : str
            Auszugebende Nachricht

        Returns
        -------
        None.

        """
        logger = logging.getLogger( self.loggerName )
        if logger.hasHandlers():
            logger.error( msg )
        else:
            print("### {} ERROR".format(self.loggerName), msg)

    
    # ---- Bearbeitungsfortschritt
    #
    #
    def progress_start( self, topic:str=None, payload={}  ):
        """Startet einen Bearbeitungsfortschritt.

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

    def progress_run( self, topic:str=None, progress=0, payload={}  ):
        """Sendet den Bearbeitungsfortschritt.

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

    # --- durch onMessage und do... aufgerufene methoden
    #
    #
    #
    def doMessage(self, msg:dict={}):
        """Nachrichten (cmnd) verarbeiten

        Parameters
        ----------
        msg : dict, optional
            Message dict mit _fulltopics list
        """
        #print("logging-doMessage", msg)
        cmd = msg["_fulltopics"][1]
        if len(msg["_fulltopics"]) > 2 and cmd == self.defaults["cmnd"]:
            if msg["_fulltopics"][2] == "echo": #pragma: no cover
                msg["topic"] = self.defaults["stat"] + "/echo"
                self.publish( msg )
            elif msg["_fulltopics"][2] == "logger-info": #pragma: no cover
                self.info( msg["payload"] )
            elif msg["_fulltopics"][2] == "logger-warning": #pragma: no cover
                self.warning( msg["payload"] )
            elif msg["_fulltopics"][2] == "logger-error": #pragma: no cover
                self.error( msg["payload"] )
            elif msg["_fulltopics"][2] == "status": #pragma: no cover
                self.doStatus( )
            elif msg["_fulltopics"][2] == "process": #pragma: no cover
                self.doProcess( msg )
            else:
                self.doCmnd( msg )
                self.doSignal( msg )

    def doCmnd(self, msg:dict={}):
        """Stub function - Process cmnd messages 
        
        Parameters
        ----------
        msg : dict
            dict mit topic, payload, _fulltopics
        """
        pass

    def doSignal(self, msg:dict={}):
        """Message über signal weiterleiten

        Parameters
        ----------
        msg : dict, optional
            dict mit topic und payload.
            .. code::

                - topic: <BASE>/stat/#
                - payload: beliebig

        Returns
        -------
        None.

        """
        if self.signal:
            self.signal.send( msg )

    def doStatus(self, msg:dict=None):
        """Status Information senden.

        .. code::

            <BASE>/stat/status

        Parameters
        ----------
        msg : dict, optional
            dict mit payload. The default is None.
            .. code::

                - topic: <BASE>/stat/status
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

        self.info("doStatus - {} : {}".format( msg["topic"], str(1) ) )
        self.publish( msg, qos=0, retain=False)

        self.doSignal( msg )

    def doProcess(self, msg:dict={}): #pragma: no cover
        """Den in msg.payload angegebenen process abfragen.

        payload entweder als pid oder als processname

        .. code::

            <BASE>/stat/process { "<pid>": {
                'pid', 
                'name', 
                'cwd', 
                'status', 
                'memory_rss', 
                'num_threads'
            } }
            

        Parameters
        ----------
        msg : dict, optional
            Das Nachrichten Object mit payload. The default is None.

        Returns
        -------
        None.

        """
        pl = {  }
        if msg["payload"] == "":
            return pl
 
        # name oder pid 
        payload = msg["payload"]
        pid = 0
        try:
            pid = int(payload)
        except ValueError:
            pass

        def getInfos(p):
            pd = p.as_dict(attrs=[
                'pid', 'name', 'cwd', 'status', 'memory_info', 'num_threads'
            ])
            pd["create_time"] = datetime.datetime.fromtimestamp(p.create_time()).strftime("%Y-%m-%d %H:%M:%S")
            rss = pd["memory_info"][0] # rss - Resident Set Size
            del pd["memory_info"]
            pd["memory_rss"] = f"{round(rss/(pow(1024,2)), 2)} MB"
            return pd
        
        if pid==0:
            for p in psutil.process_iter(attrs=[ 'pid', 'name' ]):
                if payload == p.info['name']:
                    pid = p.info['pid']
                    pl[pid] = getInfos( p )
                   
                    break
        elif pid > 0:
            pl[pid] = {}
            try:
                p = psutil.Process( pid )
                pl[pid] = getInfos( p )
            except psutil.NoSuchProcess:
                pass

        topic = self.defaults["stat"] + "/process"

        # pl als json senden
        self.info("doProcess - {} : {}".format( topic, json.dumps( pl ) ) )

        msg = {"topic": topic, "payload": pl }

        self.publish( msg , qos=0, retain=False )

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

        # gibt es einen  Handler dann über ihn loggen
        if self._handler:
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
            except RuntimeError as e:
                """ RuntimeError: Working outside of request context.
                Error bei publish SOCKET Working outside of request context.

                This typically means that you attempted to use functionality that needed
                an active HTTP request. Consult the documentation on testing for
                information about how to avoid this problem
                """
                # FIXME: mqtt ruft logger-error socket soll benachrichtigen
                print("{} - {} - logging.emit:".format(ts, self.handlerName), record )
            except Exception as e:  # pragma: no cover
                print( " # logging.emit: Error bei publish", self.handlerName, e, msg )
        else:
            print("{} - {} - logging.emit:".format(ts, self.handlerName), record )
