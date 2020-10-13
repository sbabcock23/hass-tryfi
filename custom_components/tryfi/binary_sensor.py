from homeassistant.helpers.entity import Entity
from homeassistant.const import STATE_OK, STATE_PROBLEM
from . import DOMAIN

def setup_platform(hass, config, add_entities, discovery_info=None, tryfi):
    """Set up the sensor platform."""
    ##add_entities([ExampleSensor()])
    helloentity = hass.data.get(DOMAIN)

    add_entities([HelloWorldBinarySensor(hass, "stevebinsensor")])

class HelloWorldBinarySensor(HelloWorld):
    def __init__(self, hass, name):
        print("starting initialization of binar sensor")
        self._hass = hass
        self._name = name
        self._state = STATE_OK
        self._device_class = 'window'
    @property
    def device_info(self):  
        identifier = "identifier123" 
        return {
                "identifiers": {(DOMAIN, identifier)},
                "name": self._name,
                "manufacturer": "steve manufact",
                "model": "binary model sensor",
            }
    @property
    def name(self):
        """Return the name of the ADT sensor."""
        return self._name
    @property
    def is_on(self):
        """Return True if the binary sensor is on."""
        status = self._state
        return status
    @property
    def unique_id(self):
        return f"steve_sensor_{self.name}"
    @property
    def device_class(self):
        """Return the class of the binary sensor."""
        return self._device_class