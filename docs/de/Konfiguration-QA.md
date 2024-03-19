# Konfiguration Geräte QA

Beschreibung der zusätzliche Konfigurationsmöglichkeiten für die Geräte-QA.


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

Beispiel für die LeafSpeed Konfiguration:
```json
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
```

