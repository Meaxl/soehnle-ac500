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
| Nachtmodus | IN ENTWICKLUNG |
| Timer (2h / 4h / 8h) | Funktionsfähig |
| PM2.5 Feinstaubsensor | Funktionsfähig |
| Temperatursensor | Funktionsfähig |
| Luftqualitätssensor | Funktionsfähig |
| Filter-Nutzungsanzeige | Funktionsfähig |

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
| Night Mode | Aktiviert den leisen Nachtbetrieb, Lichter aus|

### Sensoren (`sensor`)

| Entität | Einheit | Beschreibung |
|---|---|---|
| PM2.5 | µg/m³ | Feinstaubkonzentration in Echtzeit |
| Temperatur | °C | Raumtemperatur (aus EF04-History-Buffer) |
| Luftqualität | – | Kategorisch: `Good` / `Moderate` / `Unhealthy_sensitive` / `Unhealthy` / `Very_unhealthy` / `Hazardous` |
| Filter Used Hours | h | Bisherige Betriebsstunden des Filters |
| Filter Remaining Hours | h | Verbleibende Stunden bis zum Filterwechsel |
| Filter Usage | % | Prozentualer Filterverbrauch (entspricht App-Anzeige) |

### Diagnose-Sensoren (`sensor` – standardmäßig deaktiviert)

Diese Sensoren sind für Debugging und Reverse-Engineering gedacht und standardmäßig deaktiviert. Sie können unter **Einstellungen → Geräte & Dienste → Entitäten** manuell aktiviert werden.

| Entität | Beschreibung |
|---|---|
| EF03 Raw Payload | Rohdaten der EF03-Charakteristik (Zweck noch unbekannt) |
| EF04 Pair0/2/3/5/6/7 (raw) | Einzelne Paare des EF04-History-Buffers |
| EF04 Raw Payload | Vollständiger EF04-Rohpayload als Hex-String |
| FFD2 / FFD3 / FFD4 / FFD5 / FFF1 Raw | Statische Gerätekennungen des d0ff-BLE-Service |

### Binärsensor (`binary_sensor` – standardmäßig deaktiviert)

| Entität | Beschreibung |
|---|---|
| Connection | Zeigt den aktuellen BLE-Verbindungsstatus (`on` = verbunden) |

### Auswahl (`select`)

| Entität | Optionen | Beschreibung |
|---|---|---|
| Timer | `off`, `2h`, `4h`, `8h` | Automatisches Abschalten nach gewählter Zeit |

---

## Bekannte Einschränkungen

- **Bluetooth-Reichweite:** Die Verbindungsqualität hängt direkt von der Entfernung und möglichen Hindernissen zwischen Bluetooth-Adapter und Gerät ab.
- **Einzelverbindung:** Das Gerät kann jeweils nur mit einer BLE-Quelle verbunden sein. Während Home Assistant verbunden ist, ist die Original-App möglicherweise nicht nutzbar.
- **Diagnose-Sensoren:** Standardmäßig deaktiviert, da sie für den normalen Betrieb nicht benötigt werden. Die EF03-Charakteristik wird überwacht, ihr genauer Zweck ist jedoch noch nicht vollständig bekannt.

---

## Technische Details

Die Integration kommuniziert ausschließlich über Bluetooth Low Energy mit dem Gerät und benötigt keine Internetverbindung.

**BLE-Protokoll:**

| UUID | Richtung | Beschreibung |
|---|---|---|
| `EF01` | Schreiben | Steuerbefehle (Ein/Aus, Geschwindigkeit, Modi) |
| `EF02` | Notify | Gerätezustand: Lüfterdaten, Flags, PM2.5, Filterdaten |
| `EF03` | Notify | Unbekannte Charakteristik (wird überwacht) |
| `EF04` | Notify | History-Buffer: abwechselnde (PM2.5_raw, Temp×10)-Paare |
| `FFD2–FFF1` | Lesen | Statische Gerätekennungen (proprietärer d0ff-Service) |

**EF02-Filterdaten (reverse-engineered):**

Die Filterdaten sind direkt im EF02-Notify-Frame kodiert:
- Bytes `p[7:9]` (big-endian uint16) = Filter-Gesamtlaufzeit in Stunden (z. B. `0x10E0` = 4320 h)
- Bytes `p[9:11]` (big-endian uint16) = bisher genutzte Filterstunden

**Verbindungsmanagement:**
- Wiederverbindungsintervall: 5 Sekunden
- Keepalive-Timeout: 15 Sekunden (Neuverbindung falls keine Notify empfangen)
- IoT-Klasse: `local_push`

---

> Diese Integration ist ein inoffizielles Community-Projekt und steht in keiner Verbindung zur Firma Soehnle.
