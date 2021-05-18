# -*- coding: utf-8 -*-

'''
Das eigentliche starten der app wird über run erledigt

'''

import logging

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
        import os
        import json
        
        def checkPath( path, info ):
            html = ""
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
        
        # --------------- Aria Datenbank
        from app.aria import ariaClass 
        _database_key = config.get( "server.database.servername", "variansystem" )
        aria = ariaClass( _database_key, config )
        connect = aria.openDatabase( _database_key )
        db_config = config.database[_database_key]
        
        html += '<div class="alert alert-dark" >Prüfe Datenbankzugriff <span class="badge badge-info">database.servername</span>: <b>{}</b> - Konfiguration:'.format( _database_key )
        db_config_copy = db_config.copy()
        db_config_copy.password = "******"
        html += '</br> <pre>{}</pre>'.format( json.dumps( db_config_copy.toDict(), indent=2 ) )
        info_text = "Der Zugriff auf die Datenbank dbname:<b>{dbname}</b>, host:<b>{host}</b>, user:<b>{user}</b>".format( **db_config )
        if not connect:
            info_class = "danger"   
            info_text = "{} ist nicht möglich.".format( info_text )
        else:
            info_class = "success"
            info_text = "{} ist möglich.".format( info_text )
        html += '<div class="alert alert-{} ">{}</div>'.format( info_class, info_text )
        
        
        if connect:
            html += '<div class="alert alert-dark" >Prüfe Patienten für <span class="badge badge-info">units</span> - Konfiguration:'
            html += '</br> <pre>{}</pre>'.format( json.dumps( config.get( "units" ).toDict(), indent=2 ) )
            for name, unit in config.get( "units" ).items():
                
                sql = "SELECT [Patient].[PatientId]FROM [dbo].[Patient] [Patient]"
                sql = sql + " WHERE [Patient].[PatientId] = '{}' ".format( name )
                result = aria.execute( sql ) 
                
                info_text = "PatientId: <b>{}</b>".format( name )
                if len( result ) > 0:
                    info_text = "{} ist vorhanden.".format( info_text )
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
                html += "</div>"
            html += "</div>"
        html += "</div>"
        
        # --------------- DICOM
        from app.ariadicom import ariaDicomClass
        
        _dicom_key = config.get( "dicom.servername", "VMSDBD" )
        adc = ariaDicomClass( _database_key, _dicom_key, config )
        dicom_config = config.get( ["dicom", _dicom_key] )
        
        html += '<div class="alert alert-dark" >Prüfe Dicom <span class="badge badge-info">dicom.servername</span>: <b>{}</b> - Konfiguration:'.format( _dicom_key )
        html += '<pre>{}</pre>'.format( json.dumps( dicom_config.toDict(), indent=2 ) )
        html += '<br>Server Settings - AE Title (aec): <b>{aec}</b> - IP (server_ip): <b>{server_ip}</b> - Port (server_port): <b>{server_port}</b><br>'.format( **dicom_config )
        html += '<br>Application Entity Map Entry - AE Title (aet): <b>{aet}</b> - Port (listen_port): <b>{listen_port}</b>'.format( **dicom_config )
        html += '<div class="alert alert-dark" >Prüfe Verzeichnis: <span class="badge badge-info">dicom.{}.local_dir</span>'.format( _dicom_key ) 
        html += checkPath( dicom_config.get("local_dir", "" ) , '<span class="badge badge-info">dicom.{}.local_dir</span>'.format(_dicom_key))
        html += "</div>"
        
        status = adc.initAE()
        dicom_info = adc.getInfo()
        adc.closeAE()
        if status == 0x0000:
            info_class = "success"   
            info_text = "Dicom Zugriff ist möglich. Associations: "
            for association in dicom_info["associations"]:
                association["ae_title"] = association["ae_title"].decode().strip()
                info_text += '</br> <pre>{}</pre>'.format( json.dumps( association, indent=2 ) )    
        else:
            info_class = "danger"   
            info_text = "Dicom Zugriff ist nicht möglich. ErrorCode: 0x{0:04x}.".format( status )
            
        html += '<div class="alert alert-{} ">{}</div>'.format( info_class, info_text )  
        html += "</div>"
        
        # --------------- resultsPath
        resultsPath = adc.initResultsPath()
        html += '<div class="alert alert-dark" >Prüfe <span class="badge badge-info">resultsPath</span>: <b>{}</b>'.format( resultsPath )
        html += checkPath(resultsPath, '<span class="badge badge-info">resultsPath</span>')
        html += "</div>"

        # --------------- MQTT
        mqtt_config = config.get( "server.mqtt" )
        mqtt_config_copy = mqtt_config.copy()
        mqtt_config_copy.password = "********"
        if mqtt_config_copy.get("host", "") == "":
            html += '<div class="alert alert-info" >MQTT deaktiviert'
        else:
            html += '<div class="alert alert-dark" >Prüfe <span class="badge badge-info">server.mqtt</span> - Konfiguration:'
            html += '<pre>{}</pre>'.format( json.dumps( mqtt_config_copy.toDict(), indent=2 ) )
            
            mqtt = config.mqttGetHandler()
            if not mqtt:
                info_class = "danger"   
                info_text = "MQTT Zugriff ist nicht möglich."
            else:    
                info_class = "info"   
                info_text = 'MQTT Zugriff ist eingerichtet. <button type="button" class="btn btn-primary" onClick="mqttTest( this )">Prüfen</button>'
                 
            html += '<div id="MQTT-checkline" class="alert alert-{} ">{}<div id="MQTT-results" class"alert"></div></div>'.format( info_class, info_text ) 
            
        html += "</div>"
        html += '''
            <script>
            var box = document.querySelector("#MQTT-checkline");
            var result_box = document.querySelector("#MQTT-results");
            if ( typeof app.clientMqtt === "object" ) {
                app.clientMqtt.subscribe( "MQTT/test", function( msg ) {
                    box.className = "alert alert-success";
                    result_box.className = "alert alert-success";
                    result_box.innerHTML = "MQTT Test erfolgreich";
                } );      
            }
            function mqttTest( btn ){
                box.className = "alert alert-info";
                result_box.className = "";
                   
                if ( typeof app.clientMqtt === "object" ) {
                    result_box.className = "alert alert-danger";
                    result_box.innerHTML = "MQTT Test nicht erfolgreich.";
                    app.clientMqtt.publish( "MQTT/test", { "test":"MQTT" } );
                } else {
                    result_box.className = "alert alert-warning";
                    result_box.innerHTML = "kein clientMqtt vorhanden";
                } 
            }
            </script>
        '''
        return {}, html

# -----------------------------------------------------------------------------      
def run( overlay:dict={} ):
    ''' Startet ispBaseWebApp mit zusätzlichen config Angaben
    
    Parameters
    ----------
    overlay : dict, optional
        Overlay Angaben für config. The default is {}.

    Returns
    -------
    webApp : ispBaseWebApp
        Die gestartete WebApplication

    '''
   
    # Konfiguration öffnen
    _config = ispConfig( mqttlevel=logging.WARNING )
    
    _apiConfig = {
        "models": [ gqa, gqadb, system ],
    }
    
    # Webserver starten
    webApp = ispBaseWebApp( _config, db, apiconfig=_apiConfig, overlay=overlay )
    
    #  mqtt in config schließen
    _config.mqttCleanup( )
    return webApp


    