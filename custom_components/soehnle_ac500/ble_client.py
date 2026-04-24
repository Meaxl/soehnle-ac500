"""BLE client using bleak_retry_connector for reliable connections."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Callable

from bleak import BleakClient
from bleak.exc import BleakError
from bleak_retry_connector import (
    BleakClientWithServiceCache,
    establish_connection,
)

from .const import (
    UUID_WRITE, UUID_EF02, UUID_EF04,
    FLAG_POWER, FLAG_UVC, FLAG_TIMER, FLAG_AUTO, FLAG_NIGHT,
    SPEED_MAP, COMMANDS,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class AC500State:
    # ── Control state (EF02) ────────────────────────────────────────────
    power:       bool  = False
    uvc:         bool  = False
    night:       bool  = False
    auto:        bool  = False
    timer_on:    bool  = False
    speed:       int   = 0        # 0-3
    timer_val:   int   = 0        # 0/2/4/8 hours
    pm25_raw:    int   = 0        # ÷10 = µg/m³
    # ── Environmental sensors (EF04 snapshot) ───────────────────────────
    temperature: float | None = None   # °C
    humidity:    int   | None = None   # % RH
    # ── EF04 unknown pairs (diagnostic / reverse-engineering) ───────────
    ef04_pair0:  int   | None = None   # purpose unknown
    ef04_pair2:  int   | None = None   # purpose unknown
    ef04_pair3:  int   | None = None   # purpose unknown
    # ── Connection state ────────────────────────────────────────────────
    connected:   bool  = False    # True = BLE link active right now
    ever_seen:   bool  = False    # True = received at least one valid EF02

    @property
    def pm25(self) -> float:
        return round(self.pm25_raw / 10, 1)

    @property
    def timer_hours(self) -> int:
        return self.timer_val if self.timer_on else 0

    def parse_ef02(self, data: bytes) -> bool:
        if len(data) != 17 or data[0] != 0xAA or data[-1] != 0xEE:
            return False
        p = data[4:-1]
        expected = (p[0]+p[1]+p[2]+p[4]+p[6]+p[10]+0xC0) & 0xFF
        if expected != p[11]:
            _LOGGER.warning("EF02 checksum mismatch: expected 0x%02x got 0x%02x",
                            expected, p[11])
            return False

        old = (self.power, self.uvc, self.night, self.auto,
               self.timer_on, self.timer_val, self.speed, self.pm25_raw)

        flags          = p[2]
        self.power     = bool(flags & FLAG_POWER)
        self.uvc       = bool(flags & FLAG_UVC)
        self.night     = bool(flags & FLAG_NIGHT)
        self.auto      = bool(flags & FLAG_AUTO)
        self.timer_on  = bool(flags & FLAG_TIMER)
        self.speed     = p[0]
        self.timer_val = p[1]
        self.pm25_raw  = p[4]
        self.ever_seen = True

        new = (self.power, self.uvc, self.night, self.auto,
               self.timer_on, self.timer_val, self.speed, self.pm25_raw)
        return old != new

    def parse_ef04(self, data: bytes) -> bool:
        if len(data) < 4 or len(data) % 2 != 0:
            return False
        pairs = [int.from_bytes(data[i:i+2], "big") for i in range(0, len(data), 2)]
        old_temp, old_hum = self.temperature, self.humidity
        old_p0, old_p2, old_p3 = self.ef04_pair0, self.ef04_pair2, self.ef04_pair3

        if len(pairs) >= 2 and pairs[1] != 0xFFFF:
            self.temperature = round(pairs[1] / 10, 1)
        if len(pairs) >= 5 and pairs[4] != 0xFFFF and pairs[4] <= 100:
            self.humidity = pairs[4]

        # Capture unknown pairs for diagnostic purposes
        if len(pairs) >= 1 and pairs[0] != 0xFFFF:
            self.ef04_pair0 = pairs[0]
        if len(pairs) >= 3 and pairs[2] != 0xFFFF:
            self.ef04_pair2 = pairs[2]
        if len(pairs) >= 4 and pairs[3] != 0xFFFF:
            self.ef04_pair3 = pairs[3]

        return (self.temperature != old_temp or self.humidity != old_hum
                or self.ef04_pair0 != old_p0 or self.ef04_pair2 != old_p2
                or self.ef04_pair3 != old_p3)


class AC500BleClient:
    """
    BLE client using bleak_retry_connector.establish_connection()
    for reliable connection establishment (resolves HA debug warning).

    State persistence: entities remain available with last-known values
    during temporary BLE disconnects. Only unavailable before first connect.
    """

    def __init__(self, address: str) -> None:
        self._address    = address
        self._client: BleakClientWithServiceCache | None = None
        self._lock       = asyncio.Lock()
        self.state       = AC500State()
        self._callbacks: list[Callable] = []

    def register_callback(self, cb: Callable) -> None:
        self._callbacks.append(cb)

    def unregister_callback(self, cb: Callable) -> None:
        if cb in self._callbacks:
            self._callbacks.remove(cb)

    async def connect(self) -> bool:
        """Connect using establish_connection() for reliable BLE setup."""
        try:
            self._client = await establish_connection(
                client_class=BleakClientWithServiceCache,
                device=self._address,
                name=f"AC500({self._address})",
                disconnected_callback=self._on_disconnected,
                max_attempts=3,
            )
            await self._client.start_notify(UUID_EF02, self._notify_ef02)
            await self._client.start_notify(UUID_EF04, self._notify_ef04)
            self.state.connected = True
            _LOGGER.info("AC500 connected via bleak_retry_connector")
            self._notify_ha()
            return True
        except (BleakError, Exception) as err:
            _LOGGER.error("AC500 connect failed: %s", err)
            self.state.connected = False
            self._notify_ha()
            return False

    async def disconnect(self) -> None:
        if self._client:
            try:
                await self._client.disconnect()
            except BleakError:
                pass
            self._client = None
        self.state.connected = False
        self._notify_ha()

    def _on_disconnected(self, client: BleakClient) -> None:
        """Called by bleak when connection drops unexpectedly."""
        _LOGGER.debug("AC500 BLE disconnected (callback)")
        self.state.connected = False
        self._notify_ha()

    @property
    def is_connected(self) -> bool:
        return bool(self._client and self._client.is_connected)

    async def send_command(self, command_key: str) -> bool:
        hex_cmd = COMMANDS.get(command_key)
        if not hex_cmd:
            _LOGGER.error("Unknown command: %s", command_key)
            return False
        async with self._lock:
            if not self.is_connected:
                _LOGGER.warning("Not connected, cannot send %s", command_key)
                return False
            try:
                await self._client.write_gatt_char(
                    UUID_WRITE, bytearray.fromhex(hex_cmd)
                )
                _LOGGER.debug("Sent %s (%s)", command_key, hex_cmd)
                return True
            except BleakError as err:
                _LOGGER.error("Write failed for %s: %s", command_key, err)
                self.state.connected = False
                self._notify_ha()
                return False

    def _notify_ef02(self, _sender, raw: bytearray) -> None:
        if self.state.parse_ef02(bytes(raw)):
            self._notify_ha()

    def _notify_ef04(self, _sender, raw: bytearray) -> None:
        data = bytes(raw)
        if len(data) > 2 and self.state.parse_ef04(data):
            self._notify_ha()

    def _notify_ha(self) -> None:
        for cb in self._callbacks:
            try:
                cb()
            except Exception as err:
                _LOGGER.error("Callback error: %s", err)
