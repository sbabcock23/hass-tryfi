import logging

from homeassistant.components.light import LightEntity, ColorMode
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)
import math

from .const import DOMAIN

LOGGER = logging.getLogger(__name__)

def hex_to_rgb(hex_color):
    """
    Convert a hex representation of a color to an RGB tuple.

    Parameters:
    - hex_color (str): Hexadecimal representation of the color (e.g., "#RRGGBB" or "RRGGBB").

    Returns:
    - tuple: RGB tuple (red, green, blue).
    """
    # Remove the "#" if present
    hex_color = hex_color.lstrip('#')

    # Convert the hex values to integers
    rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    return rgb



def calculate_distance(color1, color2):
    """
    Calculate Euclidean distance between two RGB colors.

    Parameters:
    - color1 (Tuple[int, int, int]): RGB values of the first color.
    - color2 (Tuple[int, int, int]): RGB values of the second color.

    Returns:
    - float: The Euclidean distance between the two RGB colors.
    """
    return math.sqrt(sum((c1 - c2) ** 2 for c1, c2 in zip(color1, color2)))

def find_closest_color_code(target_color , color_list):
    """
    Find the RGB color closest to the target color in a list.

    Parameters:
    - target_color (Tuple[int, int, int]): RGB values of the target color.
    - color_list (Dict[Int: Tuple[int, int, int]]): Map of RGB colors to compare, where the key is the color code used by the device

    Returns:
    - int: The color code for this device closest to the target color
    """
    min_distance = float('inf')
    closest_color = None  # type: Tuple[int, int, int]
    # default to white, which is 8
    closest_color_code = 8 # type: int

    for code, color in color_list.items():
        distance = calculate_distance(target_color, color)
        if distance < min_distance:
            min_distance = distance
            closest_color_code = code

    return closest_color_code



async def async_setup_entry(hass, config_entry, async_add_devices):
    """Add sensors for passed config_entry in HA."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    tryfi = coordinator.data

    new_devices = []
    for pet in tryfi.pets:
        new_devices.append(TryFiPetLight(hass, pet, coordinator))
    if new_devices:
        async_add_devices(new_devices)


class TryFiPetLight(CoordinatorEntity, LightEntity):
    def __init__(self, hass, pet, coordinator):
        self._petId = pet.petId
        self._hass = hass

        self._colorMap = {ledColor.ledColorCode: hex_to_rgb(ledColor.hexCode) for ledColor in pet.device.availableLedColors}

        super().__init__(coordinator)

    @property
    def name(self):
        return f"{self.pet.name} - Collar Light"

    @property
    def petId(self):
        return self._petId

    @property
    def pet(self):
        return self.coordinator.data.getPet(self.petId)

    @property
    def tryfi(self):
        return self.coordinator.data

    @property
    def unique_id(self):
        return f"{self.pet.petId}-light"

    @property
    def device_id(self):
        return self.unique_id

    @property
    def is_on(self):
        return bool(self.pet.device.ledOn)

    @property
    def supported_color_modes(self):
       return [ColorMode.RGB]

    @property
    def color_mode(self):
       return ColorMode.RGB

    @property
    def rgb_color(self):
        return hex_to_rgb(self.pet.device.ledColorHex)

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self.pet.petId)},
            "name": self.pet.name,
            "manufacturer": "TryFi",
            "model": self.pet.breed,
            "sw_version": self.pet.device.buildId,
        }

    # Fix later, request update
    def turn_on(self, **kwargs):
        self.pet.turnOnOffLed(self.tryfi.session, True)

        if "rgb_color" in kwargs:
            # This is set when the color is changed
            # if the brightness(which is a no-op) is changed, for example, this is not set
            requested_color = kwargs["rgb_color"]
            closest_color_code = find_closest_color_code(requested_color, self._colorMap)

            self.pet.setLedColorCode(self.tryfi.session, closest_color_code)
            self.lastKnownColor = self._colorMap[closest_color_code]

    def turn_off(self, **kwargs):
        self.pet.turnOnOffLed(self.tryfi.session, False)
