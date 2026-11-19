"""Config, discovery, re-authentication, reconfigure and options flows."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

# Core 2026.10 replaced voluptuous with probatio, and types every flow schema
# as probatio's. Same API, so the schemas below are written once; voluptuous
# is only reached on the older cores this still supports, where probatio does
# not exist.
try:
    import probatio as vol
except ImportError:
    import voluptuous as vol  # type: ignore[no-redef]

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)
from homeassistant.helpers.service_info.bluetooth import BluetoothServiceInfo

from .api import TryFiAuthError, TryFiError, async_check
from .const import (
    CONF_PASSWORD,
    CONF_POLLING_RATE,
    CONF_USERNAME,
    DEFAULT_POLLING_RATE,
    DOMAIN,
    MIN_POLLING_RATE,
    account_id,
)
from .coordinator import polling_rate

_LOGGER = logging.getLogger(__name__)

_POLLING = NumberSelector(
    NumberSelectorConfig(
        min=MIN_POLLING_RATE,
        max=3600,
        step=1,
        unit_of_measurement="s",
        mode=NumberSelectorMode.BOX,
    )
)
_PASSWORD = TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): TextSelector(
            TextSelectorConfig(type=TextSelectorType.EMAIL)
        ),
        vol.Required(CONF_PASSWORD): _PASSWORD,
        vol.Optional(CONF_POLLING_RATE, default=DEFAULT_POLLING_RATE): _POLLING,
    }
)
STEP_REAUTH_SCHEMA = vol.Schema({vol.Required(CONF_PASSWORD): _PASSWORD})
STEP_RECONFIGURE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): TextSelector(
            TextSelectorConfig(type=TextSelectorType.EMAIL)
        ),
        vol.Required(CONF_PASSWORD): _PASSWORD,
    }
)


class TryFiConfigFlow(ConfigFlow, domain=DOMAIN):
    """Sign in to TryFi.

    The entry's unique id is TryFi's own user id, read at sign-in, so it
    survives a change of login email and tells one account from another.
    """

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlowHandler:
        return OptionsFlowHandler()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            # One entry per account: a second polls TryFi for the same pets and
            # its entities collide with the first's unique ids. Entries made by
            # upstream have no unique id until they load here, so they are
            # matched on their email before signing in at all.
            email = account_id(user_input[CONF_USERNAME])
            for existing in self._async_current_entries(include_ignore=False):
                if account_id(existing.data.get(CONF_USERNAME, "")) == email:
                    return self.async_abort(reason="already_configured")
            user_id, errors = await self._sign_in(
                user_input[CONF_USERNAME], user_input[CONF_PASSWORD]
            )
            if user_id is not None:
                await self.async_set_unique_id(user_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input[CONF_USERNAME],
                    data={
                        CONF_USERNAME: user_input[CONF_USERNAME],
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                        CONF_POLLING_RATE: int(user_input[CONF_POLLING_RATE]),
                    },
                )
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                STEP_USER_SCHEMA, user_input
            ),
            errors=errors,
        )

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfo
    ) -> ConfigFlowResult:
        """A Fi collar heard by Home Assistant's Bluetooth.

        It says only that a collar is nearby, not whose account it is on, so
        it leads to the sign-in form; and once any account is set up, the
        collars it hears are already accounted for.
        """
        if self._async_current_entries(include_ignore=False):
            return self.async_abort(reason="already_configured")
        # One discovery at a time, however many collars are in range.
        await self.async_set_unique_id(f"{DOMAIN}_bluetooth")
        self._abort_if_unique_id_configured()
        self.context["title_placeholders"] = {"name": discovery_info.name}
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return await self.async_step_user()
        self._set_confirm_only()
        return self.async_show_form(step_id="bluetooth_confirm")

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            user_id, errors = await self._sign_in(
                entry.data[CONF_USERNAME], user_input[CONF_PASSWORD]
            )
            if user_id is not None:
                return self.async_update_reload_and_abort(
                    entry, data_updates={CONF_PASSWORD: user_input[CONF_PASSWORD]}
                )
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=STEP_REAUTH_SCHEMA,
            description_placeholders={"username": entry.data[CONF_USERNAME]},
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change the login email or password of the same TryFi account."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            user_id, errors = await self._sign_in(
                user_input[CONF_USERNAME], user_input[CONF_PASSWORD]
            )
            if user_id is not None:
                # A different account would leave every pet's entities behind.
                await self.async_set_unique_id(user_id)
                if entry.unique_id is not None:
                    self._abort_if_unique_id_mismatch(reason="wrong_account")
                return self.async_update_reload_and_abort(
                    entry,
                    unique_id=user_id,
                    title=user_input[CONF_USERNAME],
                    data_updates={
                        CONF_USERNAME: user_input[CONF_USERNAME],
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                    },
                )
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                STEP_RECONFIGURE_SCHEMA,
                user_input or {CONF_USERNAME: entry.data[CONF_USERNAME]},
            ),
            errors=errors,
        )

    async def _sign_in(
        self, username: str, password: str
    ) -> tuple[str | None, dict[str, str]]:
        """Sign in once to prove the credentials: TryFi's user id, or errors."""
        try:
            user_id = await async_check(self.hass, username, password)
        except TryFiAuthError:
            return None, {"base": "invalid_auth"}
        except TryFiError:
            return None, {"base": "cannot_connect"}
        except Exception:
            _LOGGER.exception("Unexpected error signing in to TryFi")
            return None, {"base": "unknown"}
        return user_id, {}


class OptionsFlowHandler(OptionsFlow):
    """Change how often TryFi is polled.

    Takes no config entry: core provides self.config_entry, and assigning it
    here, as upstream did, now fails (upstream sbabcock23/hass-tryfi#113).
    """

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            # Saving triggers the entry's update listener, which reloads it.
            return self.async_create_entry(
                data={CONF_POLLING_RATE: int(user_input[CONF_POLLING_RATE])}
            )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_POLLING_RATE, default=polling_rate(self.config_entry)
                    ): _POLLING,
                }
            ),
        )
