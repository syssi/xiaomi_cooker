"""Xiaomi MiIO Cooker integration."""

from datetime import timedelta
import json
import logging
from pathlib import Path
from typing import Any

from homeassistant.const import CONF_HOST, CONF_NAME, CONF_SCAN_INTERVAL, CONF_TOKEN
from homeassistant.exceptions import PlatformNotReady
from homeassistant.helpers import discovery
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.dispatcher import dispatcher_send
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import track_time_interval
from homeassistant.util.dt import utcnow
from miio import Cooker, CookerWY3, Device, DeviceException
from miio.integrations.chunmi.cooker.cooker_wy3 import OperationMode
from miio.miot_models import DeviceModel
import voluptuous as vol

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "Xiaomi Miio Cooker"
DOMAIN = "xiaomi_miio_cooker"
DATA_KEY = "xiaomi_miio_cooker_data"
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
MODEL_WY3 = "chunmi.cooker.wy3"

SUPPORTED_MODELS = [
    MODEL_PRESSURE1,
    MODEL_PRESSURE2,
    MODEL_NORMAL1,
    MODEL_NORMAL2,
    MODEL_NORMAL3,
    MODEL_NORMAL4,
    MODEL_NORMAL5,
    MODEL_WY3,
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
ATTR_DURATION = "duration"
ATTR_SCHEDULE = "schedule"
ATTR_AUTO_KEEP_WARM = "auto_keep_warm"
ATTR_TASTE = "taste"

SUCCESS = ["ok"]

SERVICE_SCHEMA = vol.Schema(
    {
        #    vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
    }
)

SERVICE_SCHEMA_START = SERVICE_SCHEMA.extend(
    {
        vol.Required(ATTR_PROFILE): cv.string,
        # vol.Optional(ATTR_DURATION): cv.positive_int,
        vol.Optional(ATTR_DURATION): vol.Any(cv.positive_int, cv.time_period_dict),
        # vol.Optional(ATTR_SCHEDULE): cv.positive_int,
        vol.Optional(ATTR_SCHEDULE): vol.Any(cv.positive_int, cv.datetime),
        vol.Optional(ATTR_AUTO_KEEP_WARM): cv.boolean,
        vol.Optional(ATTR_TASTE): cv.positive_int,
    }
)

SERVICE_START = "start"
SERVICE_STOP = "stop"


# pylint: disable=unused-argument
def setup(hass, config):
    """Set up the platform from config."""
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    host = config[DOMAIN][CONF_HOST]
    token = config[DOMAIN][CONF_TOKEN]
    # name = config[DOMAIN][CONF_NAME]
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
            raise PlatformNotReady from None

    if model in SUPPORTED_MODELS:
        if model == MODEL_WY3:

            def get_mapping_from_file(file):
                fullmap = json.loads(file.read_text())

                def get_iid(element):
                    return {element["type"][:1] + "iid": element["iid"]}

                data = {}

                for service in fullmap.values():
                    siid = get_iid(service)
                    properties = service["properties"]
                    actions = service["actions"]

                    pa = [*properties.values(), *actions.values()]

                    for propact in pa:
                        data[propact["name"]] = {**siid, **get_iid(propact)}

                return data

            mapping_file = (
                Path(__file__).parent / f"miot_specifications/mappings/{model}.json"
            )
            mapping = get_mapping_from_file(mapping_file)

            cooker = CookerWY3(
                ip=host,
                token=token,
                model=model,
                mapping=mapping,
            )

            specifications_file = (
                Path(__file__).parent
                / f"miot_specifications/specifications/{model}.json"
            )
            device_model = DeviceModel.model_validate_json(
                specifications_file.read_text()
            )
            cooker.initialize_model(device_model)
        else:
            cooker = Cooker(host, token)

        hass.data[DOMAIN][host] = cooker

        for component in ["sensor", "select"]:
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

        try:
            state = cooker.status()
            _LOGGER.debug("Got new state: %s", state)
            hass.data[DATA_KEY][host][DATA_STATE] = state

            if state.mode in [OperationMode.Running, OperationMode.AutoKeepWarm]:
                hass.data[DATA_KEY][host][DATA_TEMPERATURE_HISTORY] = (
                    cooker.get_temperature_history()
                )

            dispatcher_send(hass, f"{DOMAIN}_updated", host)

        except DeviceException as ex:
            dispatcher_send(hass, f"{DOMAIN}_unavailable", host)
            _LOGGER.info("Got exception while fetching the state: %s", ex)

    update(utcnow())
    track_time_interval(hass, update, scan_interval)

    def start_service(call):
        """Service to start cooking."""

        profile = call.data.get(ATTR_PROFILE)
        duration = call.data.get(ATTR_DURATION)
        schedule = call.data.get(ATTR_SCHEDULE)
        auto_keep_warm = call.data.get(ATTR_AUTO_KEEP_WARM)
        taste = call.data.get(ATTR_TASTE)

        if model == MODEL_WY3:
            cooker.start(profile, duration, schedule, auto_keep_warm, taste)
        else:
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

    def __init__(self, device, name) -> None:
        """Initialize the entity."""
        self._device = device
        self._name = name

        self._available = None
        self._state = None
        self._state_attrs: dict[str, Any] = {}

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
    def extra_state_attributes(self):
        """Return the extra state attributes of the device."""
        return self._state_attrs


#    async def _try_command(self, mask_error, func, *args, **kwargs):
#        """Call a device command handling error messages."""
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
