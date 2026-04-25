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
    UUID_WRITE, UUID_EF02, UUID_EF03, UUID_EF04,
    UUID_FFD1, UUID_FFD2, UUID_FFD3, UUID_FFD4, UUID_FFD5, UUID_FFF1,
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
    # ── Environmental sensors ────────────────────────────────────────────
    temperature: float | None = None   # °C – last valid temp from EF04 history
    # ── EF04 history buffer (diagnostic / reverse-engineering) ───────────
    # Structure: alternating (PM2.5_raw, temp×10) pairs per frame
    # even-indexed pairs = PM2.5 raw history, odd-indexed = temperature×10 history
    ef04_pair0:   int   | None = None   # PM2.5 raw history
    ef04_pair2:   int   | None = None   # PM2.5 raw history
    ef04_pair3:   int   | None = None   # temperature×10 history
    ef04_pair5:   int   | None = None   # temperature×10 history
    ef04_pair6:   int   | None = None   # PM2.5 raw history
    ef04_pair7:   int   | None = None   # temperature×10 history
    ef04_raw_hex: str   | None = None   # full raw payload for analysis
    # ── EF03 unknown characteristic ─────────────────────────────────────
    ef03_raw_hex: str   | None = None   # raw EF03 payload (purpose unknown)
    # ── d0ff service read-only chars (filter data candidates) ───────────
    ffd2_raw_hex: str   | None = None
    ffd3_raw_hex: str   | None = None
    ffd4_raw_hex: str   | None = None
    ffd5_raw_hex: str   | None = None
    fff1_raw_hex: str   | None = None
    # ── Filter lifetime data (from EF02 p[7:9] / p[9:11]) ──────────────
    filter_total_hours: int = 0   # big-endian uint16 at p[7:9], e.g. 4320
    filter_used_hours:  int = 0   # big-endian uint16 at p[9:11], e.g. 758
    # ── Connection state ────────────────────────────────────────────────
    connected:   bool  = False    # True = BLE link active right now
    ever_seen:   bool  = False    # True = received at least one valid EF02

    @property
    def pm25(self) -> float:
        return round(self.pm25_raw / 10, 1)

    @property
    def filter_pct_used(self) -> float | None:
        if self.filter_total_hours == 0:
            return None
        return round(self.filter_used_hours / self.filter_total_hours * 100, 1)

    @property
    def filter_remaining_hours(self) -> int | None:
        if self.filter_total_hours == 0:
            return None
        return max(0, self.filter_total_hours - self.filter_used_hours)

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
               self.timer_on, self.timer_val, self.speed, self.pm25_raw,
               self.filter_total_hours, self.filter_used_hours)

        flags          = p[2]
        self.power     = bool(flags & FLAG_POWER)
        self.uvc       = bool(flags & FLAG_UVC)
        self.night     = bool(flags & FLAG_NIGHT)
        self.auto      = bool(flags & FLAG_AUTO)
        self.timer_on  = bool(flags & FLAG_TIMER)
        self.speed     = p[0]
        self.timer_val = p[1]
        self.pm25_raw  = p[4]
        # p[7:9] = filter total lifetime (hours), p[9:11] = filter hours used
        self.filter_total_hours = int.from_bytes(p[7:9], "big")
        self.filter_used_hours  = int.from_bytes(p[9:11], "big")
        self.ever_seen = True

        new = (self.power, self.uvc, self.night, self.auto,
               self.timer_on, self.timer_val, self.speed, self.pm25_raw,
               self.filter_total_hours, self.filter_used_hours)
        return old != new

    def parse_ef04(self, data: bytes) -> bool:
        if len(data) < 4 or len(data) % 2 != 0:
            return False
        pairs = [int.from_bytes(data[i:i+2], "big") for i in range(0, len(data), 2)]
        old = (self.temperature,
               self.ef04_pair0, self.ef04_pair2, self.ef04_pair3,
               self.ef04_pair5, self.ef04_pair6, self.ef04_pair7,
               self.ef04_raw_hex)

        # EF04 is a history buffer of alternating (PM2.5_raw, temp×10) pairs.
        # Odd-indexed pairs = temperature×10. Iterate all to get the most recent
        # (last valid) temperature from this frame.
        for i in range(1, len(pairs), 2):
            if pairs[i] != 0xFFFF:
                self.temperature = round(pairs[i] / 10, 1)

        # Capture selected pairs as diagnostic history values
        _diag = {0: "ef04_pair0", 2: "ef04_pair2", 3: "ef04_pair3",
                 5: "ef04_pair5", 6: "ef04_pair6", 7: "ef04_pair7"}
        for idx, attr in _diag.items():
            if len(pairs) > idx and pairs[idx] != 0xFFFF:
                setattr(self, attr, pairs[idx])

        self.ef04_raw_hex = data.hex()

        new = (self.temperature,
               self.ef04_pair0, self.ef04_pair2, self.ef04_pair3,
               self.ef04_pair5, self.ef04_pair6, self.ef04_pair7,
               self.ef04_raw_hex)
        return old != new


class AC500BleClient:
    """
    BLE client using bleak_retry_connector.establish_connection()
    for reliable connection establishment (resolves HA debug warning).

    State persistence: entities remain available with last-known values
    during temporary BLE disconnects. Only unavailable before first connect.
    """

    def __init__(self, address: str) -> None:
        self._address      = address
        self._client: BleakClientWithServiceCache | None = None
        self._lock         = asyncio.Lock()
        self.state         = AC500State()
        self._callbacks: list[Callable] = []
        self._ffd1_probed  = False   # probe FFD1 only once per session

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
            try:
                await self._client.start_notify(UUID_EF03, self._notify_ef03)
                _LOGGER.debug("AC500 subscribed to EF03")
            except BleakError as err:
                _LOGGER.warning("AC500 EF03 not available: %s", err)

            # Read proprietary d0ff characteristics (filter data candidates)
            await self._read_d0ff_chars()

            # One-time: probe FFD1 with common query bytes to see if EF03 responds
            if not self._ffd1_probed:
                await self._probe_ffd1()

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

    async def _probe_ffd1(self) -> None:
        """Send query bytes to FFD1 once and watch for EF03 response."""
        self._ffd1_probed = True
        # Try common single-byte queries and the aa..ee frame format
        probes = [b"\x00", b"\x01", b"\xff",
                  bytes.fromhex("aa0306000000aee")]  # aa-frame style query
        for payload in probes:
            try:
                _LOGGER.info("FFD1 probe: %s", payload.hex())
                await self._client.write_gatt_char(
                    UUID_FFD1, bytearray(payload), response=False
                )
                await asyncio.sleep(0.3)   # brief pause for potential EF03 reply
            except BleakError as err:
                _LOGGER.warning("FFD1 probe %s failed: %s", payload.hex(), err)

    async def _read_d0ff_chars(self) -> None:
        """Read all readable d0ff service characteristics after connecting."""
        candidates = [
            ("ffd2", UUID_FFD2),
            ("ffd3", UUID_FFD3),
            ("ffd4", UUID_FFD4),
            ("ffd5", UUID_FFD5),
            ("fff1", UUID_FFF1),
        ]
        changed = False
        for name, uuid in candidates:
            try:
                data = bytes(await self._client.read_gatt_char(uuid))
                hex_str = data.hex()
                _LOGGER.info("AC500 %s (%d bytes): %s", name.upper(), len(data), hex_str)
                attr = f"{name}_raw_hex"
                if getattr(self.state, attr) != hex_str:
                    setattr(self.state, attr, hex_str)
                    changed = True
            except BleakError as err:
                _LOGGER.warning("AC500 read %s failed: %s", name.upper(), err)
        if changed:
            self._notify_ha()

    def _notify_ef02(self, _sender, raw: bytearray) -> None:
        data = bytes(raw)
        _LOGGER.info("EF02 raw (%d bytes): %s", len(data), data.hex())
        if self.state.parse_ef02(data):
            self._notify_ha()

    def _notify_ef03(self, _sender, raw: bytearray) -> None:
        hex_str = bytes(raw).hex()
        _LOGGER.info("EF03 notification: %s", hex_str)
        if self.state.ef03_raw_hex != hex_str:
            self.state.ef03_raw_hex = hex_str
            self._notify_ha()

    def _notify_ef04(self, _sender, raw: bytearray) -> None:
        data = bytes(raw)
        _LOGGER.info("EF04 raw (%d bytes): %s", len(data), data.hex())
        if len(data) > 2 and self.state.parse_ef04(data):
            self._notify_ha()

    def _notify_ha(self) -> None:
        for cb in self._callbacks:
            try:
                cb()
            except Exception as err:
                _LOGGER.error("Callback error: %s", err)
