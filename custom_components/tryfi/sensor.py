"""Platform for sensor integration."""
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.icon import icon_for_battery_level
from homeassistant.const import STATE_OK, STATE_PROBLEM, DEVICE_CLASS_BATTERY, PERCENTAGE
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import dispatcher_send, async_dispatcher_connect
import logging
from . import TRYFI_DOMAIN, TRYFI_FLAG_UPDATED, TryFiCore, TryFiPet
LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the sensor platform."""
    ##add_entities([ExampleSensor()])
    #tryfi_service = hass.data.get(TRYFI_DOMAIN)
    tryfi = hass.data[TRYFI_DOMAIN]

    for pet in tryfi._pets:
        add_entities([TryFiBatterySensor(hass, tryfi, pet)])

class TryFiBatterySensor(Entity):
    """Representation of a Sensor."""
    def __init__(self, hass, tryfi, pet):
        self._hass = hass
        self._pet = pet
        self._tryfi = tryfi
        #super().__init__(hass,tryfi,pet)

    async def async_added_to_hass(self):
        """Register callbacks."""
        # register callback when data has been updated
        LOGGER.info(f"Notifying update for data for {self.name}")
        async_dispatcher_connect(self._hass, TRYFI_FLAG_UPDATED, self._update_callback)       
    @callback
    def _update_callback(self):
        """Call update method."""
        LOGGER.info(f"Scheduling update for data for {self.name}")
        self.async_schedule_update_ha_state(True)
    @property
    def should_poll(self):
        """Updates occur periodically from __init__ when changes detected"""
        return True
    
    def update(self):
        LOGGER.info(f"Updating data for {self.name}")
        self._tryfi = self._hass.data[TRYFI_DOMAIN]
        for pet in self._tryfi.pets:
            if self.pet.name == pet.name:
                self._pet = pet
                break
    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self.pet.name} Collar Battery Level"
    @property
    def unique_id(self):
        """Return the ID of this sensor."""
        return f"{self.pet.petId}-battery"
    @property
    def pet(self):
        return self._pet
    @property
    def device(self):
        return self.pet.device
    @property
    def device_id(self):
        return self.unique_id
    @property
    def device_class(self):
        """Return the device class of the sensor."""
        return DEVICE_CLASS_BATTERY
    @property
    def unit_of_measurement(self):
        """Return the unit_of_measurement of the device."""
        return PERCENTAGE
    @property
    def isCharging(self):
        return bool(self.pet.device.isCharging)
    @property
    def icon(self):
        """Return the icon for the battery."""
        return icon_for_battery_level(
            battery_level=self.batteryPercent, charging=self.isCharging
        )
    @property
    def batteryPercent(self):
        """Return the state of the sensor."""
        return self.pet.device.batteryPercent
    @property
    def state(self):
        return self.batteryPercent