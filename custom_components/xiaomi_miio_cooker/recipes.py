"""Recipe database for the Xiaomi rice cooker."""

import json
import logging
from pathlib import Path

_LOGGER = logging.getLogger(__name__)


RECIPE_FOLDER = Path(__file__).parent / "recipes"


class Recipes:
    """Named cooking profiles bundled for a given cooker model."""

    def __init__(
        self, model: str = "chunmi.cooker.wy3", folder: Path = RECIPE_FOLDER
    ) -> None:
        """Load the recipes bundled for the given model."""
        self.model = model
        self.folder = folder

        self._recipes = self.load_recipes()

    def load_recipes(self):
        """Load the recipe database."""
        recipes = json.loads((self.folder / f"{self.model}.recipes.json").read_text())

        # List of dicts with keys order, name, cookcode
        ordered_recipes = sorted(recipes, key=lambda k: k["order"])

        # Keep only the name and cookcode
        options = {
            recipe["name"].strip(): recipe["cookcode"] for recipe in ordered_recipes
        }

        return options

    def get_cookcode_by_name(self, name: str) -> str:
        """Get the cookcode by name."""
        return self._recipes.get(name)

    @property
    def recipes(self):
        """Return the recipes."""
        return self._recipes
