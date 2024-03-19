
Wir nutzen folgenden Aufbau für unsere Testpläne:

Pro Beschleuniger ist ein Test-Patient in ARIA angelegt (z.B. "QA, VitalBeam").
Für diesen Patienten werden Behandlungsreihen entsprechend der Testfrequenz angelegt,
z.B. "Monatstest" oder "Jahrestest".  
Innerhalb der Behandlungsreihen liegen dann die Bestrahlungspläne für die einzelnen Tests,
z.B. "Linearität MU" oder "MLC Leaf Speed".

Die MV-Aufnahmen werden alle im Portal Imaging Modus (teilweise auch "Integrated Image" genannt) aufgenommen.  
Für diesen Modus liegt eine Dosiskalibration vor, so dass ein Zusammenhang zwischen dem mittleren Pixelwert (in kalibrierten Einheiten "KE" oder calibrated units "CU" angezeigt) und der Wasser-Energiedosis in Gy besteht. Regelmäßige Kalibration der Bildeinheit im Service Modus beachten.

Um die durchgeführten MV-Aufnahmen einem Test zuzuordnen, verwenden wir Tagging Informationen im Aria Bestrahlungsfeld unter `Feldeigenschaften Kommentar`:

Für jeden Test wurde ein **tag** festgelegt, z.B. "MT_LeafSpeed" für einen monatlichen Lamellen-Geschwindigkeitstest.
Dieser **tag** wird in ARIA in die Informationen aller zum Test gehörenden Felder geschrieben.
Dazu (bspw. im Modul Planparameter) die Eigenschaften eines Felds anzeigen lassen und im Tab Kommentar den **tag** eintragen.
Diese Tagging Informationen dienen dazu die passenden Aufnahmen für einen Test in der Datenbank zu bestimmen. 
Über den DICOM Zugriff werden dann die gefunden Aufnahmen für die Auswertung geladen.

Ein Feld kann für die Auswertung mehrerer Tests verwendet werden, dazu einfach die entsprechenden **tags** im Kommentarfeld zeilenweise untereinander notieren.

Darüber hinaus kann ein Feld auch mit einer besonderen Markierung versehen werden,
beispielsweise weil es als Referenzfeld für alle anderen Felder gilt.
Dafür wird hinter den **tag** ein Doppelpunkt und eine entsprechende Bezeichnung gesetzt, z.B. "MT_4.1.2:base" für das 100MU Feld.
  

MT_4.1.2 - Linearität des Dosismonitorsystems bei kleinen Dosismonitorwerten
============================================================================

![MT_4.12.png](/docs/MT-4_1_2.png "MT_4.12.png")

Tags: 
* MT_4.1.2 - Kennzeichnet alle Felder für diesen Test
* MT_4.1.2:base - Kennzeichnet das Basisfeld für die Auswertung der jeweiligen Dosis (100MU)


MT_LeafSpeed - Geschwindigkeit und Geschwindigkeitsänderung der Lamellen
========================================================================

![MT_LeafSpeed.png](/docs/MT_LeafSpeed.png "MT_LeafSpeed.png")

Tags:
* MT_LeafSpeed - Kennzeichnet alle Felder für diesen Test
* MT_LeafSpeed:gating - Kennzeichnet die Felder die unter Gating Bedingungen abgestrahlt werden.
