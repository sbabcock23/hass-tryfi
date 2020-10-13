"""Platform for sensor integration."""
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.icon import icon_for_battery_level
from homeassistant.const import STATE_OK, STATE_PROBLEM, DEVICE_CLASS_BATTERY, PERCENTAGE
from . import TRYFI_DOMAIN, TryFiCore, TryFiPet

def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the sensor platform."""
    ##add_entities([ExampleSensor()])
    #tryfi_service = hass.data.get(TRYFI_DOMAIN)
    tryfi = hass.data[TRYFI_DOMAIN]

    for pet in tryfi._pets:
        print(pet)
        device = pet._device
        add_entities([TryFiBatterySensor(device)])

class TryFiBatterySensor(TryFiPet):
    """Representation of a Sensor."""
    def __init__(self, device):
        self._device = device
        print (device)
        print (self.device)
    @property
    def device(self):
        return self._device
    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self.device.deviceId} Battery Level"
    @property
    def unique_id(self):
        """Return the ID of this sensor."""
        return f"battery_{self.device.deviceId}"
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
        return bool(self.device.isCharging)
    @property
    def icon(self):
        """Return the icon for the battery."""
        return icon_for_battery_level(
            battery_level=self.batteryPercent, charging=self.isCharging
        )
    @property
    def batteryPercent(self):
        """Return the state of the sensor."""
        return self.device.batteryPercent
    @property
    def state(self):
        return self.batteryPercent