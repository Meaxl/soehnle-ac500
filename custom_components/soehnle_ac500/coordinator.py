"""DataUpdateCoordinator – Verbindungsschleife und Wiederverbindung für den AC500."""
from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable

from homeassistant.components.bluetooth import (
    BluetoothChange,
    BluetoothScanningMode,
    async_register_callback as bt_async_register_callback,
)
from homeassistant.components.bluetooth.match import ADDRESS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .ble_client import AC500BleClient, AC500State

_LOGGER = logging.getLogger(__name__)

RECONNECT_INTERVAL        = 5    # Sekunden zwischen Wiederverbindungsversuchen
KEEPALIVE_TIMEOUT         = 15   # Sekunden ohne Notify bevor Neuverbindung erzwungen wird
CHECK_NIGHT_MODE_INTERVAL    = 300  # Minimalabstand zwischen Nachtmodus-Reconnect-Checks (Advertisement-Pfad)
NIGHT_MODE_FALLBACK_INTERVAL = 60   # Fallback-Poll-Interval wenn keine BLE-Advertisements eingehen


class AC500Coordinator(DataUpdateCoordinator):
    """
    Verwaltet den BLE-Lebenszyklus.
    - Verbindet bei Verbindungsabbruch automatisch neu
    - Benachrichtigt alle Entitäten bei jeder Zustandsänderung
    """

    def __init__(self, hass: HomeAssistant, client: AC500BleClient,
                 name: str) -> None:
        super().__init__(hass, _LOGGER, name=name)
        self._client                      = client
        self._last_notify_ts              = time.monotonic()
        self._running                     = False
        self._task: asyncio.Task | None   = None
        self._paused_for_night_mode       = False
        self._bt_cancel_callback: Callable[[], None] | None = None
        self._checking_night_mode         = False
        self._last_night_mode_check_ts    = 0.0

    @property
    def state(self) -> AC500State:
        return self._client.state

    @property
    def client(self) -> AC500BleClient:
        return self._client

    async def async_start(self) -> None:
        self._running = True
        self._client.register_callback(self._on_state_change)
        self._task = self.hass.async_create_background_task(
            self._connection_loop(), name="AC500 connection loop"
        )

    async def async_stop(self) -> None:
        self._running = False
        self._unregister_bt_wakeup_listener()
        if self._task:
            self._task.cancel()
        await self._client.disconnect()

    def _on_state_change(self) -> None:
        self._last_notify_ts = time.monotonic()
        # Nach HA-Neustart: Gerät meldet Nachtmodus per EF02, aber _paused_for_night_mode
        # ist False. Automatisch pausieren, damit der Reconnect-Loop das Gerät nicht weckt.
        if self._client.state.night and not self._paused_for_night_mode and not self._checking_night_mode:
            _LOGGER.debug("AC500 Nachtmodus per EF02 erkannt ohne Pause-Flag – automatisch pausieren")
            self.hass.async_create_task(self.pause_for_night_mode())
        self.async_set_updated_data(self._client.state)

    def _register_bt_wakeup_listener(self) -> None:
        """BLE-Advertisement-Callback für physische Wakeup-Erkennung registrieren."""
        if self._bt_cancel_callback is not None:
            return
        self._bt_cancel_callback = bt_async_register_callback(
            self.hass,
            self._on_bt_advertisement,
            {ADDRESS: self._client.address},
            BluetoothScanningMode.ACTIVE,
        )

    def _unregister_bt_wakeup_listener(self) -> None:
        """BLE-Advertisement-Callback wieder abmelden."""
        if self._bt_cancel_callback is not None:
            self._bt_cancel_callback()
            self._bt_cancel_callback = None

    def _on_bt_advertisement(self, service_info, change: BluetoothChange) -> None:
        """Wird aufgerufen, wenn das Gerät während der Nachtmodus-Pause advertised."""
        if not self._paused_for_night_mode or self._checking_night_mode:
            return
        now = time.monotonic()
        if now - self._last_night_mode_check_ts < CHECK_NIGHT_MODE_INTERVAL:
            return
        # Flag synchron setzen, bevor Task erstellt wird – verhindert Race bei
        # mehreren Advertisement-Callbacks vor dem ersten async-Switch.
        self._checking_night_mode = True
        self.hass.async_create_task(self._check_night_mode_ended())

    async def _check_night_mode_ended(self) -> None:
        """Kurzer Connect zur Prüfung ob der Nachtmodus physisch beendet wurde."""
        # _checking_night_mode wurde bereits synchron in _on_bt_advertisement gesetzt.
        if not self._paused_for_night_mode:
            self._checking_night_mode = False
            return
        self._last_night_mode_check_ts = time.monotonic()
        try:
            connected = await self._client.connect()
            if not connected:
                return

            # Callback erst nach connect() registrieren: connect() feuert bereits
            # _notify_ha() für state.connected – der nächste Callback enthält EF02-Daten.
            ef02_event = asyncio.Event()

            def _on_notify() -> None:
                ef02_event.set()

            self._client.register_callback(_on_notify)
            try:
                await asyncio.wait_for(ef02_event.wait(), timeout=3.0)
            except asyncio.TimeoutError:
                _LOGGER.warning("EF02 nicht innerhalb 3s empfangen – Nachtmodus-Status unklar")
            finally:
                self._client.unregister_callback(_on_notify)

            if not self._client.state.night:
                _LOGGER.debug("Nachtmodus physisch beendet – Coordinator resumed")
                self.resume_from_night_mode()
            else:
                # Gerät noch im Nachtmodus → sofort wieder trennen
                await self._client.disconnect()
        finally:
            self._checking_night_mode = False

    async def pause_for_night_mode(self) -> None:
        """BLE-Reconnect für Nachtmodus deaktivieren, Verbindung trennen und Wakeup-Listener starten."""
        self._paused_for_night_mode = True
        await self._client.disconnect()
        self._register_bt_wakeup_listener()
        self._last_night_mode_check_ts = time.monotonic()
        _LOGGER.debug("AC500 BLE-Verbindung für Nachtmodus getrennt")

    def resume_from_night_mode(self) -> None:
        """BLE-Reconnect nach Nachtmodus-Ende wieder erlauben und Listener stoppen."""
        self._unregister_bt_wakeup_listener()
        self._paused_for_night_mode = False
        _LOGGER.debug("AC500 Nachtmodus beendet – Reconnect wieder aktiv")

    async def _connection_loop(self) -> None:
        while self._running:
            if not self._client.is_connected:
                if self._paused_for_night_mode:
                    if not self._checking_night_mode:
                        now = time.monotonic()
                        if now - self._last_night_mode_check_ts >= NIGHT_MODE_FALLBACK_INTERVAL:
                            _LOGGER.debug(
                                "Nachtmodus-Fallback: keine Advertisements seit %ds – probe connect",
                                NIGHT_MODE_FALLBACK_INTERVAL,
                            )
                            self._checking_night_mode = True
                            self.hass.async_create_task(self._check_night_mode_ended())
                    await asyncio.sleep(2)
                    continue
                _LOGGER.info("AC500 attempting connection...")
                connected = await self._client.connect()
                if not connected:
                    await asyncio.sleep(RECONNECT_INTERVAL)
                    continue
                self._last_notify_ts = time.monotonic()

            await asyncio.sleep(2)

            # Keepalive watchdog
            elapsed = time.monotonic() - self._last_notify_ts
            if elapsed > KEEPALIVE_TIMEOUT:
                _LOGGER.warning(
                    "No notify for %ds – forcing reconnect", KEEPALIVE_TIMEOUT
                )
                await self._client.disconnect()
                await asyncio.sleep(RECONNECT_INTERVAL)
