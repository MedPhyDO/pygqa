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
    { "value": 0, "content": "test" }
        
    config-20180101.json enthält:
    { "value": 1, "info": "info-20180101" }
    
    config-20180501.json enthält:
    { "value": 5, "content": "test-20180501" }
    
    from isp import ispConfig
    
    config = ispConfig()
    print( config.get("value"), config.get("content" ), config.get("info" ) )
    > 5 test test-20180501
    
    config = ispConfig()
    print( config.get("value" ) )
     
## Optionen
- `version:` Version der Configuration
- `server:` Angaben für den Server und dessen Verbindungen
- `database:` Angaben für die verwendete Datenbank
- `pdf:` Angaben für die erstellung von PDF Dateien
- `use_as_variables:` Benannte Liste von Optionen die in `variables` übernommen werden sollen
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
  - `safrs:` Für die Api Schnittstelle. Default `40`
  - `webapp:` Für den Webserver. Default `40`
  - `sqlalchemy:` Für das Datenbankmodul. Default `40`
            
## Optionen `pdf`

- `pdf:`
    - `page-style:` Default: mpdf_page.css
    - `overlay-style:` Default: mpdf_overlay.css

Bei diesen Angaben werden keine `variables` ersetzt.
 
## Optionen `database`

Datenbank Parameter für verschiedene Datenbanken

- `main:` Die als default verwendete Datenbank für safrs (<dbname>). Default None
- `<dbname>:`
    `connection`: Datenbank Connection string

# templates werden zuerst eingefügt und dann alle `variables` ersetzt

Bei Änderungen von *.tmpl Dateien diese als include angeben: `"{% include \"<name>.tmpl\" %}'"`

- `templates:` 
  - `PDF-HEADER:` Default: Inhalt von mpdf_header.tmpl
  - `PDF-FOOTER:` Default: Inhalt von mpdf_footer.jinja
  - `PDF-PAGE_STYLE:` Default: Inhalt von mpdf_page_style.tmpl
  - `PDF-OVERLAY_STYLE:` Default: Inhalt mpdf_overlay_style.tmpl
 
## `use_as_variables` Angaben

Diese Angaben werden aus den angegebenen Pfaden als `variables` für die Nutzung in Templates abgelegt.

Default::
    
    {
        "webserver" : "server.webserver", 
        "resources" : "server.api.resources",
        "globals" : "server.api.globals",
        "api" : "server.api",
        "mqtt" : "server.mqtt",
        "title" : "server.webserver.title"
    }
    
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
