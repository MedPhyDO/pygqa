# -*- coding: utf-8 -*-

'''
Das eigentliche starten der app wird über run erledigt

'''

__author__ = "R. Bauer"
__copyright__ = "MedPhyDO - Machbarkeitsstudien des Instituts für Medizinische Strahlenphysik und Strahlenschutz am Klinikum Dortmund im Rahmen von Bachelor und Masterarbeiten an der TU-Dortmund / FH-Dortmund"
__credits__ = ["R.Bauer", "K.Loot"]
__license__ = "MIT"
__version__ = "0.1.5"
__status__ = "Prototype"

import logging
logger = logging.getLogger( "ISP" )
import os
from pathlib import Path
import json
import time 

from isp.config import ispConfig

from app.db import gqadb

from app.api import gqa

from isp.webapp import ispBaseWebApp
from isp.safrs import db, system

class system( system ):

    @classmethod
    def _extendedSystemCheck(self):
        """filled Stub Function for api_list (Systeminformationen)

        Returns
        -------
        dict, string

        """

        logger.info("_extendedSystemCheck - START")
        def checkPath( path, info ):
            html = ""
            _path = Path(path)
            if not os.path.exists( path ):
                try:
                    os.makedirs( path )
                except IOError as e:
                    info_class = "danger"
                    info_text = "{} kann nicht erzeugt werden.".format( info )
                    html += '<div class="alert alert-{} ">{}</div>'.format( info_class, info_text )
    
            if os.path.exists( path ):
                info_class = "success"
                info_text = "{} ist vorhanden.".format( info )
            else:
                info_class = "danger"
                info_text = "{} ist nicht vorhanden.".format( info )
            html += '<div class="alert alert-{} ">{}</div>'.format( info_class, info_text )

            if os.path.isdir( path ):
                info_class = "success"
                info_text = "{} ist ein Verzeichnis.".format( info )
            else:
                info_class = "danger"
                info_text = "{} ist kein Verzeichnis.".format( info )
            html += '<div class="alert alert-{} ">{}</div>'.format( info_class, info_text )

            if os.access(path, os.W_OK):
                info_class = "success"
                info_text = "{} ist beschreibbar.".format( info )
            else:
                info_class = "danger"
                info_text = "{} ist nicht beschreibbar.".format( info )
            html += '<div class="alert alert-{} ">{}</div>'.format( info_class, info_text )

            return html

        config = ispConfig()
        html = "<h4>System Check</h4>"

        from isp.config import dict_merge

        # --------------- Aria Datenbank
        from app.aria import ariaClass
        _database_key = config.get( "database.servername", "" )

        connect = None
        aria = None
        check_image_uid = None
        check_patient_id = None
        loaded_config = config.get( ["database", _database_key] )
        db_config = {
            "dbname":"notset",
            "host":"notset/unused",         
            "user":"notset",
            "password":"notset",
            "engine":"notset/unused",
            "dsn":"notset/unused"
        }
        if loaded_config:
            db_config = dict_merge( db_config, loaded_config.toDict() )
            aria = ariaClass( _database_key, config )
            connect = aria.openDatabase( _database_key )
        else:
             html += '<div class="alert alert-danger">Kein passender Eintrag für <b>server.database.servername</b></div>'

        html += '<div class="alert alert-dark" >Prüfe Datenbankzugriff <span class="badge badge-info">database.servername</span>: <b>{}</b> - Konfiguration:'.format( _database_key )
        db_config_copy = db_config.copy()
        db_config_copy["password"] = "******"
        html += '</br> <pre>{}</pre>'.format( json.dumps( db_config_copy, indent=2 ) )
        info_text = "Der Zugriff auf die Datenbank dbname:<b>{dbname}</b>, user:<b>{user}</b>".format( **db_config )
        if not connect:
            info_class = "danger"
            info_text = "{} ist nicht möglich.".format( info_text )
        else:
            info_class = "success"
            info_text = "{} ist möglich.".format( info_text )
            db_version = aria.getDbVersion( )
            info_text += "<br>{}".format( db_version.replace( "\\n", "<br>").replace('\\t', '') )

        html += '<div class="alert alert-{} ">{}</div>'.format( info_class, info_text )

        if connect:
            html += '<div class="alert alert-dark" >Prüfe Patienten für <span class="badge badge-info">units</span> - Konfiguration:'
            html += '</br> <pre>{}</pre>'.format( json.dumps( config.get( "units" ).toDict(), indent=2 ) )
            for name, unit in config.get( "units" ).items():
                if not unit:
                    continue
                sql = "SELECT PatientSer, PatientId, FirstName, LastName FROM [{dbname}].[dbo].[Patient] [Patient]"
                sql = sql + " WHERE [PatientId] = '{}' ".format( name )
                result = aria.execute( sql )

                html += aria.lastExecuteSql

                info_text = "PatientId: <b>{}</b>".format( name )
                if len( result ) > 0:
                    info_text = "{} ist vorhanden.".format( info_text )
                    info_text += '</br> <pre>{}</pre>'.format( json.dumps( result[0], indent=2 ) )
                    info_class = "success"
                else:
                    info_text = "{} ist nicht vorhanden.".format( info_text )
                    info_class = "danger"

                html += '<div class="alert alert-{} ">{}'.format( info_class, info_text )

                if len( result ) > 0:
                    html += "<br>Prüfe Tags im Datenbankfeld '[Radiation].[Comment]' für PatientId: <b>{}</b> ".format( name )
                    tags = aria.getTags( name )
                    if tags and len( tags ) > 0:
                        info_text = "<b>{}</b> Tags sind vorhanden.".format( len( tags ) )
                        info_class = "success"
                    else:
                        info_text = "Keine Tags vorhanden."
                        info_class = "danger"
                    html += '<div class="alert alert-{} ">{}</div>'.format( info_class, info_text )
                    
                    html += "<br>Prüfe Bilder für PatientId: <b>{}</b> ".format( name )
                    images, sql = aria.getImages( name )
                    if len(images) > 0:
                        check_patient_id = images[0]["PatientId"]
                        check_image_uid = images[0]["SliceUID"]
                        info_text = "<b>{}</b> Bilder sind vorhanden.".format( len( images ) )
                        info_class = 'success'
                    else:
                        info_text = "Keine Bilder vorhanden."
                        info_class = "warning"                        
                    html += '<div class="alert alert-{} ">{}</div>'.format( info_class, info_text )                
                html += "</div>"
            html += "</div>"
        html += "</div>"

        # --------------- ariaDicomClass
        from app.ariadicom import ariaDicomClass

        _dicom_key = config.get( "dicom.servername", "" )
        adc = ariaDicomClass( _database_key, _dicom_key, config )

        loaded_config = config.get( ["dicom", _dicom_key] )

        dicom_config = {
            "aec" : "notset",
            "server_ip": "notset",
            "server_port": "notset",
            "aet":  "notset",
            "listen_port": "notset"
        }
        if loaded_config:
            dicom_config = dict_merge(dicom_config, loaded_config.toDict() )
        else:
            html += '<div class="alert alert-danger">Kein passender Eintrag für <b>server.dicom.servername</b></div>'

        status = adc.initAE()

        # --------------- resultsPath
        resultsPath = adc.initResultsPath()
        configResultsPath = adc.config.get("resultsPath", ".")
        path = Path(resultsPath).resolve()
        html += '<div class="alert alert-dark" >Prüfe <span class="badge badge-info">resultsPath</span>: <b>{}</b> => <b>{}</b>'.format( configResultsPath, path )
        html += checkPath(resultsPath, '<span class="badge badge-info">resultsPath</span>')
        useFile = adc.pd_results.useFile
        html += 'Ergebnisse in einer Datei speichern: <span class="badge badge-{}">{}</span>'.format('success' if useFile else 'warning', useFile)
        useDB = adc.pd_results.useDB
        html += '<br>Ergebnisse in einer Datenbank speichern: <span class="badge badge-{}">{}</span>'.format('success' if useDB else 'warning', useDB)
        html += "</div>"
       
        # --------------- DICOM
        html += '<div class="alert alert-dark" >Prüfe Dicom <span class="badge badge-info">dicom.servername</span>: <b>{}</b> - Konfiguration:'.format( _dicom_key )
        html += '<pre>{}</pre>'.format( json.dumps( dicom_config, indent=2 ) )
        html += '<br>Server Settings - AE Title (aec): <b>{aec}</b> - IP (server_ip): <b>{server_ip}</b> - Port (server_port): <b>{server_port}</b><br>'.format( **dicom_config )
        html += '<br>Application Entity Map Entry - AE Title (aet): <b>{aet}</b> - Port (listen_port): <b>{listen_port}</b>'.format( **dicom_config )
        
        path = Path( adc.dicomPath ).resolve()
        html += '<div class="alert alert-dark" >Prüfe Verzeichnis: <span class="badge badge-info">dicom.{}.local_dir</span>: <b>{}</b> => <b>{}</b>'.format( _dicom_key, dicom_config.get("local_dir", "notset" ), path )        
        html += checkPath( adc.dicomPath , '<span class="badge badge-info">dicom.{}.local_dir</span>'.format(_dicom_key))
        html += "</div>"


        dicom_info = adc.getInfo()
        
        if status == 0x0000:
            info_class = "success"
            info_text = "Dicom Zugriff ist möglich. Associations: "
            for association in dicom_info["associations"]:
                association["ae_title"] = association["ae_title"] # .decode().strip()
                info_text += '</br> <pre>{}</pre>'.format( json.dumps( association, indent=2 ) )
        else:
            info_class = "danger"
            info_text = "Dicom Zugriff ist nicht möglich. ErrorCode: 0x{0:04x}.".format( status )

        html += '<div class="alert alert-{} ">{}</div>'.format( info_class, info_text )
        #
       
        html += '<div class="alert alert-dark" >Prüfe DICOM GET'           
        if check_image_uid:
            html += " mit UID: <b>{}</b><br>".format( check_image_uid )
            
            result, signals = adc.retrieve( {
                "SOPInstanceUID" : check_image_uid,
                "override" : True,
                "subPath" : "systeminfo"
            })
            
            if len(signals) > 0:
                for signal in signals:
                    exists, filename = adc.archive_hasSOPInstanceUID( check_image_uid )
                    html += "<br>Signal - name:<b>{name}</b> status:<b>{status}</b> msg:<b>{msg}</b>".format( **signal )
                    # hole das Dateidatum 
                    if exists:
                        mtime = os.path.getmtime(filename)
                        localtime = time.localtime(mtime)
                        localtime_string = time.strftime('%Y-%m-%d %H:%M:%S', localtime)
                        info_class = "success"
                        info_text = 'Datei <b>{}</b> ist vorhanden. Dateidatum: <b>{}</b>'.format(filename, localtime_string)
                    else:
                        info_class = "danger"
                        info_text = "Datei <b>{}</b> wurde nicht geholt.".format( filename )


                    html += '<div class="alert alert-{} ">{}</div>'.format( info_class, info_text )
            else:
                html += '<div class="alert alert-danger" >Das DICOM Bild konnte nicht geholt werden</div>'
        
        else:
            html += '<div class="alert alert-warning" >Prüfung nicht möglich. Es wurde noch kein Bild für den Patienten gemacht.</div>'
        html += "</div>"

        adc.closeAE()
        html += "</div>"

        # --------------- logging
        logging_config = config.get( "server.logging" )
        baseTopic = config.get( "server.webserver.name", "webapp" )
        html += '<div class="alert alert-dark" ><span class="badge badge-info">Logging</span> - Konfiguration:'
        html += '<pre>{}</pre>'.format( json.dumps( logging_config, indent=2 ) )

        # --------------- websocket
        if not config.get( "server.logging.handler.websocket", False ):
            html += '<div class="alert alert-info" >Websocket ist deaktiviert'
        else: 
            html += '<div class="alert alert-success" >Websocket ist aktiviert '
            html += '<button type="button" class="btn btn-primary" onClick="websocketTest( this )">Prüfen</button>'
            # TODO: websocket testen
            info_class = "info"
            info_text = ''

            html += '<div id="websocket-results" class="alert alert-{}">{}</div>'.format( info_class, info_text )
            html += '''
            <script>
   
            var result_box_ws = document.querySelector("#websocket-results");
            if ( typeof app.socket === "object" ) {
                if ( !app.socket?._sysinfo ) {
                    app.socket._sysinfo = true;
                    app.socket.on('publish', function(msg) {
                        topics = msg.topic.split('/')
                        if (msg.topic === app.socket.basetopic + '/stat/echo' ) {
                            result_box_ws.className = "alert alert-success";
                            result_box_ws.innerHTML = msg.payload;                
                        } else if (msg.topic === app.socket.basetopic + '/stat/status' ) {
                            result_box_ws.className = "alert alert-success";
                            result_box_ws.innerHTML = 'Websocket Zugriff ist möglich';  
                        }
                    })
                    function websocketTest( btn ){
                        result_box_ws.className = "alert alert-danger";
                        result_box_ws.innerHTML = "Websocket Prüfung nicht erfolgreich";
                        app.socket.emit('publish', {
                            topic: app.socket.basetopic + '/cmnd/echo',
                            payload: 'Websocket Prüfung erfolgreich'
                        })
                    }
                }
            }
            </script>
            '''
            pass
        html += "</div>"

        # --------------- MQTT
        mqtt_config = config.get( "server.mqtt" )
        mqtt_config_copy = mqtt_config.copy()
        mqtt_config_copy.password = "********"
        if not config.get( "server.logging.handler.mqtt", False ):
            html += '<div class="alert alert-info" >MQTT ist deaktiviert'
        else:
            html += '<div class="alert alert-dark" ><span class="badge badge-info">server.mqtt</span> - Konfiguration:'
            html += '<pre>{}</pre>'.format( json.dumps( mqtt_config_copy.toDict(), indent=2 ) )

            mqtt = config.mqttGetHandler()
            if not mqtt:
                info_class = "danger"
                info_text = "MQTT Zugriff ist nicht möglich."
            else:
                info_class = "info"
                info_text = 'MQTT Zugriff ist eingerichtet. <button type="button" class="btn btn-primary" onClick="mqttTest( this )">Prüfen</button>'

            html += '<div id="MQTT-checkline" class="alert alert-{} ">{}<div id="MQTT-results" class="alert"></div></div>'.format( info_class, info_text )

        html += "</div>"
        html += "</div>"
        html += '''
            <script>
            var box = document.querySelector("#MQTT-checkline");
            var result_box = document.querySelector("#MQTT-results");
            if ( typeof app.clientMqtt === "object" ) {
                app.clientMqtt.subscribe( "MQTT/test", function( msg ) {
                    box.className = "alert alert-success";
                    result_box.className = "alert alert-success";
                    result_box.innerHTML = "MQTT Prüfung erfolgreich";
                } );
            }
            function mqttTest( btn ){
                box.className = "alert alert-info";
                result_box.className = "";
                if ( typeof app.clientMqtt === "object" ) {
                    result_box.className = "alert alert-danger";
                    result_box.innerHTML = "MQTT Prüfung nicht erfolgreich.";
                    app.clientMqtt.publish( "MQTT/test", { "test":"MQTT" } );
                } else {
                    result_box.className = "alert alert-warning";
                    result_box.innerHTML = "kein clientMqtt vorhanden";
                }
            }
            </script>
        '''

        logger.info("_extendedSystemCheck - END")
        return {}, html

def importPandas( filename, conn:str=None ):
    import pandas as pd
    from app.results import columns, index
    gqa = None
    msg = ""
    rowcount = 0
    ok = False
    if os.access(filename, os.R_OK) is True:
        try:
            gqa = pd.read_json( filename, orient="table", precise_float=10 )
            msg = "import Pandas Datendatei: {}".format(filename)
            ok = True
        except:
            msg = "import fehlgeschlagen: {}".format(filename)
    else:
        msg = "import keine Leserechte: {}".format(filename)
        
    print( msg )
    if ok:
        if not conn:
            _config = ispConfig( )
            
            bind =_config.get("database.main", ["gqa"] )
            if type( bind ) == list:
                bind =bind[0]
            conn = _config.get(["database", bind, "connection"], False)
        try:
            # eindeutige id spalte start bei 1
            gqa = gqa.reset_index()
            gqa.index = gqa.index + 1
            gqa.index.rename('id', inplace=True)
            rowcount = gqa.to_sql('gqadb', conn, 
                index=True, 
                if_exists='replace',
                dtype =columns
            )
        except TypeError as e:
            print( "pandas", e )
        
        print( "{} Datensätze in die Datenbank geschrieben".format(rowcount) ) 
    
def exportPandas( filename, conn:str=None ):
    import pandas as pd
    from app.results import columns, index
    if not conn:
        _config = ispConfig( )
        bind =_config.get("database.main", ["gqa"] )
        if type( bind ) == list:
            bind =bind[0]
        conn = _config.get(["database", bind, "connection"], False)
   
    msg = ""
    # alle columns als string bis auf group das ist integer
    gqa = pd.read_sql_table('gqadb', conn, 
        index_col=index,
    )
    gqa.drop(columns=['id'], inplace=True)
    gqa.reset_index( inplace=True )
    gqa["date"] = gqa["date"].dt.strftime( "%Y%m%d" )
    gqa.set_index(index, inplace=True)
  
    if not os.path.isfile( filename ) or os.access(filename, os.W_OK) is True:
        try:
            gqa.to_json( filename, 
                orient="table", 
                double_precision=10, 
                # default_handler=str,
                indent=2 
            ) 
            msg = "export nach: {}".format(filename)
        except:
            msg = "export fehlgeschlagen: {}".format(filename)
    else:
        msg = "export keine Schreibrechte: {}".format(filename)

    print( msg )


# -----------------------------------------------------------------------------
def run( overlay:dict={}, additionalModels:list=[] ):
    ''' Startet ispBaseWebApp mit zusätzlichen config Angaben

    Parameters
    ----------
    overlay : dict, optional
        Overlay Angaben für config. The default is {}.
    load_tests_db: bool, optional
        load also testdb
        
    Returns
    -------
    webApp : ispBaseWebApp
        Die gestartete WebApplication

    '''

    # Konfiguration öffnen
    
    # _config = ispConfig( mqttlevel=logging.DEBUG, rootlevel=logging.DEBUG)
    _config = ispConfig( )

    _apiConfig = {
        "models": [ gqa, gqadb, system ] + additionalModels,
    }
            
    # Webserver starten
    webApp = ispBaseWebApp( _config, db, apiconfig=_apiConfig, overlay=overlay )

    #  mqtt in config schließen
    _config.mqttCleanup( )
    return webApp


