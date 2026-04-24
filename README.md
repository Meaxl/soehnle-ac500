# Soehnle Airfresh Clean Connect 500 – Home Assistant Integration

Eine inoffizielle Home Assistant Custom Component zur lokalen Steuerung des **Soehnle Airfresh Clean Connect 500** Luftreinigers via Bluetooth Low Energy (BLE). Keine Cloud, keine App – vollständige Kontrolle direkt aus Home Assistant.

---

## Inhaltsverzeichnis

- [Features](#features)
- [Voraussetzungen](#voraussetzungen)
- [Installation](#installation)
  - [Methode 1: HACS (empfohlen)](#methode-1-hacs-empfohlen)
  - [Methode 2: Manuelle Installation](#methode-2-manuelle-installation)
- [Einrichtung](#einrichtung)
- [Entitäten](#entitäten)
- [Bekannte Einschränkungen](#bekannte-einschränkungen)
- [Technische Details](#technische-details)

---

## Features

- Lokale BLE-Verbindung – kein Cloud-Zugriff erforderlich
- Automatische Wiederverbindung bei Verbindungsabbruch
- Letzter bekannter Zustand bleibt sichtbar bei kurzen Unterbrechungen
- Vollständige Steuerung über die Home Assistant UI und Automationen

**Unterstützte Funktionen:**

| Funktion | Status |
|---|---|
| Ein-/Ausschalten | Funktionsfähig |
| Lüftergeschwindigkeit (4 Stufen) | Funktionsfähig |
| Automatikmodus | Funktionsfähig |
| UV-C Licht | Funktionsfähig |
| Timer (2h / 4h / 8h) | Funktionsfähig |
| PM2.5 Feinstaubsensor | Funktionsfähig |
| Temperatursensor | Funktionsfähig |
| Nachtmodus | In Entwicklung |
| Luftfeuchtigkeitssensor | Nicht bestätigt |

---

## Voraussetzungen

- Home Assistant **2023.8** oder neuer
- Bluetooth-Adapter, der von Home Assistant erkannt wird (integriert oder USB)
- MAC-Adresse des Geräts (auffindbar unter **Einstellungen → Geräte & Dienste → Bluetooth**)
- Optional: [HACS](https://hacs.xyz/) für die empfohlene Installationsmethode

---

## Installation

### Methode 1: HACS (empfohlen)

Diese Methode ermöglicht automatische Updates über HACS.

1. Öffne HACS in Home Assistant
2. Klicke oben rechts auf die drei Punkte → **Benutzerdefinierte Repositories**
3. Füge folgende URL als Repository hinzu und wähle die Kategorie **Integration**:
   ```
   https://github.com/Meaxl/soehnle-ac500
   ```
4. Suche in HACS nach **Soehnle AC500** und klicke auf **Herunterladen**
5. Starte Home Assistant neu

### Methode 2: Manuelle Installation

1. Lade dieses Repository als ZIP-Datei herunter oder klone es:
   ```
   git clone https://github.com/Meaxl/soehnle-ac500.git
   ```
2. Kopiere den Ordner `custom_components/soehnle_ac500` in dein Home Assistant Konfigurationsverzeichnis:
   ```
   <config>/custom_components/soehnle_ac500/
   ```
   Der Pfad `<config>` ist üblicherweise `/config` (bei Home Assistant OS) oder `~/.homeassistant/`.
3. Starte Home Assistant neu

---

## Einrichtung

1. Navigiere zu **Einstellungen → Geräte & Dienste → Integration hinzufügen**
2. Suche nach **Soehnle AC500**
3. Gib folgende Informationen ein:
   - **Name:** Beliebiger Anzeigename (z. B. `Soehnle Airfresh AC500`)
   - **Bluetooth-Adresse:** MAC-Adresse des Geräts (Format: `48:87:2D:1F:DB:EB`)
4. Bestätige mit **Senden**

Die MAC-Adresse des Geräts lässt sich am einfachsten ermitteln, indem das Gerät eingeschaltet und paarungsbereit ist und dann unter **Einstellungen → Geräte & Dienste → Bluetooth** nach neuen Geräten gesucht wird.

---

## Entitäten

Nach erfolgreicher Einrichtung werden folgende Entitäten erstellt:

### Lüfter (`fan`)

| Eigenschaft | Beschreibung |
|---|---|
| Ein/Aus | Schaltet das Gerät ein oder aus |
| Geschwindigkeit | 4 Stufen (25 % / 50 % / 75 % / 100 %) |
| Voreinstellungsmodi | `speed_1`, `speed_2`, `speed_3`, `speed_4`, `auto` |

### Schalter (`switch`)

| Entität | Beschreibung |
|---|---|
| UV-C | Schaltet die UV-C-Entkeimungslampe ein/aus |
| Nachtmodus | Aktiviert den leisen Nachtbetrieb *(in Entwicklung)* |

### Sensoren (`sensor`)

| Entität | Einheit | Geräteklasse |
|---|---|---|
| PM2.5 | µg/m³ | `pm25` |
| Temperatur | °C | `temperature` |
| Luftfeuchtigkeit | % | `humidity` *(nicht bestätigt)* |

### Auswahl (`select`)

| Entität | Optionen | Beschreibung |
|---|---|---|
| Timer | `off`, `2h`, `4h`, `8h` | Automatisches Abschalten nach gewählter Zeit |

---

## Bekannte Einschränkungen

- **Nachtmodus:** Die Schalter-Entität ist vorhanden, die Funktion ist jedoch noch nicht vollständig implementiert und getestet.
- **Luftfeuchtigkeit:** Der Sensor wird ausgelesen, die Werte wurden noch nicht mit einem Referenzgerät validiert.
- **Bluetooth-Reichweite:** Die Verbindungsqualität hängt direkt von der Entfernung und möglichen Hindernissen zwischen Bluetooth-Adapter und Gerät ab.
- **Einzelverbindung:** Das Gerät kann jeweils nur mit einer BLE-Quelle verbunden sein. Während Home Assistant verbunden ist, ist die Original-App möglicherweise nicht nutzbar.

---

## Technische Details

Die Integration kommuniziert ausschließlich über Bluetooth Low Energy mit dem Gerät und benötigt keine Internetverbindung.

**BLE-Protokoll:**

| UUID | Richtung | Beschreibung |
|---|---|---|
| `EF01` | Schreiben | Befehle senden (Steuerung) |
| `EF02` | Lesen / Notify | Gerätezustand (Lüfter, PM2.5, Flags) |
| `EF04` | Lesen | Umgebungsdaten (Temperatur, Luftfeuchtigkeit) |

**Verbindungsmanagement:**
- Wiederverbindungsintervall: 5 Sekunden
- Keepalive-Timeout: 15 Sekunden (Neuverbindung falls keine Notify empfangen)
- IoT-Klasse: `local_push`

---

> Diese Integration ist ein inoffizielles Community-Projekt und steht in keiner Verbindung zur Firma Soehnle.
