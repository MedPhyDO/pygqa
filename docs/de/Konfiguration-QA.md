# Konfiguration Geräte QA

Beschreibung der zusätzliche Konfigurationsmöglichkeiten für die Geräte-QA.

## Optionen `database`

- `servername:`Zu verwendender Datenbankeintrag. Default "variansystem",
- `variansystem:` Name des Datenbankeintrags
  - `engine:` Databaseengine `pytds` or `pyodbc`. Default `pytds`
  - `dsn:` für `pyodbc` verwendeter DSN name aus `/etc/odbc.ini`
  - `host:` IP des Varian Datenbank Servers. Default ""
  - `dbname:` Name der Datenbank. Normalerweise `variansystem` oder `VARIAN`. Default Name des Datenbankeintrags
  - `user:` Username für die Autentifizierung. Ausreichend ist ein `nur lese` Zugriff. Default ""
  - `password:` Passwort für die Autentifizierung. Default ""
  - `login_timeout:` Timeout für das login.  Default 3

Im `SQL Server Management Studio` auf dem Varian Server muss ein User mit nur lese Rechten `db_datareader, public` für die Database `VARIAN` Default Schema `dbo` angelegt werden.

### Aria 13.x

Für die Verbindung zur Datenbank wird `pytds` verwendet.

### Aria 16.x

Für die Verbindung zur Datenbank wird `pyodbc` verwendet.
Eine zusätzliche notwendige Installation für ODBC ist unter [Installation (en) database connection with odbc](../en/installation.md) beschrieben.


## Optionen `dicom`

- `servername:` : Zu verwendender DICOM Server Eintrag. Default "VMSDBD"
- `VMSDBD:` Name des DICOM Servereintrags
  - `aec:` Aufzurufender AE Title. Default "VMSDBD"
  - `server_ip:` IP des Varian DICOM Servers. Default ""
  - `server_port:` Listen Port des Varian DICOM Servers. Default 105
  - `aet:` Aufrufender AE title unter . Default "GQA"
  - `listen_port:` Der verwendete lokale DICOM Port. Default 50300
  - `local_dir:` Das Lokale Verzeichnis für die geladenen DICOM Daten.

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

Beispiel::

    "units": {
        "_QA Linac1" : "Linac-1",
        "_QA Linac2" : "Linac-2"
    }

Für einen Aufruf von tests/test_app.py werden zusätzich die zu Testenden unit keys in `units_TestsApp:` angegeben.

Beispiel::

    "units_TestsApp": ["_QA Linac1","_QA Linac2"]


## Optionen `templates`

Zusätzliche Templates für die PDF Erstellung. Default::

    "templates": {
        "PDF-JT-filename": "{{'%04d' % AcquisitionYear}} - {{unit}} - {{energy}} - {{testId}}.pdf",
        "PDF-JT-Titel": "GQA Jahrestest - {{testTag}} - {{unit}} - {{energy}}",
        "PDF-JT-Betreff": "für: {{'%04d' % AcquisitionYear}}",
        "PDF-MT-filename": "{{'%04d' % AcquisitionYear}}{{ '%02d' % AcquisitionMonth}} - {{unit}} - {{energy}} - {{testId}}.pdf",
        "PDF-MT-Titel": "GQA Monatstest - {{testTag}} - {{unit}} - {{energy}}",
        "PDF-MT-Betreff": "für: {{'%04d' % AcquisitionYear}}/{{ '%02d' % AcquisitionMonth}}"
    }

## Optionen `GQA`

Eine Benannte Liste mit Tests und deren Parametern. [Hier](/docs/de/GQA-Tests.md) ist eine Beschreibung der einzelnen Tests zu finden.

- `testId:`
  - `tag:` Der in Aria Bestrahlungsfeld unter `Feldeigenschaften Kommentar` einzugebende Tag für diesen Test.
  - `info:`
    - `tip:` Eine Kurze Beschreibung die in der Testliste angezeigt wird.
    - `anleitung:` Pfad zu einer Anleitung für den Test in `resources`. Default ""
    - `need:` Hier kann angegeben werden, welcher andere Test als Grundlage für diesen verwendet wird.
    - `TODO:` Hier kann in einer Liste angegeben werden was noch vor der allgemeinen Verwendung des Tests gemacht werden muss. Diese Angaben werden im Menü **Testmatrix** angezeigt.
    - `tolerance:` Benannte Liste mit Energien und deren Test Toleranzen für die Auswertung.
      - `<energy>:` Die Energie für die folgenden Parameter gelten. z.B. "6x".
        - `<id>:` Diese Parameter werden für die Auswertung verwendet. Default "default"
          - `soll:` Benannte Liste für den Sollwert.
            - `value:` Der zu verwendene Sollwert.
            - `unit:` Angabe einer Einheit für den Sollwert.
          - `warning:` Benannte Liste für die Warnschwelle.
            - `value:` Der zu verwendene Warnwert, wenn keine Formel verwendet wird.
            - `f:` Die Formel für die Berechnung. An der Position `{value}` wird der aktuelle Wert verwendet.
            - `unit:` Angabe einer Einheit für den Warnwert.
          - `error:` Benannte Liste für die Fehlerschwelle
            - `value:` Der zu verwendene Fehlerwert, wenn keine Formel verwendet wird.
            - `f:` Die Formel für die Berechnung. An der Position `{value}` wird der aktuelle Wert verwendet.
            - `unit:` Angabe einer Einheit für den Fehlerwert.
          - `check:` Angaben für die Toleranzprüfung in Pandas Feldern
            - `field:` Das für die Toleranzprüfung verwendete Tabellen Feld.
            - `query:` Die für Pandas verwendete Query um die von Pandas für die Toleranzprüfung verwendeten Datensätze einzuschränken
    - `inaktiv:` Mit diesem boolean Parameter kann ein Test ab einem zeitpunkt von der weiteren Auswertung ausgeschlossen werden.
  - `<unit>:` Name des Geräts für die Konfiguration z.B. `Linac-1`
    - `energyFields:` Benannte Liste mit Energien und der mind. Anzahl von Feldern z.B. `{ "6x":18, "15x":18 }`
  - `series_groupby:` Kann intern bei der Testauswertung verwendet werden und ist für den jeweiligen Test vorgegeben.

Beispiel für die LeafSpeed Konfiguration::

    "MT-LeafSpeed":{
        "tag": "MT_LeafSpeed",
        "info": {
            "tip": "Geschwindigkeit der Lamellen DIN 6875-3, Teil 4.2.6 (mit Gating)",
            "anleitung" : "qa/MLC-MT-LeafSpeed.md",
            "TODO": [ ],
            "tolerance": {
                "6x" : {
                    "default": {
                        "soll" : { "value": 0, "unit": "%" },
                        "warning" : { "f":"abs({value}) > 1.75", "unit": "%" },
                        "error" : { "f":"abs({value}) > 2", "unit": "%" }
                    }
                }
            }
        },
        "Linac-1": {
            "energyFields" : { "6x":18 }
        },
        "Linac-2": {
            "energyFields" : { "6x":18 }
        }
    }


