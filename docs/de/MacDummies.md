Installation des Skeletts für Mac User ohne jegliche Ahnung
===========================================================

Installation von Miniconda (enthält Python 3.7 etc.)
----------------------------------------------------

Seite aufrufen:

https://repo.anaconda.com/miniconda/

Download des Pakets:

Miniconda3-4.6.14-MacOSX-x86_64.pkg

Ausführen des Pakets (geführte Installation mit Assistent), dabei:
Installation in Benutzerordner, z.B. Macintosh HD > Benutzer > deinname

Prüfe danach im Finder, dass in deinem Benutzerordner „deinname“ ein neuer Ordner „miniconda3“ angelegt wurde.


Prüfen der Installation
-----------------------

Terminal starten.

Du befindest dich in deinem Benutzerordner (Mac:~ deinname$)

Prüfe Versionen::

    ~/miniconda3/bin/python --version
    > Python 3.7.3 
    ~/miniconda3/bin/pip  --version
    > pip 19.0.3 or higher


Erstellen eines Arbeitsordners
------------------------------

Im Finder einen neuen Ordner für dieses Projekt anlegen, z.B. den Ordner „deinordner“ unter Dokumente. 


Download des Skeletts von GitHub
--------------------------------

Seite aufrufen:
https://github.com/MedPhyDO/app-skeleton

Klick auf den grünen Code-Button, Download ZIP
ZIP entpacken und den Ordner („app-skeleton-main“) in deinen Arbeitsordner (z.B. ~/deinname/Dokumente/deinordner) kopieren.


Installieren von benötigten Modulen
-----------------------------------

Terminal aufrufen.
Du befindest dich in deinem Benutzerordner (Mac:~ deinname$)
Navigiere in das Skelett-Repository in deinem Benutzerordner, z.B.:

    cd Dokumente/deinordner/app-skeleton-main
    
Installiere weitere benötigte Module:

    ~/miniconda3/bin/pip install -r requirements.txt
    
Installiere Javascript/CSS, Fonts etc.:

    ~/miniconda3/bin/python install-resources.py


Schriftart für Symbole installieren
-----------------------------------

Seite aufrufen:
https://github.com/Templarian/MaterialDesign-Webfont/blob/master/fonts/materialdesignicons-webfont.ttf

* Download von materialdesignicons-webfont.ttf
* Schriftsammlung (im Finder unter Anwendungen) öffnen.
* Über „+“ neue Schriftart hinzufügen.
* materialdesignicons-webfont.ttf im Download-Ordner auswählen und installieren.


Das Skelett loslaufen lassen
----------------------------

Skelett starten:

    ~/miniconda3/bin/python skeleton.py
    
Aufruf des Web-Servers:

    http://127.0.0.1:5000/

Dein Skelett läuft jetzt!
