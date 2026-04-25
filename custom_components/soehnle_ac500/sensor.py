"""Sensor entities – PM2.5, Temperature, Air Quality, Filter, EF04/EF02 diagnostics."""
from __future__ import annotations

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, UnitOfTemperature, PERCENTAGE
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
    device_name = entry.data.get(CONF_NAME, "Soehnle AC500")
    async_add_entities([
        AC500PM25Sensor(coordinator, entry, device_name),
        AC500TempSensor(coordinator, entry, device_name),
        AC500AirQualitySensor(coordinator, entry, device_name),
        AC500FilterUsedSensor(coordinator, entry, device_name),
        AC500FilterRemainingSensor(coordinator, entry, device_name),
        AC500FilterPctSensor(coordinator, entry, device_name),
        AC500EF04DiagSensor(coordinator, entry, device_name, 0, "ef04_pair0"),
        AC500EF04DiagSensor(coordinator, entry, device_name, 2, "ef04_pair2"),
        AC500EF04DiagSensor(coordinator, entry, device_name, 3, "ef04_pair3"),
        AC500EF04DiagSensor(coordinator, entry, device_name, 5, "ef04_pair5"),
        AC500EF04DiagSensor(coordinator, entry, device_name, 6, "ef04_pair6"),
        AC500EF04DiagSensor(coordinator, entry, device_name, 7, "ef04_pair7"),
        AC500EF04RawSensor(coordinator, entry, device_name),
        AC500EF03RawSensor(coordinator, entry, device_name),
        AC500D0FFRawSensor(coordinator, entry, device_name, "ffd2"),
        AC500D0FFRawSensor(coordinator, entry, device_name, "ffd3"),
        AC500D0FFRawSensor(coordinator, entry, device_name, "ffd4"),
        AC500D0FFRawSensor(coordinator, entry, device_name, "ffd5"),
        AC500D0FFRawSensor(coordinator, entry, device_name, "fff1"),
    ])


class _SensorBase(AC500EntityBase, SensorEntity):
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry, device_name, suffix):
        super().__init__(coordinator, entry, suffix)


class AC500PM25Sensor(_SensorBase):
    _attr_device_class               = SensorDeviceClass.PM25
    _attr_native_unit_of_measurement = "µg/m³"
    _attr_icon                       = "mdi:air-filter"
    _attr_suggested_display_precision = 1

    def __init__(self, coordinator, entry, device_name):
        super().__init__(coordinator, entry, device_name, "pm25")
        self._attr_name = f"{device_name} PM2.5"

    @property
    def native_value(self) -> float | None:
        return self._coordinator.state.pm25 if self._coordinator.state.ever_seen else None


class AC500TempSensor(_SensorBase):
    _attr_device_class               = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_suggested_display_precision = 1

    def __init__(self, coordinator, entry, device_name):
        super().__init__(coordinator, entry, device_name, "temperature")
        self._attr_name = f"{device_name} Temperature"

    @property
    def available(self) -> bool:
        return (self._coordinator.state.ever_seen
                and self._coordinator.state.temperature is not None)

    @property
    def native_value(self) -> float | None:
        return self._coordinator.state.temperature


# PM2.5 thresholds based on WHO 2021 / EPA AQI breakpoints
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
    """Categorical air quality derived from PM2.5 reading."""

    _attr_device_class  = SensorDeviceClass.ENUM
    _attr_options       = ["Good", "Moderate", "Unhealthy_sensitive",
                           "Unhealthy", "Very_unhealthy", "Hazardous"]
    _attr_icon          = "mdi:leaf"

    def __init__(self, coordinator, entry, device_name):
        super().__init__(coordinator, entry, "air_quality")
        self._attr_name = f"{device_name} Air Quality"

    @property
    def native_value(self) -> str | None:
        if not self._coordinator.state.ever_seen:
            return None
        return _pm25_to_quality(self._coordinator.state.pm25)


class AC500FilterUsedSensor(_SensorBase):
    """Filter hours used – extracted from EF02 p[9:11]."""

    _attr_native_unit_of_measurement = "h"
    _attr_icon                       = "mdi:air-filter"
    _attr_suggested_display_precision = 0

    def __init__(self, coordinator, entry, device_name):
        super().__init__(coordinator, entry, device_name, "filter_used_hours")
        self._attr_name = f"{device_name} Filter Used Hours"

    @property
    def available(self) -> bool:
        return (self._coordinator.state.ever_seen
                and self._coordinator.state.filter_total_hours > 0)

    @property
    def native_value(self) -> int | None:
        return self._coordinator.state.filter_used_hours


class AC500FilterRemainingSensor(_SensorBase):
    """Filter hours remaining – calculated from EF02 filter data."""

    _attr_native_unit_of_measurement = "h"
    _attr_icon                       = "mdi:air-filter"
    _attr_suggested_display_precision = 0

    def __init__(self, coordinator, entry, device_name):
        super().__init__(coordinator, entry, device_name, "filter_remaining_hours")
        self._attr_name = f"{device_name} Filter Remaining Hours"

    @property
    def available(self) -> bool:
        return (self._coordinator.state.ever_seen
                and self._coordinator.state.filter_total_hours > 0)

    @property
    def native_value(self) -> int | None:
        return self._coordinator.state.filter_remaining_hours


class AC500FilterPctSensor(_SensorBase):
    """Filter usage percentage – matches app display."""

    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_icon                       = "mdi:air-filter"
    _attr_suggested_display_precision = 1

    def __init__(self, coordinator, entry, device_name):
        super().__init__(coordinator, entry, device_name, "filter_pct_used")
        self._attr_name = f"{device_name} Filter Usage"

    @property
    def available(self) -> bool:
        return (self._coordinator.state.ever_seen
                and self._coordinator.state.filter_total_hours > 0)

    @property
    def native_value(self) -> float | None:
        return self._coordinator.state.filter_pct_used


class AC500EF04DiagSensor(AC500EntityBase, SensorEntity):
    """Raw EF04 pair value – diagnostic aid for reverse-engineering."""

    _attr_state_class    = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon           = "mdi:help-rhombus-outline"

    def __init__(self, coordinator, entry, device_name, pair_idx: int,
                 state_attr: str) -> None:
        super().__init__(coordinator, entry, f"ef04_pair{pair_idx}")
        self._state_attr = state_attr
        self._attr_name  = f"{device_name} EF04 Pair{pair_idx} (raw)"

    @property
    def available(self) -> bool:
        return (self._coordinator.state.ever_seen
                and getattr(self._coordinator.state, self._state_attr) is not None)

    @property
    def native_value(self) -> int | None:
        return getattr(self._coordinator.state, self._state_attr)


class AC500EF04RawSensor(AC500EntityBase, SensorEntity):
    """Full raw EF04 payload as hex – for payload length and unknown bytes analysis."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon            = "mdi:format-list-numbered"

    def __init__(self, coordinator, entry, device_name) -> None:
        super().__init__(coordinator, entry, "ef04_raw_hex")
        self._attr_name = f"{device_name} EF04 Raw Payload"

    @property
    def available(self) -> bool:
        return (self._coordinator.state.ever_seen
                and self._coordinator.state.ef04_raw_hex is not None)

    @property
    def native_value(self) -> str | None:
        return self._coordinator.state.ef04_raw_hex


class AC500EF03RawSensor(AC500EntityBase, SensorEntity):
    """Full raw EF03 payload as hex – characteristic purpose unknown."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon            = "mdi:help-rhombus-outline"

    def __init__(self, coordinator, entry, device_name) -> None:
        super().__init__(coordinator, entry, "ef03_raw_hex")
        self._attr_name = f"{device_name} EF03 Raw Payload"

    @property
    def available(self) -> bool:
        return self._coordinator.state.ef03_raw_hex is not None

    @property
    def native_value(self) -> str | None:
        return self._coordinator.state.ef03_raw_hex


class AC500D0FFRawSensor(AC500EntityBase, SensorEntity):
    """Raw hex value of a d0ff service read-only characteristic (filter data candidate)."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon            = "mdi:filter-cog-outline"

    def __init__(self, coordinator, entry, device_name, char_name: str) -> None:
        super().__init__(coordinator, entry, f"{char_name}_raw_hex")
        self._char_attr   = f"{char_name}_raw_hex"
        self._attr_name   = f"{device_name} {char_name.upper()} Raw"

    @property
    def available(self) -> bool:
        return getattr(self._coordinator.state, self._char_attr) is not None

    @property
    def native_value(self) -> str | None:
        return getattr(self._coordinator.state, self._char_attr)
