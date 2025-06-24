"""Config flow for TryFi integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import (
    CONF_POLLING_RATE,
    DEFAULT_POLLING_RATE,
    DOMAIN,
)
from pytryfi import PyTryFi

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_POLLING_RATE, default=DEFAULT_POLLING_RATE): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=3600)
        ),
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    username = data[CONF_USERNAME]
    password = data[CONF_PASSWORD]
    
    try:
        # Test the connection
        tryfi = await hass.async_add_executor_job(PyTryFi, username, password)
        
        # Verify we can authenticate
        if not hasattr(tryfi, "currentUser") or tryfi.currentUser is None:
            raise CannotConnect("Failed to authenticate")
            
    except Exception as err:
        _LOGGER.error("Failed to connect to TryFi: %s", err)
        raise CannotConnect from err
    
    # Return info that you want to store in the config entry
    return {"title": username}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for TryFi."""
    
    VERSION = 1
    
    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> OptionsFlowHandler:
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)
    
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["title"], data=user_input)
        
        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle TryFi options."""
    
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry
    
    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        return await self.async_step_user()
    
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle options flow."""
        errors: dict[str, str] = {}
        
        if user_input is not None:
            # If username/password changed, validate them
            username = user_input.get(CONF_USERNAME, self.config_entry.data.get(CONF_USERNAME))
            password = user_input.get(CONF_PASSWORD, self.config_entry.data.get(CONF_PASSWORD))
            
            # Only validate if credentials changed
            if (username != self.config_entry.data.get(CONF_USERNAME) or 
                password != self.config_entry.data.get(CONF_PASSWORD)):
                try:
                    await validate_input(self.hass, {
                        CONF_USERNAME: username,
                        CONF_PASSWORD: password,
                    })
                except CannotConnect:
                    errors["base"] = "cannot_connect"
                except Exception:  # pylint: disable=broad-except
                    _LOGGER.exception("Unexpected exception")
                    errors["base"] = "unknown"
            
            if not errors:
                # Update config entry with new data
                new_data = dict(self.config_entry.data)
                new_data.update(user_input)
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    data=new_data,
                )
                return self.async_create_entry(title="", data={})
        
        # Show form with current values as defaults
        data_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_USERNAME,
                    default=self.config_entry.data.get(CONF_USERNAME, ""),
                ): str,
                vol.Optional(
                    CONF_PASSWORD,
                    default=self.config_entry.data.get(CONF_PASSWORD, ""),
                ): str,
                vol.Optional(
                    CONF_POLLING_RATE,
                    default=self.config_entry.data.get(CONF_POLLING_RATE, DEFAULT_POLLING_RATE),
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=3600)),
            }
        )
        
        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "current_user": self.config_entry.data.get(CONF_USERNAME, ""),
            },
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""