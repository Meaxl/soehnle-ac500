# CLAUDE.md

## Projektübersicht

Dieses Repository enthält eine Home Assistant Custom Integration für den
Luftreiniger **Soehnle Airfresh Clean 500 (AC500)**.

Ziel ist die lokale oder cloud-basierte Integration des Geräts in Home
Assistant mit Fokus auf: - Stabilität - Wartbarkeit - Home Assistant
Best Practices

------------------------------------------------------------------------

## Repository Struktur

    soehnle-ac500/
    ├── .github/workflows/              # CI/CD Pipelines (Validation + Release)
    │   ├── publish.yml
    │   └── validate-homeassistant.yaml
    ├── custom_components/soehnle_ac500/  # Hauptintegration (komplette Logik)
    │   ├── translations/en.json        # UI Übersetzungen
    │   ├── __init__.py                # Setup & Initialisierung
    │   ├── binary_sensor.py           # Status-Sensoren
    │   ├── ble_client.py              # Bluetooth Kommunikation (Core!)
    │   ├── config_flow.py             # UI Setup Flow
    │   ├── const.py                   # Konstanten
    │   ├── coordinator.py             # DataUpdateCoordinator (State Handling)
    │   ├── entity_base.py             # Gemeinsame Entity-Basis
    │   ├── fan.py                     # Lüftersteuerung
    │   ├── manifest.json              # HA Metadaten
    │   ├── select.py                  # Auswahl-Entities
    │   ├── sensor.py                  # Messwerte
    │   ├── strings.json               # UI Texte
    │   └── switch.py                  # Schalter
    ├── .gitignore                     # Git Ignore Regeln
    ├── LICENSE                        # Lizenz
    ├── README.md                      # Dokumentation
    ├── hacs.json                      # HACS Definition
    ├── pyproject.toml                 # Dev Tooling
    └── CLAUDE.md                      # Diese Datei

### Wichtige Einstiegspunkte

-   **BLE / Gerätelogik** → `ble_client.py`
-   **Datenfluss / Updates** → `coordinator.py`
-   **Entities** → `fan.py`, `sensor.py`, `switch.py`, etc.
-   **Setup/UI** → `config_flow.py`

------------------------------------------------------------------------

## Architektur

Die Integration folgt den offiziellen Home Assistant Guidelines:

-   `__init__.py`\
    Setup der Integration und Koordination

-   `config_flow.py`\
    UI-basierte Einrichtung (Config Entries)

-   `coordinator.py`\
    Zentrale Datenbeschaffung via `DataUpdateCoordinator`

-   `fan.py` / `sensor.py` / `switch.py`\
    Plattformen für Entities

-   `const.py`\
    Konstanten (Domain, Defaults, Keys)

-   `manifest.json`\
    Metadaten der Integration

------------------------------------------------------------------------

## Grundprinzipien

### 1. Home Assistant Standards einhalten

-   Nutze `DataUpdateCoordinator` für API-Kommunikation
-   Entities dürfen **keine direkte API-Kommunikation** enthalten
-   Verwende `async_*` Methoden überall, wo möglich

### 2. Kein Blocking Code

-   Keine synchronen Netzwerkaufrufe im Event Loop
-   Falls nötig: `hass.async_add_executor_job`

### 3. Klare Trennung von Verantwortung

-   API-Logik → eigene Klasse (z. B. `api.py`)
-   Coordinator → orchestriert Updates
-   Entities → nur Darstellung

### 4. Fehlerbehandlung

-   Netzwerkfehler sauber abfangen
-   `UpdateFailed` im Coordinator verwenden

------------------------------------------------------------------------

## Code-Stil

-   Python ≥ 3.11
-   Typisierung verpflichtend (`typing`)
-   `ruff` / `black` kompatibel

### Variablennamen

-   Englisch
-   snake_case (Variablen/Funktionen)
-   PascalCase (Klassen)

### Kommentare

-   Deutsch
-   Fokus auf:
    -   komplexe Logik
    -   Workarounds
    -   Geräteverhalten

------------------------------------------------------------------------

## Entity-Richtlinien

-   Eindeutige `unique_id`
-   `device_info` setzen
-   Keine redundanten Namen

------------------------------------------------------------------------

## Config Flow

-   UI-basiert
-   Fehlerhandling Pflicht
-   Kein YAML

------------------------------------------------------------------------

## API-Integration

-   Keine Logik in Entities
-   Timeouts + Retry
-   Kapselung

------------------------------------------------------------------------

## Testing & Debugging

-   `_LOGGER` verwenden
-   Keine `print()`

------------------------------------------------------------------------

## Claude Guidelines

### Do

-   Architektur respektieren
-   Coordinator nutzen
-   Minimal invasive Änderungen

### Don't

-   Blocking Code
-   API in Entities
-   Unnötige Refactorings

------------------------------------------------------------------------

## Domain

DOMAIN = "soehnle_ac500"

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- ALWAYS read graphify-out/GRAPH_REPORT.md before reading any source files, running grep/glob searches, or answering codebase questions. The graph is your primary map of the codebase.
- IF graphify-out/wiki/index.md EXISTS, navigate it instead of reading raw files
- For cross-module "how does X relate to Y" questions, prefer `graphify query "<question>"`, `graphify path "<A>" "<B>"`, or `graphify explain "<concept>"` over grep — these traverse the graph's EXTRACTED + INFERRED edges instead of scanning files
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
