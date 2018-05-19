from collections import defaultdict
import asyncio
from functools import partial
import logging

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.helpers import discovery
from homeassistant.const import (CONF_NAME, CONF_HOST, CONF_TOKEN,
                                 ATTR_ENTITY_ID, )
from homeassistant.exceptions import PlatformNotReady

_LOGGER = logging.getLogger(__name__)

DOMAIN = DATA_KEY = 'xiaomi_cooker'

CONF_MODEL = 'model'

SUPPORTED_MODELS = ['chunmi.cooker.normal2',
                    'chunmi.cooker.normal5']

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_TOKEN): vol.All(cv.string,
                                          vol.Length(min=32, max=32)),
        vol.Optional(CONF_MODEL): vol.In(SUPPORTED_MODELS),
    })
}, extra=vol.ALLOW_EXTRA)

REQUIREMENTS = ['python-miio>=0.3.7']

ATTR_MODEL = 'model'
ATTR_PROFILE = 'profile'

SUCCESS = ['ok']

SERVICE_SCHEMA = vol.Schema({
    vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
})

SERVICE_SCHEMA_START = SERVICE_SCHEMA.extend({
    vol.Required(ATTR_PROFILE): cv.string,
})

SERVICE_START = 'start'
SERVICE_STOP = 'stop'

SERVICE_TO_METHOD = {
    SERVICE_START: {'method': 'async_start', 'schema': SERVICE_SCHEMA_START},
    SERVICE_STOP: {'method': 'async_stop'},
}


# pylint: disable=unused-argument
def setup(hass, config):
    """Set up the platform from config."""
    from miio import Device, DeviceException
    if DATA_KEY not in hass.data:
        hass.data[DATA_KEY] = {}

    if DOMAIN in config:
        host = config[DOMAIN][CONF_HOST]
        token = config[DOMAIN][CONF_TOKEN]
        model = config[DOMAIN].get(CONF_MODEL)

    _LOGGER.info("Initializing with host %s (token %s...)", host, token[:5])

    if model is None:
        try:
            miio_device = Device(host, token)
            device_info = miio_device.info()
            model = device_info.model
            _LOGGER.info("%s %s %s detected",
                         model,
                         device_info.firmware_version,
                         device_info.hardware_version)
        except DeviceException:
            raise PlatformNotReady

    if model in SUPPORTED_MODELS:
        from miio import Cooker
        cooker = Cooker(host, token)

        hass.data[DATA_KEY][host] = cooker

#        for component in ['sensor', 'switch']:
#            discovery.load_platform(hass, component, DOMAIN, {}, config)

    else:
        _LOGGER.error(
            'Unsupported device found! Please create an issue at '
            'https://github.com/syssi/xiaomi_cooker/issues '
            'and provide the following data: %s', model)
        return False

    return True


class XiaomiMiioDevice(Entity):
    """Representation of a Xiaomi MiIO device."""

    def __init__(self, device, name):
        """Initialize the entity."""
        self._device = device
        self._name = name

        self._available = None
        self._state = None
        self._state_attrs = {}

    @property
    def should_poll(self):
        """Poll the miio device."""
        return True

    @property
    def name(self):
        """Return the name of this entity, if any."""
        return self._name

    @property
    def available(self):
        """Return true when state is known."""
        return self._available

    @property
    def state(self):
        """Return the state of the device."""
        return self._state

    @property
    def device_state_attributes(self):
        """Return the state attributes of the device."""
        return self._state_attrs

    async def _try_command(self, mask_error, func, *args, **kwargs):
        """Call a device command handling error messages."""
        from miio import DeviceException
        try:
            result = await self.hass.async_add_job(
                partial(func, *args, **kwargs))

            _LOGGER.info("Response received from miio device: %s", result)

            return result == SUCCESS
        except DeviceException as exc:
            _LOGGER.error(mask_error, exc)
            return False
