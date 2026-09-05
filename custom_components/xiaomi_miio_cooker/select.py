"""Xiaomi MiIO Cooker recipe select platform."""

import logging

from homeassistant.components.select import SelectEntity
from miio.integrations.chunmi.cooker.cooker_wy3 import Wy3CookerProfile

from .recipes import Recipes

_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the Xiaomi Cooker sensors."""
    if discovery_info is None:
        return

    add_devices([RecipeSelector()])


class RecipeSelector(SelectEntity):
    """Representation of an input select."""

    def __init__(self) -> None:
        """Initialize the input select."""

        # super().__init__()
        self._name = "Xiaomi Cooker Recipe Selection"
        self._recipes = Recipes()
        self.update_recipes()
        self._attr_current_option = next(iter(self._attr_options))

        self.update_current_cookcode()
        self.update_recipe_attributes()

    def select_option(self, option: str) -> None:
        """Select a recipe by name."""
        self._attr_current_option = option

        self.update_current_cookcode()
        self.update_recipe_attributes()

    def update_recipes(self):
        """Update state."""
        self._attr_options = self._recipes.recipes

    def update_current_cookcode(self):
        """Return the cookcode of the selected recipe."""
        self._current_cookcode = self._recipes.get_cookcode_by_name(
            self._attr_current_option
        )

    def update_recipe_attributes(self):
        """Refresh the cached attributes of the selected recipe."""
        self._recipe_attributes = Wy3CookerProfile(
            self.current_cookcode
        ).get_recipe_attributes()

    @property
    def name(self):
        """Return the name of the input select."""
        return self._name

    @property
    def options(self):
        """Return the list of options for the input select."""
        return list(self._attr_options.keys())

    @property
    def current_cookcode(self):
        """Return the cookcode of the selected recipe."""
        return self._current_cookcode

    @property
    def recipe_attributes(self):
        """Return the recipe attributes."""
        return self._recipe_attributes

    @property
    def extra_state_attributes(self):
        """Return entity specific state attributes."""
        attributes = {
            "cookcode": self.current_cookcode,
            **self._recipe_attributes,
        }
        return attributes
