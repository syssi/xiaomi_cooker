"""Xiaomi MiIO Cooker sensor platform."""

from enum import Enum
import logging

from homeassistant.components.sensor import ENTITY_ID_FORMAT
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity
from homeassistant.util import slugify

_LOGGER = logging.getLogger(__name__)

COOKER_DOMAIN = "xiaomi_miio_cooker"
DATA_KEY = "xiaomi_miio_cooker_data"
DATA_TEMPERATURE_HISTORY = "temperature_history"
DATA_STATE = "state"


SENSOR_TYPES = {
    "mode": ["Mode", None, "mode", None, "mdi:bowl"],
    "menu": ["Menu", None, "menu", None, "mdi:menu"],
    "fault": ["Fault", None, "fault", None, "mdi:alert"],
    "remaining": ["Remaining", None, "remaining", "min", "mdi:timer"],
    "cooking_delayed": ["Cooking delayed", None, "cooking_delayed", "min", "mdi:timer"],
    "temperature": ["Temperature", None, "temperature", "°C", "mdi:thermometer"],
    "duration": ["Duration", None, "duration", "min", "mdi:timelapse"],
    "keep_warm": ["Keep warm", None, "keep_warm", None, "mdi:heat-wave"],
    "keep_warm_duration": ["Keep warm duration", None, "keep_warm_duration", None, "mdi:timer"],
    "rice": ["Rice Id", None, "rice", None, "mdi:rice"],
    "taste": ["Taste", None, "taste", None, "mdi:flash-outline"],
}

def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the Xiaomi Cooker sensors."""
    if discovery_info is None:
        return

    sensors = []

    for host, cooker in hass.data[COOKER_DOMAIN].items():
        for type in SENSOR_TYPES.values():
            sensors.append(XiaomiCookerSensor(cooker, host, type))

    add_devices(sensors)


class XiaomiCookerSensor(Entity):
    """Representation of a Xiaomi Cooker sensor."""

    def __init__(self, device, host, config) -> None:
        """Initialize sensor."""
        self._device = device
        self._host = host
        self._name = config[0]
        self._child = config[1]
        self._attr = config[2]
        self._unit_of_measurement = config[3]
        self._icon = config[4]
        self._state = None

        self.entity_id = ENTITY_ID_FORMAT.format(
            f"{COOKER_DOMAIN}_{slugify(self._name)}"
        )

    async def async_added_to_hass(self):
        """Register callbacks."""
        async_dispatcher_connect(
            self.hass, f"{COOKER_DOMAIN}_updated", self.async_update_callback
        )

    @property
    def name(self):
        """Return the name."""
        return self._name

    @callback
    def async_update_callback(self, host):
        """Update state."""
        if self._host is not host:
            return

        state = self.hass.data[DATA_KEY][host].get(DATA_STATE)
        temperature_history = self.hass.data[DATA_KEY][host].get(
            DATA_TEMPERATURE_HISTORY
        )

        if self._child is not None:
            state = getattr(state, self._child, None)
            # Unset state if child attribute isn't available anymore
            if state is None:
                self._state = None

        if state is not None:
            value = getattr(state, self._attr, None)
            if isinstance(value, Enum):
                self._state = value.name
            elif (
                self._attr == "temperature"
                # The legacy Cooker and CookerWY3 OperationMode enums are distinct
                # classes that share these member names, so match on the name rather
                # than importing one enum and comparing it against the other model's.
                and getattr(state.mode, "name", None)
                in ("Running", "AutoKeepWarm")
                and temperature_history
            ):
                self._state = temperature_history.temperatures.pop()
            else:
                self._state = value

        self.async_schedule_update_ha_state()

    @property
    def state(self):
        """Return the state."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement the state is expressed in."""
        return self._unit_of_measurement

    @property
    def icon(self) -> str | None:
        """Return the icon to use in the frontend, if any."""
        return self._icon

    @property
    def should_poll(self):
        """Return the polling state."""
        return False
