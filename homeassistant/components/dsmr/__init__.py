"""The dsmr component."""
from __future__ import annotations

from asyncio import CancelledError
from contextlib import suppress
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er

from .const import CONF_DSMR_VERSION, DATA_TASK, DOMAIN, PLATFORMS


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up DSMR from a config entry."""

    @callback
    def _async_migrate_entity_entry(
        entity_entry: er.RegistryEntry,
    ) -> dict[str, Any] | None:
        """Migrate DSMR entity entry."""
        return async_migrate_entity_entry(entry, entity_entry)

    await er.async_migrate_entries(hass, entry.entry_id, _async_migrate_entity_entry)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {}

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_update_options))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    task = hass.data[DOMAIN][entry.entry_id][DATA_TASK]

    # Cancel the reconnect task
    task.cancel()
    with suppress(CancelledError):
        await task

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update options."""
    await hass.config_entries.async_reload(entry.entry_id)


@callback
def async_migrate_entity_entry(
    config_entry: ConfigEntry, entity_entry: er.RegistryEntry
) -> dict[str, Any] | None:
    """Migrate DSMR entity entries.

    - Migrates unique ID for sensors based on entity description name to key.
    """

    # Replace names with keys in unique ID
    for old, new in (
        ("Power Consumption", "current_electricity_usage"),
        ("Power Production", "current_electricity_delivery"),
        ("Power Tariff", "electricity_active_tariff"),
        ("Energy Consumption (tarif 1)", "electricity_used_tariff_1"),
        ("Energy Consumption (tarif 2)", "electricity_used_tariff_2"),
        ("Energy Production (tarif 1)", "electricity_delivered_tariff_1"),
        ("Energy Production (tarif 2)", "electricity_delivered_tariff_2"),
        ("Power Consumption Phase L1", "instantaneous_active_power_l1_positive"),
        ("Power Consumption Phase L2", "instantaneous_active_power_l2_positive"),
        ("Power Consumption Phase L3", "instantaneous_active_power_l3_positive"),
        ("Power Production Phase L1", "instantaneous_active_power_l1_negative"),
        ("Power Production Phase L2", "instantaneous_active_power_l2_negative"),
        ("Power Production Phase L3", "instantaneous_active_power_l3_negative"),
        ("Short Power Failure Count", "short_power_failure_count"),
        ("Long Power Failure Count", "long_power_failure_count"),
        ("Voltage Sags Phase L1", "voltage_sag_l1_count"),
        ("Voltage Sags Phase L2", "voltage_sag_l2_count"),
        ("Voltage Sags Phase L3", "voltage_sag_l3_count"),
        ("Voltage Swells Phase L1", "voltage_swell_l1_count"),
        ("Voltage Swells Phase L2", "voltage_swell_l2_count"),
        ("Voltage Swells Phase L3", "voltage_swell_l3_count"),
        ("Voltage Phase L1", "instantaneous_voltage_l1"),
        ("Voltage Phase L2", "instantaneous_voltage_l2"),
        ("Voltage Phase L3", "instantaneous_voltage_l3"),
        ("Current Phase L1", "instantaneous_current_l1"),
        ("Current Phase L2", "instantaneous_current_l2"),
        ("Current Phase L3", "instantaneous_current_l3"),
        ("Max power per phase", "belgium_max_power_per_phase"),
        ("Max current per phase", "belgium_max_current_per_phase"),
        ("Energy Consumption (total)", "electricity_imported_total"),
        ("Energy Production (total)", "electricity_exported_total"),
    ):
        old = old.replace(" ", "_")
        if entity_entry.unique_id.endswith(old):
            return {"new_unique_id": entity_entry.unique_id.replace(old, new)}

    # Replace unique ID for gas sensors, based on DSMR version
    old = "Gas_Consumption"
    if entity_entry.unique_id.endswith(old):
        dsmr_version = config_entry.data[CONF_DSMR_VERSION]
        if dsmr_version in {"4", "5", "5L"}:
            return {
                "new_unique_id": entity_entry.unique_id.replace(
                    old, "hourly_gas_meter_reading"
                )
            }
        if dsmr_version == "5B":
            return {
                "new_unique_id": entity_entry.unique_id.replace(
                    old, "belgium_5min_gas_meter_reading"
                )
            }
        if dsmr_version == "2.2":
            return {
                "new_unique_id": entity_entry.unique_id.replace(
                    old, "gas_meter_reading"
                )
            }

    # No migration needed
    return None
