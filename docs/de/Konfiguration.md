# Konfiguration

Die Konfigurations Dateien liegen im Ordner `config` 
und werden im [Json Format](https://de.wikipedia.org/wiki/JavaScript_Object_Notation) erstellt.

Der Name der Grundkonfiguration lautet `config.json`.

Es ist möglich die Grundkonfiguration durch das Anhängen von Zahlen zu überlagern z.B. `config-03.json`, `config-15.json`.   
Dabei wird jeder Inhalt mit dem nachfolgenden von klein nach groß beginnend mit `config.json` überlagert.

Wird bei der Initialisierung des ispConfig Moduls `overlayLast` angegeben stoppt das einlesen bei dieser Nummer.

Mit einer Datumsangabe im Format `%Y%m%d` z.B. config-20181205.json ist es möglich nur bis zu einem angegebenen Datum zu überlagern.  
Dabei wird maximal bis zum aktuellem Tag eingelesen. Dies ermöglicht das Erstellen einer Konfiguration die erst ab einem bestimmten Datum verwendet wird.

Beispiel::

config.json enthält: 
`{ "value": 0, "content": "test" }`
        
config-20180101.json enthält:
`{ "value": 1, "info": "info-20180101" }`
    
config-20180501.json enthält:
`{ "value": 5, "info": "test-20180501" }`
    
```python
from isp import ispConfig

config = ispConfig()
print( config.get("value"), config.get("content" ), config.get("info" ) )
> 5 test test-20180501
```    
     
## Optionen
- `version`: Version der Configuration
- `server`: Angaben für den Server und dessen Verbindungen
- `database`: Angaben für die verwendete Datenbank
- `dicom`: Angaben für den verwendeten Dicomserver
- `pdf`: Angaben für die Erstellung von PDF Dateien
- `resultsPath`: Der Basispfad für alle Auswertungen
- `units`: 
- `use_as_variables`: Benannte Liste von Optionen die in `variables` übernommen werden sollen
- `variables:` Angaben für die Verwendung in Templates

## Optionen `server`

Webserver und Api Parameter

- `webserver:`
  - `host:` IP des Webservers. Default `127.0.0.1` (localhost)
  - `port:` Webserverport. Default `8085`
  - `name:` Webserver Name für Templates. Default `webapp`
  - `title:` Applikations Name für Templates. Default `webapp`
  - `resources:` Pfad zu den Resourcen (Texten, Javascript Bibliotheken, Stylesheets, Fonts).  Default `{BASE_DIR}/resources/`
  - `globals:` Pfad für zusätzliche globalen Resourcen. Default `{BASE_DIR}/resources/`
  - `ui:` Pfad zu Website Templates. Default `{{BASE_DIR}}/ui/`
  - `debug:` Aktiviert den Flask debug Modus. Default `true`
  - `reloader:` Flask Angabe use_reloader Prüft während der Laufzeit auf Änderungen im Program. Default `true`
  - `checkNetarea:` Einfacher Check ob der Zugriff aus dem gleichen Subnetz erfolgt. Default `true`
  - `TESTING:` Wird nur für unittest in `/tests` verwendet. Default `false`
  - `SECRET_KEY:` Flask config SECRET_KEY. Default: `os.urandom(16)`
  
- `api:`
  - `prefix:` Zugriff auf die Swagger Api Schnittstelle. Default `/api`
  - `DBADMIN:` DB-Admin Zugriff bereitstellen. Default `false`
  - `COVERAGE:` Coverage (Bericht über die Modulnutzung) bereitstellen. (Nur nach einer fehlerfreien Durchführung von `tests/all_unittests.py`). Default `false`
  - `custom_swagger_config:` Ergänzende Sawgger Api Konfiguration für Klassen und Funktionen ohne autom. Anbindung. Nur wenn angegeben.
  
- `mqtt:`
  - `host:` IP des MQTT Server. Default `127.0.0.1` (localhost)
  - `port:` Port des MQTT Server. Default `1883`
  - `webclient_port:` Default `9001`
  - `username:` Username für die Autentifizierung. Default ""
  - `password:` Passwort für die Autentifizierung. Default ""
  - `basetopic:` topic der vor alle topics gesetzt wird. Default ""
  - `logging:` Aktiviert das logging über MQTT. Der Topic beginnt dabei immer mit `logging/`. Default: `false`
            
- `logging:` logging level für die Module. 0 - NOTSET, 10 - DEBUG, 20 - INFO, 30 - WARNING, 40 - ERROR, 50 - CRITICAL
  - `root:` Für den root logger. Default `40`
  - `mqtt:` Für den MQTT logger. Default `40`
  - `safrs:` Für die Api Schnittstelle. Default `40`
  - `webapp:` Für den Webserver. Default `40`
  - `sqlalchemy:` Für das Datenbankmodul. Default `40`
             
## Optionen `database`

Datenbank Parameter für verschiedene Datenbanken

- `main`: Die als default verwendete Datenbank für safrs (<dbname>). Default None
- `<dbname>`:
  - `connection`: Datenbank Connection string
  - `dbname`: Datenbankname
  - `engine`: Die verwendete Datenbank engine `pytds` oder `pyodbc`
  - `user:` Username für die Autentifizierung. Ausreichend ist ein `nur lese` Zugriff. 
  - `password:` Passwort für die Autentifizierung. 

Zusätzliche Parameter bei der Verwendung von `pytds`
  - `host`:  dsn Angabe für `pytds.connect()` aus `/etc/odbc.ini`
  - `login_timeout`: login_timeout Angabe für `pytds.connect()`

Zusätzliche Parameter bei der Verwendung von `pyodbc`
  - `driver`: z.B. `{ODBC Driver 17 for SQL Server}`
  - `server_ip`: Datenbank Server IP

Im `SQL Server Management Studio` auf dem Varian Server muss ein User mit nur lese Rechten `db_datareader, public` für die Database `VARIAN` Default Schema `dbo` angelegt werden.

### Aria 13.x

Für die Verbindung zur Datenbank wird `pytds` verwendet.

### Aria 16.x

Für die Verbindung zur Datenbank wird `pyodbc` verwendet.
Eine zusätzliche notwendige Installation für ODBC ist unter [Datenbankverbindung mit ODBC](/docs/de/Installation.md) beschrieben.

## Optionen `dicom`

- `servername` : Der als default verwendete DICOM Server Eintrag (<dicomname>)
- `<dicomserver>`: Name des DICOM Servereintrags
  - `aec`: Aufzurufender AE Title. Default "VMSDBD"
  - `server_ip`: IP des Varian DICOM Servers. Default ""
  - `server_port`: Listen Port des Varian DICOM Servers. Default 105
  - `aet`: Aufrufender AE title unter . Default "GQA"
  - `listen_port`: Der verwendete lokale DICOM Port. Default 50300
  - `local_dir`:er lokale Speicherort für die geladenen DICOM Dateien Default: **data/DICOM**

### Aria 13.x
Die DICOM Optionen müssen denen des `DB Daemon Configuration [DICOM Service Daemon Configuration Wizard]` (DicomController.exe) auf dem Varian Server entsprechen.

* Im Bereich **General** befinden sich die Settings für `aec` - **AE Title** und `server_port` - **Listen Port**
* Im Bereich **Security** muss eine neue **Trusted Application** mit `aet` - **AE Title** der eigenen **IP-Address** und `listen_port` - **Port** angelegt werden.

### Aria 16.x
Die DICOM Optionen müssen denen der `DICOM Services` (VMS.DICOMServices.Configuration.exe) auf dem Varian Server entsprechen.

* Varian DB Service starten und die `Service Settings` mit dem `Werkzeug Symbol` öffnen.
* Mit `Add New `eine neue **Trusted Application** mit `aet` - **AE Title** der eigenen **IP-Address** und `listen_port` - **Port** anlegen.
* Für beide `Character Set` Angaben **Unicode (ISO_IR 192)** auswählen.

## Optionen `resultsPath`

Der Pfad in dem die erstellten Testauswertungen abgelegt werden.

## Optionen `units`

Eine Benannte Liste (PatientenID:Gerät) um eine Aria Patienten ID einem Gerät zuzuordnen.
Wir Empfehlen pro Gerät einen Patienten im Aria anzulegen.

```json
"units": {
  "_QA Linac1" : "Linac-1",
  "_QA Linac2" : "Linac-2"
}
```

Für einen Aufruf von tests/test_app.py werden zusätzich die zu Testenden unit keys in `units_TestsApp:` angegeben.

```json
"units_TestsApp": ["_QA Linac1","_QA Linac2"]
```

## Optionen `pdf`

- `pdf:`
  - `page-style:` Default: mpdf_page.css
  - `overlay-style:` Default: mpdf_overlay.css

## Optionen `templates`

Zusätzliche Templates für die PDF Erstellung. Default:
```json
"templates": {
    "PDF-JT-filename": "{{'%04d' % AcquisitionYear}} - {{unit}} - {{energy}} - {{testId}}.pdf",
    "PDF-JT-Titel": "GQA Jahrestest - {{testTag}} - {{unit}} - {{energy}}",
    "PDF-JT-Betreff": "für: {{'%04d' % AcquisitionYear}}",
    "PDF-MT-filename": "{{'%04d' % AcquisitionYear}}{{ '%02d' % AcquisitionMonth}} - {{unit}} - {{energy}} - {{testId}}.pdf",
    "PDF-MT-Titel": "GQA Monatstest - {{testTag}} - {{unit}} - {{energy}}",
    "PDF-MT-Betreff": "für: {{'%04d' % AcquisitionYear}}/{{ '%02d' % AcquisitionMonth}}"
}
```

Bei diesen Angaben werden keine `variables` ersetzt.

# templates werden zuerst eingefügt und dann alle `variables` ersetzt

Bei Änderungen von *.tmpl Dateien diese als include angeben: `{% include \"<name>.tmpl\" %}'`

- `templates:` 
  - `PDF-HEADER:` Default: Inhalt von mpdf_header.tmpl
  - `PDF-FOOTER:` Default: Inhalt von mpdf_footer.jinja
  - `PDF-PAGE_STYLE:` Default: Inhalt von mpdf_page_style.tmpl
  - `PDF-OVERLAY_STYLE:` Default: Inhalt mpdf_overlay_style.tmpl
 
## `use_as_variables` Angaben

Diese Angaben werden aus den angegebenen Pfaden als `variables` für die Nutzung in Templates abgelegt.

Default:

```json
{
    "webserver" : "server.webserver", 
    "resources" : "server.api.resources",
    "globals" : "server.api.globals",
    "api" : "server.api",
    "mqtt" : "server.mqtt",
    "title" : "server.webserver.title"
}
```

Beispiel: `server.webserver.name` steht über `{{webserver.name}}` in Templates zur Verfügung.

## `variables` Variablen für templates

Diese Angaben stehen in allen jinja Templates zur Verfügung.
 
Autom. erzeugte **Statische** Angaben:
 
- `BASE_DIR:` Der Dateisystem Basis Pfad der Applikation mit dem gestarteten Python Script
- `version:` Die `version` aus der Configuration sonst `__version__` des Python Script
- `serverHost` Host und Port des Webservers. Default  `webserver.host`:`webserver.port`
- `resources:` Der Dateisystem Pfad aus `webserver.resources`
- `globals:` Der Dateisystem Pfad aus `webserver.globals`
- `logopath:` Der Dateisystem Pfad aus `webserver.resources`/`meta.logo`
- `development:` Liegt disese APP in einem Unterverzeichniss `production` dann False sonst True. .. TODO:: kann auch beim start angegeben werden 

Spezielle Angaben für PDF Dokumente und defaults, die überschrieben werden können.

- `logo:` Der Dateiname des Logos aus `resources`. Default: `logo.png`
- `path:` Pfad in dem PDF Dokumente erzeugt werden. Default: `{{BASE_DIR}}}/files`
- `filename:` Name des erzeugten PDF Dokument in path. Default: `noname.pdf`
- `Klinik:` Wird im Seitenkopf verwendet
- `Abteilung:` Wird im Seitenkopf verwendet
- `Titel:` Wird im Seitenkopf verwendet. 
- `Betreff:` Wird im Seitenkopf verwendet  
- `Schlüsselwörter:` Wird in den Metadaten des PDF verwendet
- `Datenausgabe:` Default: `{{ now.strftime('%d.%m.%Y') }}`
- `Erstelldatum:` Wird in der Fußzeile verwendet
- `Erstellt_von:` Wird in der Fußzeile verwendet
- `Gültig_ab:` Wird in der Fußzeile verwendet
- `Version:` Wird in der Fußzeile verwendet
- `Freigegeben_von:` Wird in der Fußzeile verwendet
- `page:`
  - `size:`  Default: `A4 portrait`
  - `left:` Default: `20`
  - `right:` Default: `9`
  - `top:` Default: `7.5`
  - `bottom:` Default: `6.0`
  - `header:` Default: `12`
  - `footer:` Default: `5`
  - `header-margin:` Default: `4`
  - `footer-margin:` Default: `2`
