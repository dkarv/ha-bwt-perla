"""Config flow for BWT Perla integration."""
import logging
from collections.abc import Mapping
from typing import Any

from bwt_api.api import BwtApi, BwtSilkApi, BwtSmartDosApi
from bwt_api.bwt import determine_bwt_model, BwtModel
from bwt_api.exception import ConnectException, WrongCodeException
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_CODE, CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

def _host_schema(
        host: str | None = None,
): return vol.Schema(
    {
        vol.Required(CONF_HOST, default=host): str,
    }
)

def _code_schema(
        code: str | None = None,
): return vol.Schema(
    {
        vol.Required(CONF_CODE, default=code): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from _bwt_schema with values provided by the user.
    """
    model = await determine_bwt_model(data[CONF_HOST])
    name = "BWT Perla"
    lib_logger = _LOGGER.getChild("bwt_api")
    match model:
        case BwtModel.PERLA_LOCAL_API:
            _LOGGER.debug("BWT Perla with local api detected")
            if CONF_CODE in data:
                async with BwtApi(data[CONF_HOST], data[CONF_CODE], lib_logger) as api:
                    data = await api.get_current_data()
                    suffix = "One" if data.columns == 1 else "Duplex"
                    name = f"BWT Perla {suffix}"
        case BwtModel.PERLA_SILK:
            _LOGGER.debug("BWT Perla with Silk API detected")
            async with BwtSilkApi(data[CONF_HOST], lib_logger) as api:
                await api.get_registers()
                name = "BWT Perla Silk"
        case BwtModel.SMART_DOS:
            _LOGGER.debug("BWT SmartDos detected")
            async with BwtSmartDosApi(data[CONF_HOST], lib_logger) as api:
                await api.get_gatt_0201()
                name = "BWT SmartDos"
        case _:
            _LOGGER.error("Unsupported BWT model: %s", model)
            raise ValueError(f"Unsupported BWT model: {model}")

    # Return info that you want to store in the config entry.
    return {"model": model, "title": name}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for BWT Perla."""

    VERSION = 3

    def _async_finish_reconfigure(self, data: dict[str, Any]) -> FlowResult:
        """Store the new data on the entry being reconfigured."""
        return self.async_update_reload_and_abort(
            self._get_reconfigure_entry(),
            data=data,
            reason="reconfiguration_successful",
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            # Outside the try block: the abort must not be swallowed below.
            self._async_abort_entries_match({CONF_HOST: user_input[CONF_HOST]})
            try:
                info = await validate_input(self.hass, user_input)
                match info["model"]:
                    case BwtModel.PERLA_LOCAL_API:
                        # Ask user for login code
                        self._host = user_input[CONF_HOST]
                        return await self.async_step_code()
                    case BwtModel.PERLA_SILK | BwtModel.SMART_DOS:
                        user_input["model"] = info["model"].name
                        return self.async_create_entry(title=info["title"], data=user_input)
                    case _:
                        errors["base"] = "unsupported_model"
            except ConnectException:
                _LOGGER.exception("Connection error setting up the Bwt Api")
                errors["base"] = "cannot_connect"
            except Exception as e:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception %s", e)
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=_host_schema(), errors=errors
        )


    async def async_step_code(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            user_input[CONF_HOST] = self._host
            try:
                info = await validate_input(self.hass, user_input)
                user_input["model"] = info["model"].name
                # If this flow was started as a reconfiguration, update the
                # existing entry instead of creating a new one.
                if self.source == "reconfigure":
                    return self._async_finish_reconfigure(user_input)
                return self.async_create_entry(title=info["title"], data=user_input)
            except ConnectException:
                _LOGGER.exception("Connection error setting up the Bwt Api")
                errors["base"] = "cannot_connect"
            except WrongCodeException:
                _LOGGER.exception("Wrong user code passed to bwt api")
                errors["base"] = "invalid_code_or_api_disabled"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        # Pre-fill the code from the existing entry during reconfiguration
        default_code = None
        if self.source == "reconfigure":
            current = self._get_reconfigure_entry()
            default_code = current.data.get(CONF_CODE)

        return self.async_show_form(
            step_id="code", data_schema=_code_schema(default_code), errors=errors
        )
    

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle re-authentication when the login code is no longer valid."""
        return await self.async_step_reauth_confirm()


    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask the user for a new login code."""
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            data = {**entry.data, CONF_CODE: user_input[CONF_CODE]}
            try:
                info = await validate_input(self.hass, data)
            except ConnectException:
                _LOGGER.exception("Connection error setting up the Bwt Api")
                errors["base"] = "cannot_connect"
            except WrongCodeException:
                _LOGGER.exception("Wrong user code passed to bwt api")
                errors["base"] = "invalid_code_or_api_disabled"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                # Only the local API model validates the code; for any other
                # model the code was not checked, so never report success.
                if info["model"] != BwtModel.PERLA_LOCAL_API:
                    return self.async_abort(reason="reauth_unsupported_model")
                return self.async_update_reload_and_abort(entry, data=data)

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_CODE): str}),
            description_placeholders={"host": entry.data[CONF_HOST]},
            errors=errors,
        )


    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None):
        """Manual reconfiguration to change a setting."""
        current = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            # Does not match the entry being reconfigured; outside the try block
            # so the abort is not swallowed below.
            self._async_abort_entries_match({CONF_HOST: user_input[CONF_HOST]})
            try:
                info = await validate_input(self.hass, user_input)
                match info["model"]:
                    case BwtModel.PERLA_LOCAL_API:
                        # Need to ask for login code during reconfigure
                        self._host = user_input[CONF_HOST]
                        return await self.async_step_code()
                    case BwtModel.PERLA_SILK | BwtModel.SMART_DOS:
                        user_input["model"] = info["model"].name
                        return self._async_finish_reconfigure(user_input)
                    case _:
                        errors["base"] = "unsupported_model"
            except ConnectException:
                _LOGGER.exception("Connection error setting up the Bwt Api")
                errors["base"] = "cannot_connect"
            except WrongCodeException:
                _LOGGER.exception("Wrong user code passed to bwt api")
                errors["base"] = "invalid_code_or_api_disabled"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="reconfigure", data_schema=_host_schema(
                host=current.data[CONF_HOST],
            ), errors=errors
        )
