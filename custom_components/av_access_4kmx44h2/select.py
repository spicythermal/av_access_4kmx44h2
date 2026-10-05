"""Input-select entities, one per matrix output."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, INPUT_NAMES, NUM_PORTS


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    client = data["client"]

    entities = [
        MatrixOutputInputSelect(coordinator, client, entry, output)
        for output in range(1, NUM_PORTS + 1)
    ]
    async_add_entities(entities)


class MatrixOutputInputSelect(CoordinatorEntity, SelectEntity):
    """Which HDMI input is routed to one HDMI output."""

    _attr_has_entity_name = True
    _attr_options = INPUT_NAMES

    def __init__(self, coordinator, client, entry: ConfigEntry, output: int) -> None:
        super().__init__(coordinator)
        self._client = client
        self._output = output
        self._attr_unique_id = f"{entry.entry_id}_output{output}_input_select"
        self._attr_name = f"Output {output} Input"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"AV Access Matrix ({entry.data['host']})",
            manufacturer="AV Access",
            model="4KMX44-H2",
        )

    @property
    def current_option(self) -> str | None:
        routing = self.coordinator.data.get("routing", {})
        input_num = routing.get(self._output)
        if input_num is None:
            return None
        return INPUT_NAMES[input_num - 1]

    async def async_select_option(self, option: str) -> None:
        input_num = INPUT_NAMES.index(option) + 1
        await self._client.async_set_input(self._output, input_num)
        await self.coordinator.async_request_refresh()
