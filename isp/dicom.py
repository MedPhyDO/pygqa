# -*- coding: utf-8 -*-

"""
There are two types of AEs:

* SCP (Service Class Provider) which can be thought of as a server
* SCU (Service Class User) as a client.


CHANGELOG
=========

0.1.2 / 2022-03-28
------------------
- change debug messages

0.1.1 / 2021-04-27
------------------
- enables dicom calls via pynetdicom

0.1.0 / 2021-01-16
------------------
- First Release


"""

__author__ = "R. Bauer"
__copyright__ = "MedPhyDO - Machbarkeitsstudien des Instituts für Medizinische Strahlenphysik und Strahlenschutz am Klinikum Dortmund im Rahmen von Bachelor und Masterarbeiten an der TU-Dortmund / FH-Dortmund"
__credits__ = ["R.Bauer", "K.Loot"]
__license__ = "MIT"
__version__ = "0.1.2"
__status__ = "Prototype"

import os
import os.path as osp
import json

from typing import List

from blinker import signal
import threading
import queue

from pydicom.dataset import Dataset
from pydicom import dcmread
from pydicom.uid import generate_uid

from pynetdicom import (
    AE,
    debug_logger,
    build_role,
    evt,
    AllStoragePresentationContexts,
    ALL_TRANSFER_SYNTAXES,
    QueryRetrievePresentationContexts
)

# was soll die Klassen können
from pynetdicom.sop_class import (
    PatientRootQueryRetrieveInformationModelFind,
    PatientRootQueryRetrieveInformationModelMove,
    PatientRootQueryRetrieveInformationModelGet,

    StudyRootQueryRetrieveInformationModelFind,
    StudyRootQueryRetrieveInformationModelMove,
    StudyRootQueryRetrieveInformationModelGet,

    PatientStudyOnlyQueryRetrieveInformationModelFind,
    PatientStudyOnlyQueryRetrieveInformationModelMove,
    PatientStudyOnlyQueryRetrieveInformationModelGet,

    CTImageStorage,
    RTImageStorage,
    XRayRadiationDoseSRStorage,
    SecondaryCaptureImageStorage # CT-summary

)

from pynetdicom import sop_class

#debug_logger()

import logging
logger = logging.getLogger( "MQTT" )
#logger.level = 10 # 0 - NOTSET, 10 - DEBUG, 20 - INFO, 30 - WARNING, 40 - ERROR, 50 - CRITICAL

# defaults für die query Rückgaben diese sind gestaffelt IMAGE beinhaltet alle davor
#
dicomQueryDefaults = {
    "PATIENT": {
        "QueryRetrieveLevel": "PATIENT",
        "PatientID": "*",
        "PatientName": None,
        "PatientBirthDate": None,
    },
    "STUDY": {
        "QueryRetrieveLevel": "STUDY",
        "StudyInstanceUID": None,
        "StudyID": None,
        "StudyDate": None,
        "StudyTime": None,
        "Modality": None,
        "StudyDescription": None,
        "AccessionNumber": None
    },
    "SERIES": {
        "QueryRetrieveLevel": "SERIES",
        "SeriesInstanceUID": None,
        "Modality": None,
        "SeriesNumber": None,
        "StationName": None,

    },
    "IMAGE": {
        "QueryRetrieveLevel": "IMAGE",
        "SOPClassUID": None,
        "SOPInstanceUID": None,
        "StationName": None,
        "InstanceNumber": None,
        "ManufacturerModelName": None,
        "ProtocolName": None,

        "ExposureTime": None,
        "KVP": None,
        "ContentDate": None,
        "ContentTime": None,
        "XRayTubeCurrent": None

    }
}


class ispDicom(  ):
    """Dicom Klasse zum Abfragen eines Dicom servers.

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

    messageId : int
        id der laufenden abfrage

    """

    def __init__( self, server="VMSDBD", config=None ):
        """Klasse initialisieren

        Sicherstellen das in dicomPath ein gültiger Pfad liegt

        query_model::

        - ``P`` - Patient Root Information Model
        - ``S`` - Study Root Information Model
        - ``O`` - Patient Study Only Information Model


        """

        # Klassen defaults
        self.dicomPath: str = None
        self.server: str = None
        self.ae: AE = None
        self.implementation_class_uid = generate_uid()
        self.supported_context: List[str] = [
            sop_class.RTImageStorage,
            sop_class.XRayRadiationDoseSRStorage,
            sop_class.SecondaryCaptureImageStorage,
            sop_class.CTImageStorage,
        ]
        self.assoc = None
        self.request_mode = "c_move" # c_get
        self.request_query_model = "S"
        self.scp = None
        self.override: bool = False
        self.subPath: str = ""
        self.messageId = 0

        # konfiguration verwenden oder einlesen liegt in self.config
        if config:
            self.config = config

        self.server=server

        self.initialized = False

        # pfad zu den dicom dateien bereitstellen default: {{BASE_DIR}}/files/DICOM
        self.dicomPath = str( self.config.get( ["dicom", self.server, "local_dir"], "", replaceVariables=True ) )
        if self.dicomPath == "": # pragma: no cover
            self.dicomPath = os.path.abspath( osp.join( str(self.config.BASE_DIR), "files", "dicom" ) )
            self.config.dicom[self.server]["local_dir"] = self.dicomPath

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
        """Deleting Class (Calling destructor)

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

        # sicherheitshalber bestehende schließen
        self.closeAE()

        # Initialise the Application Entity
        assoc = None
        try:
            # Initialise the Application Entity
            aet = self.config.dicom[self.server]["aet"]
            self.ae = AE( ae_title=aet )

            # Patient Suche verwenden
            self.ae.requested_contexts = QueryRetrievePresentationContexts

            # patient level
            self.ae.add_requested_context( PatientRootQueryRetrieveInformationModelFind )
            self.ae.add_requested_context( PatientRootQueryRetrieveInformationModelMove )
            self.ae.add_requested_context( PatientRootQueryRetrieveInformationModelGet )

            # Study level
            self.ae.add_requested_context( StudyRootQueryRetrieveInformationModelFind )
            self.ae.add_requested_context( StudyRootQueryRetrieveInformationModelMove )
            self.ae.add_requested_context( StudyRootQueryRetrieveInformationModelGet )

            # patientStudyOnly
            self.ae.add_requested_context( PatientStudyOnlyQueryRetrieveInformationModelFind )
            self.ae.add_requested_context( PatientStudyOnlyQueryRetrieveInformationModelMove )
            self.ae.add_requested_context( PatientStudyOnlyQueryRetrieveInformationModelGet )

            # Add the requested presentation context (Storage SCP)
            self.ae.add_requested_context( CTImageStorage )
            self.ae.add_requested_context( XRayRadiationDoseSRStorage )

            # use all Storages and Transfers
            storage_sop_classes = [
                cx.abstract_syntax for cx in AllStoragePresentationContexts
            ]
            for uid in storage_sop_classes:
                self.ae.add_supported_context(uid, ALL_TRANSFER_SYNTAXES)

            # bei den handlern wird nicht auf EVT_REJECTED geprüft, da offline ja möglich ist
            handlers=[
                ( evt.EVT_ESTABLISHED , self.handle_EVENT),
                #( evt.EVT_REJECTED , self.handle_event),
                ( evt.EVT_RELEASED, self.handle_EVENT),
                # für send_c_get
                ( evt.EVT_C_STORE, self.handle_STORE),
            ]

            # requestmode für den server festlegen: c_move oder c_get
            self.request_mode = self.config.get( ["dicom", self.server, "request_mode"], "c_move" )

            # request_query_model für den server festlegen: P-patient S-series O-PS only
            self.request_query_model = self.config.get( ["dicom", self.server, "request_query_model"], "S" )

            # Create an SCP/SCU Role Selection Negotiation item for CT Image Storage
            roles = []
            roles.append( build_role(CTImageStorage, scp_role=True, scu_role=True ) )
            roles.append( build_role(XRayRadiationDoseSRStorage, scp_role=True, scu_role=True) )

            # Associate with peer AE
            assoc = self.ae.associate(
                self.config.dicom[self.server]['server_ip'],
                self.config.dicom[self.server]['server_port'],
                ae_title=self.config.dicom[self.server]['aec'],
                evt_handlers=handlers,
                ext_neg=roles
            )

        except:  # pragma: no cover
            pass

        self.assoc = None
        status = 0xC0FF

        if assoc and assoc.is_established:
            self.assoc = assoc
            status = 0x0000
            logger.debug('dicomClass.initAE: Verbindung hergestellt')
        else:  # pragma: no cover
            logger.warning('dicomClass.initAE: Association rejected, aborted or never connected')

        return status

    def _start_server(self, evt_name:str="EVT_C_STORE"):

        # EVT_C_STORE oder EVT_C_FIND

        # Verbindung ggf herstellen
        if not self.assoc:
            status = self.initAE()
            # und testen
            if not self.assoc: # pragma: no cover
                logger.warning("dicomClass._retrieve: Verbindung fehlgeschlagen")
                signal( 'dicom.{}'.format( evt_name ) ).send( {
                    "name": evt_name,
                    '_is_cancelled': True,
                    "status": status,
                    "msg" : "initAE: Verbindung fehlgeschlagen",
                    # "dataset": None,
                } )
                return status

        # wenn noch nicht passiert server zum empfangen der daten starten
        if not self.scp:
            # message id zurpcksetzen
            self.messageId = 0
            #print( self.scp )

            # handler zum empfang der Daten bereitstellen
            handlers = [
                 ( evt.EVT_C_STORE, self.handle_STORE),

                 ( evt.EVT_ACCEPTED, self.handle_EVENT),
                 ( evt.EVT_ABORTED, self.handle_EVENT),

                 ( evt.EVT_REJECTED, self.handle_EVENT),
                 ( evt.EVT_RELEASED, self.handle_EVENT),
                 ( evt.EVT_REQUESTED, self.handle_EVENT),

                 ( evt.EVT_DIMSE_SENT, self.handle_EVENT),
                 ( evt.EVT_DIMSE_RECV, self.handle_EVENT),

            ]

            # Server starten um die Daten zu empfangen storage SCP on port listen_port
            self.ae.ae_title = self.config.dicom[self.server]['aet']
            sig_msg = None
            try:
                logger.debug( "dicomClass._start_server:  start server" )
                # If set to non-blocking then a running ``ThreadedAssociationServer``
                # instance will be returned. This can be stopped using ``shutdown()``.
                self.scp = self.ae.start_server(
                    ('', self.config.dicom[self.server]['listen_port']),
                    block=False, # Abfrage über Thread handlers
                    evt_handlers=handlers
                )
            except OSError as e: # pragma: no cover
                #print( "dicomClass.retrieve: 0xC515 - {}".format( str(e) )  )
                logger.error( "dicomClass._start_server: 0xC515 - {}".format( str(e) ) )
                sig_msg = {
                    "name": evt_name,
                    "_is_cancelled": True,
                    "status": 0xC515,
                    "msg" : "{}".format( str(e) )
                }
            except: # pragma: no cover
                logger.error( "dicomClass._retrieve: ERROR start listen server" )
                sig_msg = {
                    "name": evt_name,
                    "_is_cancelled": True,
                    "status": 0xC515,
                    "msg" : "Fehler bei start listen server"
                }

            # send signal on error
            if not sig_msg == None:
                signal( 'dicom.{}'.format( evt_name ) ).send( sig_msg )
                return 0xC515

        return 0x0000

    def closeAE( self, status=0x0000 ):
        """shutdown scp und Release association.

        Parameters
        ----------
        status : int, optional
            Grund des closeAE mitgeben. The default is 0x0000.

        Returns
        -------
        None.

        """
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

    def getInfo( self ):
        """Wie print( self.ae ) gibt aber ein object zurück

        Returns
        -------
        obj : dict
            dict mit Server Informationen.

        """
        obj = {
            "dicomPath": self.dicomPath
        }
        if self.ae:
            obj["title"] = self.ae.ae_title
            obj["active_associations"] = len(self.ae.active_associations)
            obj["maximum_associations"] = self.ae.maximum_associations
            obj["acse_timeout"] = self.ae.acse_timeout
            obj["dimse_timeout"] = self.ae.dimse_timeout
            obj["network_timeout"] = self.ae.network_timeout

            obj["associations"] = []
            for assoc in self.ae.active_associations:
                associations = {
                    "ae_title" : assoc.remote['ae_title'],
                    "address" : assoc.remote['address'],
                    "port" : assoc.remote['port'],
                    "accepted_contexts" : []
                }
                for cx in assoc.accepted_contexts:
                    #print( "cx", cx )
                    associations["accepted_contexts"].append( {
                       "Context" : cx.abstract_syntax,
                       "SCP_role" : cx.as_scp,
                       "SCU_role" : cx.as_scu
                    })
                obj["associations"].append( associations )

        return obj

    def handle_EVENT(self, event):
        """Event Verarbeitung
        sendet in evt_handlers definierte events über signal weiter

        Parameters
        ----------
        event : pynetdicom.evt
            Ein von pynetdicom gesendeter event.

        Returns
        -------
        None.

        """
        logger.info('dicomClass.handle_EVENT: {}'.format( event.event.name ) )

        signal( 'dicom.{}'.format( event.event.name ) ).send( {
            "name": event.event.name,
            "event": event,
            "status":0x0000,
            "msg":""
        } )

    def handle_STORE(self, event ):
        """Handle a C-STORE request event.
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


        """

        logger.debug('dicomClass.handle_STORE')

        ds = event.dataset
        context = event.context

        status = 0x0000

        # Ort der Dicomdaten bestimmen
        local_path = osp.join( self.dicomPath, self.subPath )

        # ggf anlegen
        if not os.path.isdir( local_path ):
            logger.debug('dicomClass.handle_STORE: erzeuge subdir={}'.format( local_path ) )
            os.makedirs( local_path )

        # Datei schon vorhanden, oder nicht
        exists, filename = self.archive_hasSOPInstanceUID( ds.SOPInstanceUID )

        logger.debug( "dicomClass.handle_STORE: {}".format( ds.SOPInstanceUID + ".dcm" ) )
        msg = ""

        # DICOM Daten schreiben
        if not exists or self.override:
            # Wie werden die Bilddaten inerpretiert
            ds.is_little_endian = True
            ds.is_implicit_VR = True

            # Datei speichern
            #   write_like_original=False um DCIM zu schreiben
            try:
                ds.save_as( filename , write_like_original=False )
                msg = "Datei abgelegt: {}".format( filename )
            except IOError as e:  # pragma: no cover
                # 0xC511 - Unhandled exception raised by the user’s implementation of the on_c_move callback
                status = 0xC511
                msg = "io_error: {}".format( str(e) )
                logger.warning( "dicomClass.handle_STORE(io_error) [{}]: {}".format(status, filename ) )
            except: # pragma: no cover
                status = 0xC512
                msg = "io_error: {}".format( filename )
                logger.warning( "dicomClass.handle_STORE(save_error) [{}]: {}".format(status, filename )  )

        else: # pragma: no cover
            logger.debug( "Datei vorhanden: {}".format( filename ) )
            msg = "Datei vorhanden: {}".format( filename )

        logger.debug( "dicomClass.handle_STORE: {}".format( ds.SOPInstanceUID + ".dcm" ) )

        signal( 'dicom.EVT_C_STORE' ).send( {
            "name": event.event.name,
            "_is_cancelled": False,
            "dataset":ds,
            "status":status,
            "msg":msg
        } )

        return status


    def echo(self):
        """

        https://github.com/pydicom/pynetdicom/issues/419

        Returns
        -------
        None.

        """
        from pynetdicom.sop_class import VerificationSOPClass
        #debug_logger()
        # Initialise the Application Entity
        ae = AE( ae_title=self.config.dicom[self.server]["aet"] )
        ae.add_requested_context(VerificationSOPClass)

        # qr_addr: the IP address of the QR SCP, as `str`
        # qr_port: the port that the QR SCP is listening on as `int`
        assoc = ae.associate(
             addr = self.config.dicom[self.server]['server_ip'],
             port = self.config.dicom[self.server]['server_port']
        )
        if assoc.is_established:
            status = assoc.send_c_echo()

            print( "status", status )

            assoc.release()
        else:
            print( "not established")


    def query( self, ds=None ):
        """Führt eine DICOM Abfrage durch.

        Parameters
        ----------
        ds : Dataset
            Dataset für die Suche und Rückgabe. The default is None.

        Returns
        -------
        results : list
            gefundene daten
        status : hex
            Rückgabecode von send_c_find::

            C-FIND related - 0xC300 to 0xC3FF

            Zusätzlich:

            - 0xC3F1 - keine PatientID
            - 0xC0FF - initAE: Verbindung fehlgeschlagen

        """
        results = []

        if not ds: # pragma: no cover
            logger.warning("dicomClass.query: kein Dataset")
            return results, 0xC3F1

        # Verbindung ggf herstellen
        if not self.assoc:
            status = self.initAE()
            # und testen
            if not self.assoc: # pragma: no cover
                #print("dicomClass.query: Verbindung fehlgeschlagen")
                logger.warning("dicomClass.query: Verbindung fehlgeschlagen")
                return results, status

        logger.warning("dicomClass.query: Abfrage durchführen")
        # Abfrage durchführen
        responses = self.assoc.send_c_find(
            ds,
            query_model=PatientRootQueryRetrieveInformationModelFind
        )
        # Rückgabe auswerten
        for (response_status, rds) in responses:

            # status code bestimmen
            status = 0xC3F3
            if response_status:
                status = response_status.Status

            # je nach status
            if status in (0xFF00, 0xFF01) and rds:
               # If the status is 'Pending' then `identifier` is the C-FIND response
               results.append( rds )
            elif status == 0x0000:
                # abfrage wurde komplett durchgeführt
                # print("identifier:", identifier)
                pass
            else: # pragma: no cover
                #print('dicomClass.query: Connection timed out, was aborted or received invalid response: 0x{0:04x}'.format( status ))

                logger.warning('dicomClass.query: Connection timed out, was aborted or received invalid response: 0x{0:04x}'.format( status ) )

        return results, status

    def PATIENT( self, query:dict={}  ):
        """Führt eine suche nach PATIENT durch.

        Wie query mit einem default Dataset

        Parameters
        ----------
        query : dict, optional
            query parameter für ds. The default is {}.

        Returns
        -------
        results : list
            gefundene daten
        status : hex
            Rückgabecode von send_c_find::

        """
        ds_model = dicomQueryDefaults["PATIENT"].copy()
        ds_model.update( query )

        ds = Dataset()
        for name, value in ds_model.items():
           ds.__setattr__(name, value)

        # Abfrage durchführen
        return self.query( ds )

    def STUDY( self, query:dict={}  ):
        """Führt eine suche nach STUDY durch.

        Wie query mit einem default Dataset

        Parameters
        ----------
        query : dict, optional
            query parameter für ds. The default is {}.

        Returns
        -------
        results : list
            gefundene daten
        status : hex
            Rückgabecode von send_c_find::

        """
        ds_model = dicomQueryDefaults["PATIENT"].copy()
        ds_model.update( dicomQueryDefaults["STUDY"] )
        ds_model.update( query )

        ds = Dataset()
        for name, value in ds_model.items():
           ds.__setattr__(name, value)

        # Abfrage durchführen
        return self.query( ds )

    def SERIES( self, query:dict={}  ):
        """Führt eine suche nach SERIES durch.

        Wie query mit einem default Dataset

        Parameters
        ----------
        query : dict, optional
            query parameter für ds. The default is {}.

        Returns
        -------
        results : list
            gefundene daten
        status : hex
            Rückgabecode von send_c_find::

        """
        ds_model = dicomQueryDefaults["PATIENT"].copy()
        ds_model.update( dicomQueryDefaults["STUDY"] )
        ds_model.update( dicomQueryDefaults["SERIES"] )
        ds_model.update( query )

        ds = Dataset()
        for name, value in ds_model.items():
           ds.__setattr__(name, value)

        # Abfrage durchführen
        return self.query( ds )

    def IMAGE( self, query:dict={}  ):
        """Führt eine suche nach IMAGE durch.

        Wie query mit einem default Dataset

        Parameters
        ----------
        query : dict, optional
            query parameter für ds. The default is {}.

        Returns
        -------
        results : list
            gefundene daten
        status : hex
            Rückgabecode von send_c_find::

        """
        ds_model = dicomQueryDefaults["PATIENT"].copy()
        ds_model.update( dicomQueryDefaults["STUDY"] )
        ds_model.update( dicomQueryDefaults["SERIES"] )
        ds_model.update( dicomQueryDefaults["IMAGE"] )
        ds_model.update( query )

        ds = Dataset()
        for name, value in ds_model.items():
           ds.__setattr__(name, value)

        # Abfrage durchführen
        return self.query( ds )

    def _retrieve( self, PatientID:str=None,
                 StudyInstanceUID:str=None,
                 SeriesInstanceUID:str=None,
                 SOPInstanceUID:str=None,
                 override:bool=False,
                 subPath:str="",
                 ds=None
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
        ds : Dataset, optional
            Angaben des Dataset statt PatientID, StudyInstanceUID, SeriesInstanceUID oder SOPInstanceUID verwenden

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

        # override Status merken
        self.override = override

        # subPath merken
        self.subPath = subPath

        if not ds:
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

        # print( "do - retreive ds:\n", ds)

        # info QueryRetrieveLevel ausgeben
        logger.debug( "dicomClass._retrieve: QueryRetrieveLevel {}".format( ds.QueryRetrieveLevel ) )

        # bei image level versuchen aus dem Dateiarchiv zu lesen statt vom Server zu holen
        # fixme - bei Angabe von SOPInstanceUID statt QueryRetrieveLevel
        if ( hasattr(ds, 'SOPInstanceUID')) and not ds.SOPInstanceUID == None and not override:
        #if ds.QueryRetrieveLevel == 'IMAGE' and not override:
            # info
            logger.debug( "dicomClass._retrieve: search archive {}".format( ds.SOPInstanceUID ) )
            # file aus dem archiv laden
            instance = self.archive_loadSOPInstanceUID( ds.SOPInstanceUID )
            # konnte gelesen werden dann raus hier
            if instance:

                logger.debug( "dicomClass._retrieve: load archive {}".format( ds.SOPInstanceUID ) )

                signal( 'dicom.EVT_C_STORE').send( {
                    "name": "EVT_C_STORE",
                    '_is_cancelled': False,
                    "status":0x0000,
                    "msg" : "load archive",
                    "dataset": instance, # Dataset mitgeben (fertig)
                } )
                return 0x0000
            else:
                logger.info( "dicomClass._retrieve: no archive {}".format( ds.SOPInstanceUID ) )

        #
        # ansonsten wird hier versucht neu zu laden
        #

        status = self._start_server("EVT_C_STORE")

        if not status == 0x000:
            return status

        # print( "dicomClass.assoc.send_c_xxx", self.assoc.is_established, self.scp, self.assoc )

        # ohne try

        '''
            convert PSO to UID

            - ``P`` - 1.2.840.10008.5.1.4.1.2.1.2 -
              *Patient Root Information Model - MOVE*
            - ``S`` - 1.2.840.10008.5.1.4.1.2.2.2 -
              *Study Root Information Model - MOVE*
            - ``O`` - 1.2.840.10008.5.1.4.1.2.3.2 -
              *Patient Study Only Information Model - MOVE*
        '''

        # Retrieve Error
        result = 0xC512
        responses =  None
        self.messageId += 1
        if self.request_mode == "c_get":
            query_model = StudyRootQueryRetrieveInformationModelGet
            if self.request_query_model == "P":
               query_model= PatientRootQueryRetrieveInformationModelGet
            elif self.request_query_model == "O":
                query_model= PatientStudyOnlyQueryRetrieveInformationModelGet
            # c_get durchführen
            if self.assoc.is_established:
                responses = self.assoc.send_c_get(
                    ds,
                    query_model = query_model,
                    msg_id = self.messageId
                )
            else:
                print( "dicomClass._retrieve send_c_get():  assoc is not established" )

        else:
            query_model = StudyRootQueryRetrieveInformationModelMove
            if self.request_query_model == "P":
               query_model= PatientRootQueryRetrieveInformationModelMove
            elif self.request_query_model == "O":
                query_model= PatientStudyOnlyQueryRetrieveInformationModelMove
            # c_move durchführen
            if self.assoc.is_established:
                responses = self.assoc.send_c_move(
                    ds,
                    self.config.dicom[self.server]['aet'],
                    query_model = query_model,
                    msg_id = self.messageId
                )
            else:
                print( "dicomClass._retrieve send_c_move():  assoc is not established" )


        if responses:
            i = 0
            for (status, identifier) in responses:
                i += 1
                if status:
                    result = status.Status
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
                    # 0xB000 -Warning - Sub-operations complete, one or more or warnings

                else:
                    # Association._wrap_get_move_responses
                    # print("Connection timed out", responses )
                    logger.warning('dicomClass._retrieve - Connection timed out, was aborted or received invalid response')
        else:
            pass

        logger.debug("dicomClass._retrieve: DICOM Daten holen: {} - {}".format( hex(result), SOPInstanceUID ) )

        # wenn nicht pending (retrieve_thread übernimmt) EVT_C_STORE mit _is_cancelled senden
        # 0xff00 - Pending
        # 0x0000 - Success
        if not result in ( 0x0000, 0xff00):
            signal( 'dicom.EVT_C_STORE').send( {
                    "name": "EVT_C_STORE",
                    "_is_cancelled": True,
                    "status": result,
                    "hex": hex(result),
                    "msg": "run EVT_C_STORE"
            } )

        return result


    def archive_hasSOPInstanceUID(self, SOPInstanceUID):
        """Prüft ob eine SOPInstanceUID schon im File Archiv vorhanden ist

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
        """

        filename = osp.join( self.dicomPath, self.subPath, SOPInstanceUID + ".dcm" )

        return os.path.isfile( filename ), filename

    def archive_loadSOPInstanceUID( self, SOPInstanceUID ):
        """Lädt eine Dicomdatei mit SOPInstanceUID aus dem Archiv

        Parameters
        ----------
        SOPInstanceUID : str
            Eine SOPInstanceUID.

        Returns
        -------
        ds : TYPE
            DESCRIPTION.

        """

        ds = None
        exists, filename = self.archive_hasSOPInstanceUID( SOPInstanceUID )

        if exists:
            try:
                # mit force True einlesen um trotz fehlender headerdaten einzulesen
                ds = dcmread(filename, force=True)
            except: # pragma: no cover
                # alle sonstigen Fehler abfangen
                logger.error("Fehler beim lesen der DICOM Datei")
                pass

        return ds

    def archive_deleteSOPInstanceUID(self, SOPInstanceUID):
        """Löscht ein Dataset aus dem File Archiv.

        Parameters
        ----------
        SOPInstanceUID : TYPE
            Eine SOPInstanceUID.

        Returns
        -------

        filename : str
            Der entfernte Dateiname
        """

        exists, filename = self.archive_hasSOPInstanceUID( SOPInstanceUID )

        if exists:
            os.remove( filename )

        return filename

    def retrieve( self, params={} ):
        """Holt DICOM Daten mit threading und event Benachrichtigung.

        Ruft _retrieve mit den Parametern auf

        suchen nach
            Received unexpected C-MOVE service message in pynetdicom Association _serve_request
            aufgerufen von _run_reactor

        Parameters
        ----------
        params : dict, optional
            DESCRIPTION. The default is {}.

        Returns
        -------
        instances : list
            gefundene Dataset Instances.
        signals: list

        """
        instances = []
        signals = []

        result_available = threading.Event()
        mq = queue.Queue()

        def _C_STORE( signal ):
            signals.append(signal)
            if signal["_is_cancelled"] == True:
                # Vorgang abbrechen
                result_available.set()
            elif signal["_is_cancelled"] == False:

                if "dataset" in signal:
                    # Ergebnis setzen und abbrechen
                    instances.append( signal["dataset"] )
                    result_available.set()

        def _RELEASED( signal ):
            signals.append( signal )
            result_available.set()

        def _REJECTED( signal ):
            signals.append( signal )
            result_available.set()

        def _ABORTED( signal ):
            signals.append( signal )
            result_available.set()

        signal( 'dicom.EVT_C_STORE' ).connect( _C_STORE )
        signal( 'dicom.EVT_REJECTED' ).connect( _REJECTED )
        signal( 'dicom.EVT_RELEASED' ).connect( _RELEASED )
        signal( 'dicom.EVT_ABORTED' ).connect( _ABORTED )

        # Als Thread aufrufen, über mq.get() wird die Rückgabe von  _retrieve abgerufen
        thread = threading.Thread( target=lambda q, args: q.put( self._retrieve( **args ) ), args=( mq, params ) )
        thread.start()

        # nach max. 10 sec den Vorgang abbrechen
        while not result_available.wait( timeout=10 ):
            result_available.set()


        return instances, signals

