import asyncio
import logging
from enum import Enum
from typing import Optional

from homeassistant.components.sensor import ENTITY_ID_FORMAT
from homeassistant.core import callback
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
    "temperature": ["Temperature", None, "temperature", "°C", None],
    "remaining": ["Remaining", None, "remaining", "min", "mdi:timer"],
    "duration": ["Duration", None, "duration", "min", "mdi:timelapse"],
    "favorite": ["Favorite", None, "favorite", None, "mdi:information-outline"],
    "state": ["State", "stage", "state", None, "mdi:playlist-check"],
    "rice_id": ["Rice Id", "stage", "rice_id", None, "mdi:rice"],
    "taste": ["Taste", "stage", "taste", None, "mdi:flash-outline"],
    "taste_phase": ["Taste Phase", "stage", "taste_phase", None, "mdi:flash-outline"],
    "stage_name": ["Stage Name", "stage", "name", None, "mdi:stairs"],
    "stage_description": [
        "Stage Description",
        "stage",
        "description",
        None,
        "mdi:stairs",
    ],
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
    def __init__(self, device, host, config):
        """Initialize sensor."""
        self._device = device
        self._host = host
        self._name = config[0]
        self._child = config[1]
        self._attr = config[2]
        self._unit_of_measurement = config[3]
        self._icon = config[4]
        self._state = None
        self._state_attributes = {}

        self.entity_id = ENTITY_ID_FORMAT.format(
            "{}_{}".format(COOKER_DOMAIN, slugify(self._name))
        )
        self._unique_id = COOKER_DOMAIN + self.entity_id

    @asyncio.coroutine
    def async_added_to_hass(self):
        """Register callbacks."""
        self.hass.helpers.dispatcher.async_dispatcher_connect(
            "{}_updated".format(COOKER_DOMAIN), self.async_update_callback
        )

    @property
    def name(self):
        """Return the name."""
        return self._name

    @callback
    def async_update_callback(self, host):
        """Update state."""
        from miio.cooker import OperationMode

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
                self._state_attributes[self._name] = None

        if state is not None:
            value = getattr(state, self._attr, None)
            if isinstance(value, Enum):
                self._state = value.name
            else:
                if (
                    self._attr == "temperature"
                    and state.mode
                    in [OperationMode.Running, OperationMode.AutoKeepWarm]
                    and temperature_history
                ):
                    self._state = temperature_history.temperatures.pop()
                    self._state_attributes[self._name] = temperature_history.temperatures.pop()
                else:
                    self._state = value
                    self._state_attributes[self._name] = value

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
    def icon(self) -> Optional[str]:
        """Return the icon to use in the frontend, if any."""
        return self._icon

    @property
    def should_poll(self):
        """Return the polling state."""
        return False

    @property
    def unique_id(self):
        """Return the unique id."""
        return self._unique_id

    @property
    def extra_state_attributes(self):
        """Return the state attributes of the sensor."""
        return self._state_attributes