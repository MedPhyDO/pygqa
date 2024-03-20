In der Strahlentherapie müssen die Bestrahlungsgeräte regelmäßig geprüft werden, um eine korrekte und präzise Bestrahlung der Patienten zu gewährleisten. Dafür gibt es verschiedene Tests, bei welchen in regelmäßigen Abständen die verschiedenen Parameter der Geräte gemessen werden. Welche Tests wie häufig durchgeführt werden müssen, ist durch DIN-Normen vorgegeben. Es wird geprüft, dass die entsprechenden Parameter bei verschiedenen Messungen bestimmte Abweichungen nicht überschreiten. Um die Auswertung der Messergebnisse zu vereinfachen, wird daran gearbeitet, diese zu automatisieren. Dafür wird am Klinikum Dortmund das Projekt pygqa basierend auf dem Pylinac-Projekt entwickelt. Hierbei wird Python genutzt um die Testergebnisse auszuwerten.

Für die Nutzung und Weiterentwicklung von pygqa müssen zunächst einige Installationen vorgenommen werden. Eine Installationsanleitung befindet sich auf der GitHub Seite MedPhyDO. Im ersten Schritt wird Miniconda installiert. Danach wird das repository, welches auf GitHub verfügbar ist, geklonet. Im nächsten Schritt werden Module und Resourcen installiert. Dabei ist zu beachten, dass für die Installation vorausgesetzt ist, dass die Module pillow, pyodbc und cargo bereits vorinstalliert sind.  

Bei der Nutzung einer Aria-Version von 13.x oder größer muss Microsoft ODBC installiert werden. Hierbei ist bislang nur die Funktionalität mit der Version ODBC 17 getestet, weshalb es empfehlenswert ist, diese Version zu installieren. Nun kann pygqa per mitgeliefertem Python-Skript gestartet werden. Mit einigen lokalen Konfigurationen kann auf entsprechende Datenbanken zugegriffen werden. In der GQA werden die eingefügten Jahres- und Monatstests aufgeführt, wobei noch ausstehende Tests grau, durchgeführte Tests, welche noch nicht ausgewertet wurden gelb und fertig ausgewertete Tests grün hinterlegt sind. Durchgeführte Tests können mit einem Mausklick auf den entsprechenden Test ausgewertet werden. In den Konfigurationen werden je nach Test verschiedene Schwellwerte angegeben, ab welchen eine Warnung oder ein Fehler auf der ausgewerteten pdf-Datei angegeben werden. So ist direkt ersichtlich, ob die Testergebnisse den Vorgaben entsprechen.

# Installation

Mit folgender Anleitung kann pygqa für Ubuntu-Linux installiert werden.
Wir empfehlen **Visual Studio Code** oder **spyder** für die Bearbeitung der Dateien.

> **⚠ NOTE**  
> In der Anleitung wird an einigen Stellen in den Befehlen etwas in spitzen Klammern angegeben, zum Beispiel **< Passwort >**. Dieser Teil muss dann individuell ersetzt werden durch das, was in den Klammern beschrieben ist.

## Repository klonen

Im ersten Schritt wird das repository von GitHub geklont. Dazu wird auf der Konsole ein Arbeitsverzeichnis für das geklonte Verzeichnis angelgt und dorthin gewechselt.

```bash
mkdir <Name_des_Arbeitsverzeichnis>
cd <Name_des_Arbeitsverzeichnis>
```

Nun wird auf der GitHub Seite [MedPhyDO/pygqa](https://github.com/MedPhyDO/pygqa/tree/pylinac-ge-3.11) der grüne Button "Code" rechts über den Ordnern und Datein angeklickt und dort die url zum klonen des repositorys kopiert.
Dann kann das repository geklont werden, indem in der Konsole `git clone` verwendet wird. Das Klonen erstellt einen Ordner, in welchem sich die geklonten Ordner und Dateien befinden. Dieser Ordner ist genauso benannt, wie das Repository.

```bash
git clone <kopierte url>
cd <Name_des_repository>
```

### Alternativ download / unpack repository

Alternativ zum Klonen kann das repository auch unter dem Button "Code" als zip-Ordner gedownloadet werden. Dieser zip-Ordner muss dann noch im neu erstellten Ordner entpackt werden.

## Variante A - lokale Python-Installation

Hierzu wird Miniconda installiert. Dafür wird folgender Befehl in die Konsole eingegeben.

```bash
wget https://repo.anaconda.com/miniconda/Miniconda3-py311_23.5.0-3-Linux-x86_64.sh -O ./Miniconda3-py311_23.5.0-3-Linux-x86_64.sh
```

[Miniconda311-23.5.0](https://repo.anaconda.com/miniconda/) beinhaltet Python **version 3.11.4** 

Anschließend überprüfen der Checksumme:   
```bash
sha256sum ./Miniconda3-py311_23.5.0-3-Linux-x86_64.sh
```

Diese sollte wie folgt lauten.  
```
61a5c087893f6210176045931b89ee6e8760c17abd9c862b2cab4c1b7d00f7c8
```

Um die Installationsdatei ausführen zu können wird das entspechende Flag gesetzt.
```bash  
chmod +x ./Miniconda3-py311_23.5.0-3-Linux-x86_64.sh 
```

Mit der Eingabe von  
```bash  
./Miniconda3-py311_23.5.0-3-Linux-x86_64.sh
``` 
wird die Installation von Miniconda gestartet.   
Bei der Installation müssen die Lizenzen akzeptiert werden. Als Installationsort kann der default `~/miniconda3` beibehalten werden.  
Die Frage **Do you wish the installer to initialize Miniconda3 by running conda init?**
wird mit **no** beantwortet, damit der Bin-Pfad nicht im System-Such-Pfad integriert wird.

Ob die Installation erfolgreich war, kann mit den folgenden beiden Befehlen überprüft werden.

```bash 
~/miniconda3/bin/python --version
``` 
In der Konsole sollte **Python 3.11.4** ausgegeben werden.

```bash
~/miniconda3/bin/pip  --version
```

Hier sollte in der Konsole **pip 23.1.2** oder eine neuere Version angezeigt werden.

> **⚠ NOTE**  
> Im Folgenden werden Befehle mit **< your miniconda binpath >** verwendet. Dieser Teil ist durch **~/miniconda3/bin** oder den Pfad zum neu gewählten Speicherort zu ersetzen.


### Installation der Module und Resourcen

Bevor im nächsten Schritt die Module und Resourcen installiert werden, müssen die Module pillow, pyodbc und cargo installiert werden, falls diese noch nicht vorinstalliert sind.  
- Pillow ist eine Python-Bibliothek, welche Bildverarbeitungsfunktionen bereitstellt.  
- Die Module für pyodbc (unixodbc-dev) werden für die Verbindung zur Datenbank benötigt.  
- Cargo wird für Abhängigkeitsprozesse in Python verwendet.  

```bash
sudo apt-get install libtiff5-dev libjpeg8-dev libopenjp2-7-dev zlib1g-dev libfreetype6-dev liblcms2-dev libwebp-dev tcl8.6-dev tk8.6-dev python3-tk libharfbuzz-dev libfribidi-dev libxcb1-dev g++ unixodbc-dev cargo
```

Nun kann mit der Installation der weiteren Module gestartet werden. Dazu muss zunächst in den Unterordner gewechselt werden, welcher beim klonen erstellt wurde.  
```bash
cd <Name_des_repository>`
```
Dort alle Abhängigen Module installieren.  
```bash
<your miniconda binpath>/pip install -r requirements.txt
```

Bei der Verwendung von spyder als Editor zusätzlich.  
```bash
<your miniconda binpath>/pip install -r requirements_spyder.txt
```

Um die notwendigen Resourcen zu installieren die folgenden Befehle ausführen.  
```bash
<your miniconda binpath>/python install-resources.py
sudo cp ./resources/vendor/fonts/materialdesignicons-webfont.ttf /usr/share/fonts/truetype/materialdesignicons_webfont.ttf
sudo chmod 644 /usr/share/fonts/truetype/materialdesignicons_webfont.ttf
```

## Datenbankverbindung mit ODBC

Wenn die genutzte Aria-Version höher als 13.x ist, muss nun noch Microsoft-ODBC installiert werden, um eine Verbindung zur Datenbank herstellen zu können. Die Installation erfolgt über die Seite [Install the Microsoft ODBC driver for SQL Server (Linux)](https://docs.microsoft.com/en-us/sql/connect/odbc/linux-mac/installing-the-microsoft-odbc-driver-for-sql-server?view=sql-server-ver15#ubuntu17). Es sollte darauf geachtet werden, dass die Version ODBC Driver 17 installiert wird.

### Config-Datei

In dem Ordner, der beim Klonen des repositorys erstellt wird, befindet sich ein Ordner "config". Hier befindet sich die Datei **config.json**. In dieser Datei muss folgendes editiert werden.

```json
  "database": {
      "servername" : "<DSN-Name>",
      ....
      "<DSN-Name>": {
          "engine": "pyodbc",
          "dsn": "<DSN-Name>",
          "dbname": "VARIAN",
          "host": "<IP-Adresse des Servers>",
          "user": "<User>",
          "password": "<Passwort>"

      },
      .....
  },
```

### Datenbankverbindung vom Rechner

Es wird eine temporäre Text-Datei erstellt, um den ODBC DSN (Data Source Name) zu definieren. In der Text-Datei sollte folgendes stehen.

```ini
[MSSQLServerDatabase]
Driver      = ODBC Driver 17 for SQL Server
Description = Connect to my SQL Server instance
Trace       = No
Server      = <IP-Adresse des Servers>
```

Wenn keine andere Driver-Version verwendet wird, muss der Driver-Name genau wie oben geschrieben lauten. Falls eine andere Version verwendet wird, kann diese mit dem Befehl

`cat /etc/odbcinst.ini`

```ini
[ODBC Driver 17 for SQL Server]
Description=Microsoft ODBC Driver 17 for SQL Server
Driver=/opt/microsoft/msodbcsql17/lib64/libmsodbcsql-17.4.so.1.1
UsageCount=1
```

ermittelt werden. In diesem Fall wird der Driver-Name verwendet, der in den eckigen Klammern steht. Wenn auf den Server nicht per IP-Adresse zugegriffen werden kann, muss für `Server =` der DSN-Name des Servers angegeben werden.
    
Nachdem die temporäre config-Datei gespeichert wurde, wird mit dem folgenden Befehl ein "System DSN" erstellt. Dabei wird die Datenbank DSN-Information des SQL Servers in `/etc/odbc.ini` registriert.

```bash
sudo odbcinst -i -s -f <Pfad zur temporären Text-Datei> -l
```

Die DSN-Installation kann mit dem Befehl
```bash
cat /etc/odbc.ini  
```
getestet werden. Die Ausgabe in der Konsole sollte `[MSSQLServerDatabase]` beinhalten.

Die Verbindung zur Datenbank erfolgt nun mit dem Befehl
```bash
sqlcmd -SMSSQLServerDatabase -D -U<User> -P<Passwort>
```

Wenn die Anbindung an die Datenbank erfolgreich war, wird in der Konsole `>1` ausgegeben.

### Datenbankverbindung von pygqa

Ob die Verbindung zur Datenbank über pygqa funktioniert kann getestet werden, indem in die Konsole folgendes eingegeben wird.

```python
<your miniconda binpath>/python
import pyodbc
pyodbc.connect('DSN=MSSQLServerDatabase;UID=<User>;PWD=<Passwort>')
```

Die Verbindung ist erfolgreich, wenn in der Konsole `1>` ausgegeben wird.

## Erster Testlauf

Nun kann der erste Testlauf gestartet werden. Dafür wird

```bash
<your miniconda binpath>/python pygqa.py
```
in die Konsole eingegeben und [GQA - Geräte-QA](http://127.0.0.1:5000/) im Web-Browser geöffnet. 

Alternativ kann Spyder geöffnet und darüber `pygqa.py` gestartet werden.
```bash
<your miniconda binpath>/spyder
```

Auf der pyGQA-Seite können unter dem Reiter **Systeminfo** einige Teile der erfolgreichen Installation kontrolliert werden.  

Zuerst kann der Zugriff auf die Datenbank geprüft werden.  
Danach sind alle Testpatienten aufgeführt und es kann überprüft werden, ob diese vorhanden sind. Darunter kann Dicom kontrolliert werden. Dabei wird geprüft, ob dicom.VMSCOM.local_dir vorhanden, ein Verzeichnis und beschreibbar ist. Auch der Dicom-Zugriff wird überprüft.  
Als nächstes kann der Ordner result überprüft werden. Hierbei wird erneut geprüft, ob resultPath vorhanden, ein Verzeichnis und beshreibbbar ist.  
Die letzte in "Systeminfo" vorhandene Kontrolle ist der MQTT Zugriff, welcher ebenfalls getestet werden kann.  
Zum Schluss ist noch eine Liste der installierten Module mit der jeweiligen Version und Lizenz aufgeführt.


## Zusätzliche Informationen

### Als service unter linux ubuntu ausführen

Ein neuer service für pyGQA kann mit

```bash
sudo nano /lib/systemd/system/pygqa.service
```

erstellt werden.
Der Inhalt von pygqa.service sieht wiefolgt aus. Dieser enthält den Start nachdem das Netzwerk bereit ist und die Gruppe www-data.

```ini
[Unit]
Description=Python GQA Service
After=network.target

[Service]
Type=simple
ExecStart=<your miniconda binpath>/python <your gqa location>/pygqa.py --webserver
WorkingDirectory=<your gqa location>/
Group=www-data
StandardInput=tty-force

[Install]
WantedBy=multi-user.target
```

Der service kann mit

```bash
sudo systemctl start pygqa.service 
sudo systemctl restart pygqa.service 
sudo systemctl stop pygqa.service
```

gestartet, neugestartet oder beendet werden. Um den service beim Systemstart zu aktivieren, den folgenden  Befehl verwenden.

```bash
sudo systemctl enable pygqa.service
```

### Installation zusätzlicher Pakete

Vor der Installation neuer Pakete sollte sichergestellt werden, dass die neuen Pakete mit dem Programm kompatibel sind.

Um die neuste Version eines Paketes zu installieren wird `pip install` verwendet.

```bash
<your miniconda binpath>/pip install <packagename>`
```

Wenn eine bestimmte Version installiert werden soll, muss diese wiefolgt mit angegeben werden.

```bash
<your miniconda binpath>/pip install <packagename>==<version>
```

`pigar` kann verwendet werden um die Datei **requirements.txt** zu aktualisieren.

```bash
<your miniconda binpath>/pigar --without-referenced-comments
```

Um **requirements_upgrade.txt** zu aktualisieren wird diese beim `pigar` Aufruf mit angegeben.

```bash
<your miniconda binpath>/pigar --without-referenced-comments -o '>=' -p ./requirements_upgrade.txt
```


### Update

Vor dem Update sollte sichergestellt werden, dass die neuste Version mit dem Programm kompatibel ist.

Wenn nötig wird zuerst pip auf den neusten Stand gebracht.

```bash
<your miniconda binpath>/pip install --upgrade pip
```

Veralteten Pakete auflisten:
```bash
<your miniconda binpath>/pip list --outdated --format columns
```

Bereits installierten Pakete auf die neuste Version zu bringen:

```bash
<your miniconda binpath>/pip install --upgrade sphinx
```

Alles aus **requirements_upgrade.txt** auf die neuste Version bringen:
```bash
<your miniconda binpath>/pip install -r requirements_upgrade.txt --upgrade
```

Sollte ein Problem mit einem bestimmten Paket auftreten, wodurch das Upgrade verzögert wird, kann im entsprechenden Ordner der Name auskommentiert werden, indem ein # vor den Namen geschrieben wird. Dann kann das Upgrade erneut durchgeführt und die Auskommentierung später rückgängig gemacht werden. Das kann auch bei dem Kopieren von globalen Python-Umgebungen hilfreich sein.

## Variante B - Installation im Dockercontainer

### Docker über snap installieren (Ubuntu)

```bash
sudo snap install docker 
```

Wird docker hinter einem Proxy verwendet, muss ein entsprechender Eintrag in der Docker Datei `~/snap/docker/current/.docker/config.json` gemacht werden.

```json
{ 
  "proxies":
  {
   "default":
   {
    "httpProxy": "http://<ip>:<port>",
    "httpsProxy": "https://<ip>:<port>"
   }
  }
}
```

### Docker verwenden

Die Datei `Dockerfile` enthält alle notwendigen Befehle und Konfigurationen, um einen Container zu erstellen.

In der Datei `docker-compose.yml` stehen alle Befehle und Konfigurationen um einen Container mit `docker compose up` zu erstellen und zu starten.

Zu ändernde Parameter stehen in der Datei `.env`.  Hier werden einfache Schlüssel-Wert-Paare definiert, die dann in `docker-compose.yml` verwendet werden.

Einige Nützliche docker compose Befehle

| Befehl                                                   | Beschreibung                                                                                                 | 
| -------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ | 
| `docker compose build`                                   | Container erstellen, ein build oder rebuild durchführen (bei Änderungen in Dockerfile)                       |
| `docker compose up`                                      | Container starten                                                                                            |
| `docker compose up -d`                                   | Container im Hintergrund starten                                                                             |
| `docker compose --file ./docker-compose.unittest.yml up` | ein anderes composefile ausführen                                                                            |
| `docker compose ps -a`                                   | Container auflisten                                                                                          |
| `docker inspect <container-name>`                        | Container überprüfen                                                                                         |
| `docker rm <container_name>`                             | Container löschen                                                                                            |
| `docker stop <container_name>`                           | Container stoppen                                                                                            |
| `docker restart <container_name>`                        | laufenden Container erneut starten                                                                           |
| `docker start <container_name>`                          | einen gestoppten Container starten                                                                           |
| `docker system df`                                       | verwendeten Speicherplatz anzeigen (Images, Containern, lokalen Volumes, Build-Cache, inaktiven Containern ) |
| `docker system prune`                                    | gestoppte Container, unbenutzte Netzwerke, Images und den Build-Cache löschen                                |
| `docker compose down --remove-orphans`                   | Entferne Verweiste                                                                                           |
| `docker compose run <service> <befehl>`                  | Befehle im container ausführen - `<service>` enstpricht der Angabe in `docker-compose.yml`                   |
| `docker compose run app python --version`                | Python Version im conatiner abrufen                                                                          |
| `sudo netstat -tulpen`                                   | belegte Ports ansehen                                                                                        |

### Anpassungen vor dem Start

#### Rechte für den aktuellen Nutzer setzen 
Dies ist nur notwendig, wenn Daten aus dem Container in das lokale Dateisystem geschrieben werden sollen.

Nutzer id und Gruppen id bestimmen

```bash
id
```

env-example nach .env kopieren und die Ids in `.env` eintragen 

```env
USE_UID=<user_id>
USE_GID=<gruppen_id>
```

#### Configdatei anpassen
In dem Ordner, der beim Klonen des Repositorys erstellt wird, befindet sich ein Ordner `config`. Darin befindet sich die Datei **config.json**. In dieser Datei müssen die unter [Konfiguration](/docs/de/Konfiguration.md) beschriebenen Einstellungen vorgenommen werden.

Wichtige Abschnitte für die Anpassungen in der `config.json` Datei.
- server
  - webserver
  - mqtt
- database
  - servername
  - VMSCOM 
- dicom
  - VMSDBD
- units
- variables 
  
  
### Container erstellen und starten

1. Docker container erzeugen
```bash
docker compose build
```

2. Docker container starten
```bash
docker compose run --rm pygqa_0.2.x python ./pygqa.py
```

Die [GQA - Geräte-QA](http://127.0.0.1:5000/) Seite im Web-Browser öffnen.

Auf der pyGQA-Seite können unter dem Reiter **Systeminfo** einige Teile der erfolgreichen Installation kontrolliert werden. Siehe auch weiter oben unter **Erster Testlauf**.