"""Sensor-Entitäten – PM2.5, Temperatur, Luftqualität, Filter, EF04/EF02-Diagnose."""
from __future__ import annotations

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import AC500Coordinator
from .entity_base import AC500EntityBase

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry,
                            async_add_entities: AddEntitiesCallback) -> None:
    coordinator: AC500Coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        AC500PM25Sensor(coordinator, entry),
        AC500TempSensor(coordinator, entry),
        AC500AirQualitySensor(coordinator, entry),
        AC500FilterUsedSensor(coordinator, entry),
        AC500FilterRemainingSensor(coordinator, entry),
        AC500FilterPctSensor(coordinator, entry),
        AC500EF04DiagSensor(coordinator, entry, 0, "ef04_pair0"),
        AC500EF04DiagSensor(coordinator, entry, 2, "ef04_pair2"),
        AC500EF04DiagSensor(coordinator, entry, 3, "ef04_pair3"),
        AC500EF04DiagSensor(coordinator, entry, 5, "ef04_pair5"),
        AC500EF04DiagSensor(coordinator, entry, 6, "ef04_pair6"),
        AC500EF04DiagSensor(coordinator, entry, 7, "ef04_pair7"),
        AC500EF04RawSensor(coordinator, entry),
        AC500EF03RawSensor(coordinator, entry),
        AC500D0FFRawSensor(coordinator, entry, "ffd2"),
        AC500D0FFRawSensor(coordinator, entry, "ffd3"),
        AC500D0FFRawSensor(coordinator, entry, "ffd4"),
        AC500D0FFRawSensor(coordinator, entry, "ffd5"),
        AC500D0FFRawSensor(coordinator, entry, "fff1"),
    ])


class _SensorBase(AC500EntityBase, SensorEntity):
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: AC500Coordinator, entry: ConfigEntry,
                 suffix: str) -> None:
        super().__init__(coordinator, entry, suffix)


class AC500PM25Sensor(_SensorBase):
    _attr_device_class               = SensorDeviceClass.PM25
    _attr_native_unit_of_measurement = "µg/m³"
    _attr_icon                       = "mdi:air-filter"
    _attr_suggested_display_precision = 1

    def __init__(self, coordinator: AC500Coordinator,
                 entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "pm25")
        self._attr_name = "PM2.5"

    @property
    def native_value(self) -> float | None:
        return self._coordinator.state.pm25 if self._coordinator.state.ever_seen else None


class AC500TempSensor(_SensorBase):
    _attr_device_class               = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_suggested_display_precision = 1

    def __init__(self, coordinator: AC500Coordinator,
                 entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "temperature")
        self._attr_name = "Temperature"

    @property
    def available(self) -> bool:
        return (self._coordinator.state.ever_seen
                and self._coordinator.state.temperature is not None)

    @property
    def native_value(self) -> float | None:
        return self._coordinator.state.temperature


# PM2.5-Grenzwerte gemäß WHO 2021 / EPA AQI
def _pm25_to_quality(pm25: float) -> str:
    if pm25 <= 12.0:
        return "Good"
    if pm25 <= 35.4:
        return "Moderate"
    if pm25 <= 55.4:
        return "Unhealthy_sensitive"
    if pm25 <= 150.4:
        return "Unhealthy"
    if pm25 <= 250.4:
        return "Very_unhealthy"
    return "Hazardous"


class AC500AirQualitySensor(AC500EntityBase, SensorEntity):
    """Kategorische Luftqualität abgeleitet aus dem PM2.5-Messwert."""

    _attr_device_class  = SensorDeviceClass.ENUM
    _attr_options       = ["Good", "Moderate", "Unhealthy_sensitive",
                           "Unhealthy", "Very_unhealthy", "Hazardous"]
    _attr_icon          = "mdi:leaf"

    def __init__(self, coordinator: AC500Coordinator,
                 entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "air_quality")
        self._attr_name = "Air Quality"

    @property
    def native_value(self) -> str | None:
        if not self._coordinator.state.ever_seen:
            return None
        return _pm25_to_quality(self._coordinator.state.pm25)


class AC500FilterUsedSensor(_SensorBase):
    """Genutzte Filterstunden – aus EF02 p[9:11]."""

    _attr_native_unit_of_measurement = "h"
    _attr_icon                       = "mdi:air-filter"
    _attr_suggested_display_precision = 0

    def __init__(self, coordinator: AC500Coordinator,
                 entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "filter_used_hours")
        self._attr_name = "Filter Used Hours"

    @property
    def available(self) -> bool:
        return (self._coordinator.state.ever_seen
                and self._coordinator.state.filter_total_hours > 0)

    @property
    def native_value(self) -> int | None:
        return self._coordinator.state.filter_used_hours


class AC500FilterRemainingSensor(_SensorBase):
    """Verbleibende Filterstunden – berechnet aus EF02-Filterdaten."""

    _attr_native_unit_of_measurement = "h"
    _attr_icon                       = "mdi:air-filter"
    _attr_suggested_display_precision = 0

    def __init__(self, coordinator: AC500Coordinator,
                 entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "filter_remaining_hours")
        self._attr_name = "Filter Remaining Hours"

    @property
    def available(self) -> bool:
        return (self._coordinator.state.ever_seen
                and self._coordinator.state.filter_total_hours > 0)

    @property
    def native_value(self) -> int | None:
        return self._coordinator.state.filter_remaining_hours


class AC500FilterPctSensor(_SensorBase):
    """Filternutzung in Prozent – entspricht der App-Anzeige."""

    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_icon                       = "mdi:air-filter"
    _attr_suggested_display_precision = 1

    def __init__(self, coordinator: AC500Coordinator,
                 entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "filter_pct_used")
        self._attr_name = "Filter Usage"

    @property
    def available(self) -> bool:
        return (self._coordinator.state.ever_seen
                and self._coordinator.state.filter_total_hours > 0)

    @property
    def native_value(self) -> float | None:
        return self._coordinator.state.filter_pct_used


class AC500EF04DiagSensor(AC500EntityBase, SensorEntity):
    """Rohwert eines EF04-Paares – Diagnosehilfe für Reverse-Engineering."""

    _attr_state_class    = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _attr_icon           = "mdi:help-rhombus-outline"

    def __init__(self, coordinator: AC500Coordinator, entry: ConfigEntry,
                 pair_idx: int, state_attr: str) -> None:
        super().__init__(coordinator, entry, f"ef04_pair{pair_idx}")
        self._state_attr = state_attr
        self._attr_name  = f"EF04 Pair{pair_idx} (raw)"

    @property
    def available(self) -> bool:
        return (self._coordinator.state.ever_seen
                and getattr(self._coordinator.state, self._state_attr) is not None)

    @property
    def native_value(self) -> int | None:
        return getattr(self._coordinator.state, self._state_attr)


class AC500EF04RawSensor(AC500EntityBase, SensorEntity):
    """Vollständiger EF04-Rohpayload als Hex – zur Analyse von Länge und unbekannten Bytes."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _attr_icon            = "mdi:format-list-numbered"

    def __init__(self, coordinator: AC500Coordinator,
                 entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "ef04_raw_hex")
        self._attr_name = "EF04 Raw Payload"

    @property
    def available(self) -> bool:
        return (self._coordinator.state.ever_seen
                and self._coordinator.state.ef04_raw_hex is not None)

    @property
    def native_value(self) -> str | None:
        return self._coordinator.state.ef04_raw_hex


class AC500EF03RawSensor(AC500EntityBase, SensorEntity):
    """Vollständiger EF03-Rohpayload als Hex – Zweck der Charakteristik noch unbekannt."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon            = "mdi:help-rhombus-outline"

    def __init__(self, coordinator: AC500Coordinator,
                 entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "ef03_raw_hex")
        self._attr_name = "EF03 Raw Payload"

    @property
    def available(self) -> bool:
        return self._coordinator.state.ef03_raw_hex is not None

    @property
    def native_value(self) -> str | None:
        return self._coordinator.state.ef03_raw_hex


class AC500D0FFRawSensor(AC500EntityBase, SensorEntity):
    """Rohwert einer d0ff-Charakteristik als Hex – statische Gerätekennung."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _attr_icon            = "mdi:filter-cog-outline"

    def __init__(self, coordinator: AC500Coordinator, entry: ConfigEntry,
                 char_name: str) -> None:
        super().__init__(coordinator, entry, f"{char_name}_raw_hex")
        self._char_attr   = f"{char_name}_raw_hex"
        self._attr_name   = f"{char_name.upper()} Raw"

    @property
    def available(self) -> bool:
        return getattr(self._coordinator.state, self._char_attr) is not None

    @property
    def native_value(self) -> str | None:
        return getattr(self._coordinator.state, self._char_attr)
