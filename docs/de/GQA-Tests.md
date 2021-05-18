
Die Zuordnung des jeweiligen Test erfolgt durch die Eingabe eines **tag** im Aria Bestrahlungsfeld unter `Feldeigenschaften Kommentar`

Im Kommentarfeld können in seperaten Zeilen mehrere Tests angegeben werden.  
Bei jeder dieser Angaben ist es, durch einen Doppelpunkt getrennt, möglich eine spezielle Zuordnung vorzunehmen.

Diese Tagging Informationen dienen dazu die passenden Aufnahmen für einen Test in der Datenbank zu bestimmen.  
Über den DICOM Zugriff werden dann die gefunden Aufnahmen für die Auswertung geladen.
  

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
