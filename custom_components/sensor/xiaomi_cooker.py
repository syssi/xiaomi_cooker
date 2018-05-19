import asyncio
import logging

from enum import Enum

# from homeassistant.components.xiaomi_cooker import (DOMAIN as COOKER_DOMAIN, DATA_KEY)
from homeassistant.components.sensor import ENTITY_ID_FORMAT
from homeassistant.core import callback
from homeassistant.helpers.entity import Entity
from homeassistant.util import slugify

_LOGGER = logging.getLogger(__name__)

COOKER_DOMAIN = 'xiaomi_cooker'
DATA_KEY = 'xiaomi_cooker_data'

SENSOR_TYPES = {
    'mode': ['Mode', 'mode', None],
    'menu': ['Menu', 'menu', None],
    'temperature': ['Temperature', 'temperature', '°C'],
    'remaining': ['Remaining', 'remaining', 'min'],
    'duration': ['Duration', 'duration', 'min'],
    'favorite': ['Favorite', 'favorite', None],
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

    def __init__(self, device, host, type):
        """Initialize sensor."""
        self._device = device
        self._host = host
        self._name = type[0]
        self._attr = type[1]
        self._unit_of_measurement = type[2]
        self._state = None

        self.entity_id = ENTITY_ID_FORMAT.format('{}_{}'.format(COOKER_DOMAIN, slugify(self._name)))

    @asyncio.coroutine
    def async_added_to_hass(self):
        """Register callbacks."""
        self.hass.helpers.dispatcher.async_dispatcher_connect('xiaomi_cooker_updated', self.async_update_callback)

    @property
    def name(self):
        """Return the name."""
        return self._name

    @callback
    def async_update_callback(self, host):
        """Update state."""
        if self._host is not host:
            return

        state = self.hass.data[DATA_KEY][host]

        if state is not None:
            value = getattr(state, self._attr, None)
            if isinstance(value, Enum):
                self._state = value.name
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
    def should_poll(self):
        """Return the polling state."""
        return False
