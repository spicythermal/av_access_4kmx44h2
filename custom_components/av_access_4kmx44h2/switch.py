"""Audio switch entities, one per matrix output.

The switch represents whether audio is flowing (ON = unmuted / audio
active, OFF = muted / audio cut) since that reads more naturally as a
switch than a literal "mute" toggle would.
"""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, NUM_PORTS


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    client = data["client"]

    entities = [
        MatrixOutputAudioSwitch(coordinator, client, entry, output)
        for output in range(1, NUM_PORTS + 1)
    ]
    async_add_entities(entities)


class MatrixOutputAudioSwitch(CoordinatorEntity, SwitchEntity):
    """Audio enable/disable (unmute/mute) for one S/PDIF output."""

    _attr_has_entity_name = True
    _attr_device_class = "switch"

    def __init__(self, coordinator, client, entry: ConfigEntry, output: int) -> None:
        super().__init__(coordinator)
        self._client = client
        self._output = output
        self._attr_unique_id = f"{entry.entry_id}_output{output}_audio"
        self._attr_name = f"Output {output} Audio"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"AV Access Matrix ({entry.data['host']})",
            manufacturer="AV Access",
            model="4KMX44-H2",
        )

    @property
    def is_on(self) -> bool | None:
        mute = self.coordinator.data.get("mute", {})
        muted = mute.get(self._output)
        if muted is None:
            return None
        return not muted  # switch ON means audio is flowing (not muted)

    async def async_turn_on(self, **kwargs) -> None:
        await self._client.async_set_mute(self._output, mute=False)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        await self._client.async_set_mute(self._output, mute=True)
        await self.coordinator.async_request_refresh()
