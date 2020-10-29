from collections import defaultdict
import asyncio
from datetime import timedelta
from functools import partial
import logging

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.helpers import discovery
from homeassistant.const import (
    CONF_NAME,
    CONF_HOST,
    CONF_TOKEN,
    CONF_SCAN_INTERVAL,
    ATTR_ENTITY_ID,
)
from homeassistant.exceptions import PlatformNotReady
from homeassistant.helpers.event import track_time_interval
from homeassistant.helpers.dispatcher import dispatcher_send
from homeassistant.util.dt import utcnow

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "Xiaomi Miio Cooker"
DOMAIN = "xiaomi_miio_cooker"
DATA_KEY = "xiaomi_miio_cooker"
DATA_TEMPERATURE_HISTORY = "temperature_history"
DATA_STATE = "state"

SCAN_INTERVAL = timedelta(seconds=30)

CONF_MODEL = "model"

MODEL_PRESSURE1 = "chunmi.cooker.press1"
MODEL_PRESSURE2 = "chunmi.cooker.press2"
MODEL_NORMAL1 = "chunmi.cooker.normal1"
MODEL_NORMAL2 = "chunmi.cooker.normal2"
MODEL_NORMAL3 = "chunmi.cooker.normal3"
MODEL_NORMAL4 = "chunmi.cooker.normal4"
MODEL_NORMAL5 = "chunmi.cooker.normal5"

SUPPORTED_MODELS = [
    MODEL_PRESSURE1,
    MODEL_PRESSURE2,
    MODEL_NORMAL1,
    MODEL_NORMAL2,
    MODEL_NORMAL3,
    MODEL_NORMAL4,
    MODEL_NORMAL5,
]

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_HOST): cv.string,
                vol.Required(CONF_TOKEN): vol.All(
                    cv.string, vol.Length(min=32, max=32)
                ),
                vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
                vol.Optional(CONF_MODEL): vol.In(SUPPORTED_MODELS),
                vol.Optional(CONF_SCAN_INTERVAL, default=SCAN_INTERVAL): cv.time_period,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

ATTR_MODEL = "model"
ATTR_PROFILE = "profile"

SUCCESS = ["ok"]

SERVICE_SCHEMA = vol.Schema(
    {
        #    vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
    }
)

SERVICE_SCHEMA_START = SERVICE_SCHEMA.extend({vol.Required(ATTR_PROFILE): cv.string})

SERVICE_START = "start"
SERVICE_STOP = "stop"


# pylint: disable=unused-argument
def setup(hass, config):
    """Set up the platform from config."""
    from miio import Device, DeviceException

    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    host = config[DOMAIN][CONF_HOST]
    token = config[DOMAIN][CONF_TOKEN]
    name = config[DOMAIN][CONF_NAME]
    model = config[DOMAIN].get(CONF_MODEL)
    scan_interval = config[DOMAIN][CONF_SCAN_INTERVAL]

    if DATA_KEY not in hass.data:
        hass.data[DATA_KEY] = {}
        hass.data[DATA_KEY][host] = {}

    _LOGGER.info("Initializing with host %s (token %s...)", host, token[:5])

    if model is None:
        try:
            miio_device = Device(host, token)
            device_info = miio_device.info()
            model = device_info.model
            _LOGGER.info(
                "%s %s %s detected",
                model,
                device_info.firmware_version,
                device_info.hardware_version,
            )
        except DeviceException:
            raise PlatformNotReady

    if model in SUPPORTED_MODELS:
        from miio import Cooker

        cooker = Cooker(host, token)

        hass.data[DOMAIN][host] = cooker

        for component in ["sensor"]:
            discovery.load_platform(hass, component, DOMAIN, {}, config)

    else:
        _LOGGER.error(
            "Unsupported device found! Please create an issue at "
            "https://github.com/syssi/xiaomi_cooker/issues "
            "and provide the following data: %s",
            model,
        )
        return False

    def update(event_time):
        """Update device status."""
        from miio.cooker import OperationMode

        try:
            state = cooker.status()
            _LOGGER.debug("Got new state: %s", state)
            hass.data[DATA_KEY][host][DATA_STATE] = state

            if state.mode in [OperationMode.Running, OperationMode.AutoKeepWarm]:
                hass.data[DATA_KEY][host][
                    DATA_TEMPERATURE_HISTORY
                ] = cooker.get_temperature_history()

            dispatcher_send(hass, "{}_updated".format(DOMAIN), host)

        except DeviceException as ex:
            dispatcher_send(hass, "{}_unavailable".format(DOMAIN), host)
            _LOGGER.error("Got exception while fetching the state: %s", ex)

    update(utcnow())
    track_time_interval(hass, update, scan_interval)

    def start_service(call):
        """Service to start cooking."""
        profile = call.data.get(ATTR_PROFILE)
        cooker.start(profile)

    def stop_service(call):
        """Service to stop cooking."""
        cooker.stop()

    hass.services.register(
        DOMAIN, SERVICE_START, start_service, schema=SERVICE_SCHEMA_START
    )

    hass.services.register(DOMAIN, SERVICE_STOP, stop_service, schema=SERVICE_SCHEMA)

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


#    async def _try_command(self, mask_error, func, *args, **kwargs):
#        """Call a device command handling error messages."""
#        from miio import DeviceException
#        try:
#            result = await
#            self.hass.async_add_job(
#                partial(func, *args, **kwargs))
#
#            _LOGGER.info("Response received from miio device: %s", result)
#
#            return result == SUCCESS
#        except DeviceException as exc:
#            _LOGGER.error(mask_error, exc)
#            return False
