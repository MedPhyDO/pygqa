# -*- coding: utf-8 -*-

"""
Dicom Funktionen auch zum Abfragen eines Dicom servers

Statuscodes:
    https://pydicom.github.io/pynetdicom/stable/reference/status.html
    
    
Test mit findscu
findscu -v -S -k 0008,0052="IMAGE" -k "0008,0018=1.2.246.352.62.1.4625604914426170283.12140466054276070541" -aet PHYSIK_BA -aec VMSDBD 192.168.131.200 105 

Test mit getscu
"""

__author__ = "R. Bauer"
__copyright__ = "MedPhyDO - Machbarkeitsstudien des Instituts für Medizinische Strahlenphysik und Strahlenschutz am Klinikum Dortmund im Rahmen von Bachelor und Masterarbeiten an der TU-Dortmund / FH-Dortmund"
__credits__ = ["R.Bauer", "K.Loot"]
__license__ = "MIT"
__version__ = "0.1.0"
__status__ = "Prototype"

import os
import os.path as osp
import json

from blinker import signal, Namespace
import threading
import queue

from pydicom.dataset import Dataset
from pydicom import dcmread

from pynetdicom import AE, evt, StoragePresentationContexts

from pynetdicom.sop_class import (
    StudyRootQueryRetrieveInformationModelFind,
    StudyRootQueryRetrieveInformationModelMove,
    RTImageStorage
)


# By default a number of notification handlers are bound for logging purposes. 
# If you wish to remove these then you can do the following before creating any associations:
#from pynetdicom import _config
# Don't bind any of the default notification handlers
#_config.LOG_HANDLER_LEVEL = 'none'

import logging
logger = logging.getLogger( "MQTT" )

class dicomClass(  ):
    """Dicom Klasse zum Abfragen eines Dicom servers
    
    Attributes
    ----------
    dicomPath : str
        Pfad zu den Dicom Dateien
        
    server : str
        Der zu verwendende DICOM Server aus config.json
     
    ae : AE
        Application Entity
      
    assoc : <associate>
        Die Verbindung zum Dicom Server Subklasse von threading.Thread
    
    scp : 
        Der server zum empfangen der Daten
    
    override: bool
        Dicomfiles neu anlegen    
    
    dicomData : dict
        die über retrieve oder load geholten Datensätze
        
    messageId : int
        id der laufenden abfrage
        
    """
    
    def __init__( self, server="VMSDBD", config=None ):
        """Klasse initialisieren 
        
        Sicherstellen das in dicomPath ein gültiger Pfad liegt
        """
        
        # Klassen defaults
        self.dicomPath: str = None
        self.server: str = None
        self.ae: AE = None
        self.assoc = None
        self.scp = None
        self.override: bool = False
        self.subPath: str = ""
        self.dicomData: dict = {}
        self.messageId = 0
        
        # konfiguration verwenden oder einlesen liegt in self.config
        if config:
            self.config = config
        
        self.server=server
        
        self.initialized = False
        
        # pfad zu den dicom dateien bereitstellen
        if self.config.dicom[self.server]["local_dir"][0] == ".": # pragma: no cover
            self.dicomPath = os.path.abspath( osp.join( str(self.config.BASE_DIR), str(self.config.dicom[self.server]["local_dir"]) ) )
            self.config.dicom[self.server]["local_dir"] = self.dicomPath
        else:
            self.dicomPath = str( self.config.dicom[self.server]["local_dir"] )
            
        
        if not os.path.isdir(self.dicomPath): # pragma: no cover
            logger.debug('dicomClass.initAE: erzeuge dirname={}'.format( self.dicomPath ) )           
            try:
                os.makedirs( self.dicomPath )
            except (OSError, IOError) as e: # pragma: no cover
                msg = 'dicomClass.initAE: Fehler beim erzeugen von: {}'.format( self.dicomPath )
                logger.error(  msg )
                self.appError( msg, e )
                
        if os.access(self.dicomPath, os.W_OK) is True:
            self.initialized = True
        else: # pragma: no cover
            msg = 'dicomClass.initAE: keine Schreibrechte auf: {}'.format( self.dicomPath ) 
            logger.error(  msg )
            self.appError( msg )
      
    def __del__(self):
        """Deleting (Calling destructor) 
             
        """
        self.closeAE()

        
    def initAE( self ):
        """Application Entity bereitstellen
        
        Status Codes: Non-service specific - 0xC000 to 0xC0FF

        
        Verwendete evt_handlers::
        
        * EVT_ESTABLISHED
        * EVT_REJECTED
        * EVT_RELEASED


        
        Returns
        -------
        status : hex
            - 0x0000 - alles OK
            - 0xC0FF -Verbindung fehlgeschlagen
            
        """
        
        # print( "dicomClass.initAE: ", self.config.dicom[self.server] )  
        # Initialise the Application Entity
        assoc = None
        try:
            # Initialise the Application Entity
            self.ae = AE( ae_title=self.config.dicom[self.server]["aet"] )
            
            # Study Suche verwenden
            self.ae.add_requested_context( StudyRootQueryRetrieveInformationModelFind )
            
            # Add a requested presentation context
            self.ae.add_requested_context( StudyRootQueryRetrieveInformationModelMove )
      
            # Add the storage SCP's supported presentation contexts
            self.ae.supported_contexts = StoragePresentationContexts
            self.ae.add_supported_context( RTImageStorage )
            
            # bei den handlern wird nicht auf EVT_REJECTED geprüft, da offline ja möglich ist
            handlers=[
                ( evt.EVT_ESTABLISHED , self.handle_event),
                #( evt.EVT_REJECTED , self.handle_event),
                ( evt.EVT_RELEASED, self.handle_event),
            ]
            
            # Associate with peer AE at IP 127.0.0.1 and port 11112
            assoc = self.ae.associate(
                self.config.dicom[self.server]['server_ip'], 
                self.config.dicom[self.server]['server_port'], 
                ae_title=self.config.dicom[self.server]['aec'],
                evt_handlers=handlers
            )
        except:
            pass
    
        self.assoc = None
        status = 0xC0FF
        if assoc and assoc.is_established:
            self.assoc = assoc
            status = 0x0000
            logger.debug('dicomClass.initAE: Verbindung hergestellt')
        else:
            logger.warning('dicomClass.initAE: Association rejected, aborted or never connected')
            
        return status
        
    def closeAE( self, status=0x0000 ):
        '''shutdown scp und Release association
        
        Parameters
        ----------
        status : int, optional
            Grund des closeAE mitgeben. The default is 0x0000.

        Returns
        -------
        None.

        '''
        
        #print("closeAE")
        done = {
            "scp": "",
            "assoc": "",
            "ae": "",
        }
        
        do = 0
        # shutdown scp - empfangen
        if self.scp:
            self.scp.shutdown()
            self.scp = None
            done["scp"] = "shutdown()"
            do += 1 
            
        # release assoc
        if self.assoc:
             self.assoc.release()
             self.assoc = None
             done["assoc"] = "release()"
             do += 1 
             
        # shutdown ae    
        if self.ae:
            self.ae.shutdown()
            self.ae = None
            done["ae"] = "shutdown()"
            do += 1 
            
        if do > 0:      
            logger.debug('dicomClass.closeAE: {}'.format( json.dumps( done ) ) )
            
        return done
       
    def aeInfo( self ):
        '''
        

        Returns
        -------
        str_out : TYPE
            DESCRIPTION.

        '''
        
        str_out = ""
        if self.ae:
            # Association information
            str_out += '  Association(s): {0!s}/{1!s}\n' \
                       .format(len(self.ae.active_associations),
                               self.ae.maximum_associations)
    
            for assoc in self.ae.active_associations:
                str_out += '\tPeer: {0!s} on {1!s}:{2!s}\n' \
                           .format(assoc.remote['ae_title'],
                                   assoc.remote['address'],
                                   assoc.remote['port'])
        else:
            str_out += 'no Association (self.ae)'
            
        return str_out
 
    def handle_event(self, event):
        '''Event Verarbeitung 
        sendet in evt_handlers definierte events über signal weiter

        Parameters
        ----------
        event : pynetdicom.evt
            Ein von pynetdicom gesendeter event.

        Returns
        -------
        None.

        '''
        logger.info('dicomClass.handle_event: {}'.format( event.event.name ) )
        
        signal( 'dicom.{}'.format( event.event.name ) ).send( { 
            "name": event.event.name,
            "event": event, 
            "status":0x0000,
            "msg":""
        } )
    
    def handle_STORE(self, event ):
        '''Handle a C-STORE request event.
        Dicom Daten empfangen und speichern
        
        https://pydicom.github.io/pynetdicom/stable/reference/status.html
        
        Status Codes: C-MOVE related - 0xC500 to 0xC5FF
        
        Parameters
        ----------
        event : TYPE
            DESCRIPTION.
        
        Returns
        -------
        status : hex
            - 0x0000 - alles OK
            - 0xC511 - Unhandled exception raised by the handler bound to evt.EVT_C_MOVE
            - 0xC512
            

        '''
        
        logger.debug('dicomClass.handle_STORE')
        
        ds = event.dataset
        context = event.context

        #print( "handle_store", ds, context )
        status = 0x0000
        
        # in dicomData unter SOPInstanceUID die geladenen Daten ablegen
        self.dicomData[ ds.SOPInstanceUID ] = ds
        
        # Ort der Dicomdaten bestimmen
        local_path = osp.join( self.dicomPath, self.subPath )
        
        # ggf anlegen
        if not os.path.isdir( local_path ):
            logger.debug('dicomClass.handle_STORE: erzeuge subdir={}'.format( local_path ) )
            os.makedirs( local_path )
        
        # Datei schon vorhanden, oder nicht 
        exists, filename = self.archive_hasSOPInstanceUID( ds.SOPInstanceUID )
        
                
        #exists = os.path.isfile( filename )
        
        logger.debug( "dicomClass.handle_STORE: {}".format( ds.SOPInstanceUID + ".dcm" ) )
        msg = ""
        # DICOM Daten schreiben
        if not exists or self.override:
            # Wie werden die Bilddaten inerpretiert
            ds.is_little_endian = True
            ds.is_implicit_VR = True

            #print( "on_c_store", ds.RTImageLabel, context, info )
            
            # Datei speichern
            #   write_like_original=False um DCIM zu schreiben
            try:
                ds.save_as( filename , write_like_original=False )
                msg = "Datei abgelegt: {}".format( filename )
            except IOError as e:
                # 0xC511 - Unhandled exception raised by the user’s implementation of the on_c_move callback
                status = 0xC511 
                msg = "io_error: {}".format( str(e) )
                #print( "dicomClass.on_c_store(io_error) [{}]: {}".format(status, filename ), e )
                logger.warning( "dicomClass.handle_STORE(io_error) [{}]: {}".format(status, filename ) )
                
            except:
                status = 0xC512 
                msg = "io_error: {}".format( filename )
                #print( "dicomClass.on_c_store(save_error) [{}]: {}".format(status, filename )  )
                logger.warning( "dicomClass.handle_STORE(save_error) [{}]: {}".format(status, filename )  )
                
        else:
            logger.debug( "Datei vorhanden: {}".format( filename ) )
            msg = "Datei vorhanden: {}".format( filename )
            
            
        #self.assoc.abort()

        logger.debug( "dicomClass.handle_STORE: {}".format( ds.SOPInstanceUID + ".dcm" ) )
       
        signal( 'dicom.EVT_C_STORE' ).send( { 
            "name": event.event.name,
            "_is_cancelled": False,
            "dataset":ds, 
            "status":status,
            "msg":msg
        } )

        return status
     
    def query( self, PatientID:str=None, 
                 StudyInstanceUID:str=None, 
                 SeriesInstanceUID:str=None, 
                 SOPInstanceUID:str=None
        ):
        '''Eine DICOM Abfrage durchführen
        
        Parameters
        ----------
        PatientID : str, optional
            Eine PatientenID. The default is None.
        StudyInstanceUID : str, optional
            Eine StudyInstanceUID. The default is None.
        SeriesInstanceUID : str, optional
            Eine SeriesInstanceUID. The default is None.
        SOPInstanceUID : str, optional
            Eine SOPInstanceUID. The default is None.

        Returns
        -------
        status : hex
            Rückgabecode von send_c_find::
            
            C-FIND related - 0xC300 to 0xC3FF
            
            Zusätzlich:
            
            - 0xC3F1 - keine PatientID
            - 0xC0FF - initAE: Verbindung fehlgeschlagen
            
        results : list    
            gefundene daten
            
        '''
        
        # print( "dicomClass : query", PatientID )
        results = []
        
        if not PatientID:
            logger.warning("dicomClass.query: keine PatientID")
            return 0xC3F1, results
        
        # Verbindung ggf herstellen
        if not self.assoc:
            status = self.initAE()
            # und testen
            if not self.assoc:
                logger.warning("dicomClass.query: Verbindung fehlgeschlagen")            
                return status, results

        
        # Create our Identifier (query) dataset
        ds = Dataset()
        
        # zuerst den Abfragelevel bestimmen
        
        # erstmal Patient
        ds.QueryRetrieveLevel = 'PATIENT'
        
        # Unique key for PATIENT level
        ds.PatientID = PatientID
    
        # Unique key for STUDY level
        if StudyInstanceUID:
            ds.QueryRetrieveLevel = 'STUDY'
            ds.StudyInstanceUID = str(StudyInstanceUID)
       
        # Unique key for SERIES 
        if SeriesInstanceUID:
            ds.QueryRetrieveLevel = 'SERIES'
            ds.SeriesInstanceUID = str(SeriesInstanceUID)
            
        # Unique key for IMAGE 
        if SOPInstanceUID:
            ds.QueryRetrieveLevel = 'IMAGE'
            ds.SOPInstanceUID = str(SOPInstanceUID)
            
        logger.debug('dicomClass.query: QueryRetrieveLevel {} - {}'.format( ds.QueryRetrieveLevel, SOPInstanceUID ) )
        
        # Use the C-FIND service to send the identifier
        # A query_model value of 'S' means use the 'Study Root Query Retrieve
        #     Information Model - Find' presentation context
        responses = self.assoc.send_c_find(ds, query_model='S')

        logger.debug( "dicomClass.query: loaded - QueryRetrieveLevel {}".format( ds.QueryRetrieveLevel, SOPInstanceUID ) )
        for (response_status, identifier) in responses:
           
            # status code bestimmen
            status = 0xC3F3
            if response_status:
                status = response_status.Status
                
            # print("dicomClass : query response 0x{0:04x}".format(status) )
            # je nach status
            if status in (0xFF00, 0xFF01) and identifier:
               # If the status is 'Pending' then `identifier` is the C-FIND response  
               results.append( identifier )
            elif status == 0x0000:
                # abfrage wurde komplett durchgeführt
                # print("identifier:", identifier)
                pass
            else:
               logger.warning('dicomClass.query: Connection timed out, was aborted or received invalid response: 0x{0:04x}'.format( status ) )

        return results, status   
    
    def _retrieve( self, PatientID:str=None, 
                 StudyInstanceUID:str=None, 
                 SeriesInstanceUID:str=None, 
                 SOPInstanceUID:str=None,
                 override:bool=False,
                 subPath:str=""
                 ):
        '''DICOM Datensätze vom Server holen
        

        Parameters
        ----------
        PatientID : str, optional
            Eine PatientenID. The default is None.
        StudyInstanceUID : str, optional
            Eine StudyInstanceUID. The default is None.
        SeriesInstanceUID : str, optional
            Eine SeriesInstanceUID. The default is None.
        SOPInstanceUID : str, optional
            Eine SOPInstanceUID. The default is None.
        override : bool, optional
            das holen der Daten über einen externen Aufruf machen.
            wird von getdicom.py verwendet und dort auf False gesetzt. The default is False.
        subPath : str, optional
            ergänzt den lokalen Ablageort um subPath

        evt_handlers
        ------------
        EVT_C_STORE
        EVT_REJECTED
        EVT_ACCEPTED
        EVT_ABORTED
        
        Signals
        -------
        dicom.EVT_C_STORE
        

        Returns
        -------
        status : Dicom Status
            - 0x0000 - daten vorhanden/gelesen | load archive | run EVT_C_STORE
            - 0xC5F1 - keine PatientID
            - 0xC0FF - initAE: Verbindung fehlgeschlagen
            - 0xC512 - 
            - 0xC515 - Address/Port already in use
            
            
        '''
        #print( "dicomClass : retrieve", PatientID, SOPInstanceUID)
        '''
        if not PatientID:
            logger.warning("dicomClass.retrieve: keine PatientID")
            signal( 'dicom.EVT_C_STORE').send( { 
                    "name": "EVT_C_STORE",
                    '_is_cancelled': True,
                    #"dataset": None,
                    "status":0xC5F1,
                    "msg" : "keine PatientID"
            } )
            return 0xC5F1
        '''
        
      
        # override Status merken
        self.override = override
        
        # subPath merken
        self.subPath = subPath
        
        # Create our Identifier (query) dataset
        ds = Dataset()
        
        #auf welchem Level soll abgefragt werden
        #ds.QueryRetrieveLevel = 'SERIES'
        if PatientID:
            ds.QueryRetrieveLevel = 'PATIENT'
            # Unique key for PATIENT level
            ds.PatientID = PatientID
    
        # Unique key for STUDY level
        if StudyInstanceUID:
            ds.QueryRetrieveLevel = 'STUDY'
            ds.StudyInstanceUID = str(StudyInstanceUID)
       
        # Unique key for SERIES 
        if SeriesInstanceUID:
            ds.QueryRetrieveLevel = 'SERIES'
            ds.SeriesInstanceUID = str(SeriesInstanceUID)
            
        # Unique key for IMAGE 
        if SOPInstanceUID:
            ds.QueryRetrieveLevel = 'IMAGE'
            ds.SOPInstanceUID = str(SOPInstanceUID)
            
        ds.Modality = 'RTIMAGE'
        
        # info QueryRetrieveLevel ausgeben
        logger.debug( "dicomClass._retrieve: QueryRetrieveLevel {}".format( ds.QueryRetrieveLevel ) )              
              
        # bei image level versuchen aus dem Dateiarchiv zu lesen statt vom Server zu holen
        if ds.QueryRetrieveLevel == 'IMAGE' and not override:
            # info 
            logger.debug( "dicomClass._retrieve: search archive {}".format( ds.SOPInstanceUID ) )              
            # file aus dem archiv laden
            file_ds = self.archive_loadSOPInstanceUID( ds.SOPInstanceUID )
            # konnte gelesen werden dann raus hier
            if file_ds:
                self.dicomData[ ds.SOPInstanceUID ] = file_ds
                
                logger.debug( "dicomClass._retrieve: load archive {}".format( ds.SOPInstanceUID ) )
       
                signal( 'dicom.EVT_C_STORE').send( { 
                    "name": "EVT_C_STORE",
                    '_is_cancelled': False,
                    "status":0x0000,
                    "msg" : "load archive",
                    "dataset": ds, # Dataset mitgeben (fertig) 
                } )
                return 0x0000
            else:
                logger.info( "dicomClass._retrieve: no archive {}".format( ds.SOPInstanceUID ) )
       
        #
        # ansonsten wird hier versucht neu zu laden
        #
        
        # Verbindung ggf herstellen
        if not self.assoc:
            status = self.initAE()
            # und testen
            if not self.assoc:
                logger.warning("dicomClass._retrieve: Verbindung fehlgeschlagen")     
                signal( 'dicom.EVT_C_STORE').send( { 
                    "name": "EVT_C_STORE",
                    '_is_cancelled': True,
                    "status": status,
                    "msg" : "initAE: Verbindung fehlgeschlagen",
                    # "dataset": None,
                } )
                return status
            
        # Informationen zur Verbindung 
        logger.debug( "dicomClass._retrieve: {}".format( self.aeInfo() ) )

        #print( "dicomClass.retrieve: QueryRetrieveLevel {}".format( ds.QueryRetrieveLevel ) )
        # wenn noch nicht passiert dann server zum empfangen der daten starten
        if not self.scp:
            # message id zurpcksetzen
            self.messageId = 0
            #print( self.scp )
            # handler zum empfang der Daten bereitstellen
            handlers = [
                 ( evt.EVT_C_STORE, self.handle_STORE),
                 ( evt.EVT_ACCEPTED, self.handle_event),
                 ( evt.EVT_ABORTED, self.handle_event),
                 
                 ( evt.EVT_REJECTED, self.handle_event),
                 ( evt.EVT_RELEASED, self.handle_event),
                 ( evt.EVT_REQUESTED, self.handle_event),

                 ( evt.EVT_DIMSE_SENT, self.handle_event),
                 ( evt.EVT_DIMSE_RECV, self.handle_event),
                 #( evt.EVT_PDU_RECV, self.handle_event),
                 #( evt.EVT_PDU_SENT, self.handle_event),
                 
            ]
            # 
            # Server starten um die Daten zu empfangen storage SCP on port listen_port
            self.ae.ae_title = self.config.dicom[self.server]['aet']
            sig_msg = None
            try:  
                logger.debug( "dicomClass._retrieve:  start server" )
                # If set to non-blocking then a running ``ThreadedAssociationServer``
                # instance will be returned. This can be stopped using ``shutdown()``.
                self.scp = self.ae.start_server(
                    ('', self.config.dicom[self.server]['listen_port']), 
                    block=False, # Abfrage über Thread
                    evt_handlers=handlers
                )
                #print( "dicomClass.retrieve: start server" )
                
            except OSError as e:
                #print( "dicomClass.retrieve: 0xC515 - {}".format( str(e) )  )
                logger.error( "dicomClass._retrieve: 0xC515 - {}".format( str(e) ) )
                sig_msg = { 
                    "name": "EVT_C_STORE",
                    "_is_cancelled": True,
                    "status": 0xC515,
                    "msg" : "{}".format( str(e) ),
                    # "dataset": ds,
                }
                # The user’s implementation of the on_c_move callback failed to yield a valid (address, port) pair
               
            except:
                sig_msg = {
                    "name": "EVT_C_STORE",
                    "_is_cancelled": True,
                    "status": 0xC515,
                    "msg" : "Fehler bei start listen server",
                    # "dataset": ds,
                }
                                
                logger.error( "dicomClass._retrieve: ERROR start listen server" )
             
            # nach einem Fehler signal senden 
            if not sig_msg == None:
               # print( "sig_msg", sig_msg )
                signal( 'dicom.EVT_C_STORE' ).send( sig_msg )
                return 0xC515
            
        
        # Use the C-MOVE service to send the identifier
        # A query_model value of 'P' means use the 'Patient Root Query
        #   Retrieve Information Model - Move' presentation context
        # in pynetdicom.status
        
        # save Error
        result = 0xC512

        try:
            #print( "dicomClass.assoc.send_c_move", self.assoc.is_established, self.scp, self.assoc )
            self.messageId += 1
            responses = self.assoc.send_c_move(
                ds, 
                self.config.dicom[self.server]['aet'], 
                query_model='S',
                msg_id = self.messageId
            )
            
            #print( "dicomClass : .assoc.send_c_move response" )
            i = 0
            for (status, identifier) in responses:
                
                i += 1
                if status:
                    result = status.Status
                    #print( "dicomClass : .assoc.send_c_move - response", hex(result), identifier )
                    #
                    logger.debug( 'dicomClass._retrieve: {} - C-MOVE query status: {}'.format( i, hex(result) ) )
                    
                    # If the status is 'Pending' then the identifier is the C-MOVE response
                    
                    # Pending
                    #   | ``0xFF00`` - Sub-operations are continuing
                    #   Der weitere Ablauf wird über retrieve_thread abgewickelt
                    if status.Status in (0xFF00, 0xFF01):
                        if identifier:
                            print( "dicomClass._retrieve:  0xFF00, 0xFF01",  identifier )
                            pass
                    elif status.Status == 0x0000:
                        if identifier:
                            print( "dicomClass._retrieve:  0x0000",  identifier)
                        pass
                    elif status.Status == 0xc002:
                        # User’s callback implementation returned an invalid status object (not a pydicom Dataset or an int)
                        if identifier:
                            print( "dicomClass._retrieve:  0xc002",  identifier)
                            
                    elif status.Status  in (0xC511, 0xC512):
                        logger.error( "dicomClass._retrieve: Fehler beim speichern der DICOM Daten" )
                        if identifier:
                            print( "dicomClass._retrieve 0xC511",  identifier)

                else:
                    logger.warning('Connection timed out, was aborted or received invalid response')
                             
            logger.debug('dicomClass._retrieve: response ready')
        except Exception as e:
            # alle sonstigen Fehler abfangen
            logger.warning("dicomClass._retrieve: Fehler beim holen der '{}' DICOM Daten: {}".format( ds.QueryRetrieveLevel, e ))
            pass
        
        logger.debug("dicomClass._retrieve: DICOM Daten holen: {} - {}".format( hex(result), SOPInstanceUID ) )
        
        # print("DICOM Daten holen: {}".format( SOPInstanceUID ), hex(result) )
        # Completely shutdown the server and close it's socket.
        
        # wenn nicht pending (retrieve_thread übernimmt) EVT_C_STORE mit _is_cancelled senden 
        # 0xff00 - Pending
        # 0x0000 - Success
        if not result in ( 0x0000, 0xff00):
        #if not result == 0xff00:
            signal( 'dicom.EVT_C_STORE').send( { 
                    "name": "EVT_C_STORE",
                    "_is_cancelled": True,
                    "status": result,
                    "msg": "run EVT_C_STORE",
                    #  "dataset": ds,
            } )
            
            
        #self.scp.shutdown()
        #self.scp = None
        
        return result
        

    def archive_hasSOPInstanceUID(self, SOPInstanceUID):
        '''Prüft ob eine SOPInstanceUID schon im File Archiv vorhanden ist
        
        Parameters
        ----------
        SOPInstanceUID : TYPE
            Eine SOPInstanceUID.

        Returns
        -------
        exists : bool
            Datei vorhanden oder nicht.
        filename : str 
            Der geprüfte Dateiname
        '''
        
        filename = osp.join( self.dicomPath, self.subPath, SOPInstanceUID + ".dcm" )
            
        return os.path.isfile( filename ), filename
        
    def archive_loadSOPInstanceUID( self, SOPInstanceUID ):
        '''Lädt eine Dicomdatei mit SOPInstanceUID aus dem Archiv
        
        Parameters
        ----------
        SOPInstanceUID : str
            Eine SOPInstanceUID.

        Returns
        -------
        ds : TYPE
            DESCRIPTION.

        '''
        
        ds = None
        exists, filename = self.archive_hasSOPInstanceUID( SOPInstanceUID )
        
        if exists:
            try:
                # mit force True einlesen um trotz fehlender headerdaten einzulesen
                ds = dcmread(filename, force=True)
            except:
                # alle sonstigen Fehler abfangen
                logger.error("Fehler beim lesen der DICOM Datei")
                pass
            
            if ds:
                self.dicomData[ ds.SOPInstanceUID ] = ds
                
                #print(ds.PatientID, ds.RadiationMachineName, ds.SOPInstanceUID)
                
        return ds
   

    def retrieve( self, params={} ):
        '''
        
        Parameters
        ----------
        params : TYPE, optional
            DESCRIPTION. The default is {}.

        Returns
        -------
        result : TYPE
            DESCRIPTION.

        suchen nach
            Received unexpected C-MOVE service message in pynetdicom Association _serve_request
            aufgerufen von _run_reactor
        '''
        
        result = []
        signals = []
        
        result_available = threading.Event()
        mq = queue.Queue()
            
        def _C_STORE( signal ):
            #print('dicom-retrieve Signal  : _C_STORE', signal )
            
            signals.append(signal)
            if signal["_is_cancelled"] == True:
                # Vorgang abbrechen
                result_available.set()
            elif signal["_is_cancelled"] == False:
                #print('Signal  : _C_STORE', signal["_is_cancelled"], signal["msg"] )
                if "dataset" in signal and "SOPInstanceUID" in signal["dataset"]:
                    #print('Signal  : _C_STORE', signal["dataset"].SOPInstanceUID )
                    # Ergebnis setzen und abbrechen
                    result.append( signal["dataset"].SOPInstanceUID )
                    result_available.set()
            
        def _RELEASED( signal ):
            #print('dicom-retrieve Signal  : _RELEASED', signal)
            signals.append( signal )
            result_available.set()    
            
        def _REJECTED( signal ):
            #print('dicom-retrieve Signal  : _REJECTED', signal)
            signals.append( signal )
            result_available.set() 
            
        def _ABORTED( signal ):
            #print('dicom-retrieve Signal  : _ABORTED', signal)
            signals.append( signal )
            result_available.set()
            
            
        signal( 'dicom.EVT_C_STORE' ).connect( _C_STORE )
        
        signal( 'dicom.EVT_REJECTED' ).connect( _REJECTED )
        signal( 'dicom.EVT_RELEASED' ).connect( _RELEASED )
        signal( 'dicom.EVT_ABORTED' ).connect( _ABORTED )
        #signal.alarm(5) # 5 sekunden zeit lassen

        #print('Main    : before creating thread')
        
        # Als Thread aufrufen, über mq.get() wird die Rückgabe von  _retrieve abgerufen
        thread = threading.Thread( target=lambda q, args: q.put( self._retrieve( **args ) ), args=( mq, params ) )
   
        #thread = threading.Thread( target=self.retrieve, kwargs=params )
        #print('Main    : before start thread')
        thread.start()
        #print("Main    : before join thread")
        #thread.join()
        #print("Main    : wait for the thread to finish")
        
        # nach max. 10 sec den Vorgang abbrechen
        while not result_available.wait( timeout=10 ):
            #print('Main    : {}% wait done...'.format(progress) )
            
            result_available.set()
        
           
        #print('Main    : {}% done...'.format(progress))
        
        #print('Main    : The result is', result)
        #print('Main    : The mq result is', hex( mq.get() ) )
        
        #print("Main    : all done")
        return result, signals
 

# -----------------------------------------------------------------------------    
if __name__ == '__main__':
    
    # Dicomdaten holen, diese werden in self.dicomData ergänzt um AcquisitionYear abgelegt
    from isp.config import ispConfig
    config = ispConfig(  )
    
    print( config.dicom.toDict() )
    dicom = dicomClass("VMSDBD", config )
    
    print( "dicomPath", dicom.dicomPath )
    
    # holen ohne override
    result1, signals = dicom.retrieve( { 
                "PatientID" : '_xxxQA TB', 
                "SOPInstanceUID" : '1.2.246.352.62.1.4625604914426170283.12140466054276070541',
                "override" : False
        } )
    
    print( "result-1:", result1, signals )
    
    # holen mit override
    result2, signals = dicom.retrieve( { 
                "PatientID" : '_xxxQA TB', 
                "SOPInstanceUID" : '1.2.246.352.62.1.4625604914426170283.12140466054276070541',
                "override" : True
        } )
    
    print( "result-2:", result2, signals )
    
    # holen mit Falschen angaben
    result3, signals = dicom.retrieve( { 
                "PatientID" : '_xxxQA TB gibt es nicht', 
                "SOPInstanceUID" : '1.2.246.352.62.1.4625604914426170283.12140466054276070541',
                "override" : True
        } )
    print( "result-3:", result3, signals )
    
    # Datei löschen und erneut holen
    file = osp.join( dicom.dicomPath, "1.2.246.352.62.1.4625604914426170283.12140466054276070541.dcm")
    if osp.exists( file ):
        os.remove( file )
    else:
        print( "keine dicom Datei vorhanden", file )
        
    result4, signals = dicom.retrieve( { 
                "PatientID" : '_xxxQA TB', 
                "SOPInstanceUID" : '1.2.246.352.62.1.4625604914426170283.12140466054276070541',
                "override" : False
    } )  
    print( "result-4:", result4, signals )
    
    
    # am ende wieder löschen
    if osp.exists( file ):
        os.remove( file )
        
    dicom.closeAE()
