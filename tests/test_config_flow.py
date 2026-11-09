"""Tests for the bwt_perla config flow."""
import voluptuous as vol
from unittest.mock import AsyncMock, MagicMock, patch

from bwt_api.bwt import BwtModel
from bwt_api.exception import ConnectException, WrongCodeException
from homeassistant import config_entries
from homeassistant.const import CONF_CODE, CONF_HOST
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.bwt_perla.const import DOMAIN

HOST = "192.168.1.50"


def _mock_api(get_current_data=None):
    """Create a mock api usable as `async with BwtApi(...) as api`."""
    api = MagicMock()
    api.__aenter__ = AsyncMock(return_value=api)
    api.__aexit__ = AsyncMock(return_value=None)
    data = MagicMock()
    data.columns = 1
    api.get_current_data = get_current_data or AsyncMock(return_value=data)
    api.get_registers = AsyncMock(return_value={})
    return api


def _patch_model(model):
    return patch(
        "custom_components.bwt_perla.config_flow.determine_bwt_model",
        AsyncMock(return_value=model),
    )


def _patch_local_api(api):
    return patch("custom_components.bwt_perla.config_flow.BwtApi", return_value=api)


def _entry(**kwargs):
    data = {
        CONF_HOST: HOST,
        CONF_CODE: "old-code",
        "model": BwtModel.PERLA_LOCAL_API.name,
    }
    return MockConfigEntry(domain=DOMAIN, version=3, data=data, title="BWT Perla One", **kwargs)


async def test_user_flow_local_api(hass):
    """User enters host, then the login code, and an entry is created."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    with _patch_model(BwtModel.PERLA_LOCAL_API), _patch_local_api(_mock_api()):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_HOST: HOST}
        )
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "code"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_CODE: "1234"}
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "BWT Perla One"
    assert result["data"] == {
        CONF_HOST: HOST,
        CONF_CODE: "1234",
        "model": BwtModel.PERLA_LOCAL_API.name,
    }


async def test_user_flow_silk(hass):
    """Silk devices need no code and create the entry directly."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    with (
        _patch_model(BwtModel.PERLA_SILK),
        patch(
            "custom_components.bwt_perla.config_flow.BwtSilkApi",
            return_value=_mock_api(),
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_HOST: HOST}
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "BWT Perla Silk"
    assert result["data"]["model"] == BwtModel.PERLA_SILK.name


async def test_user_flow_cannot_connect(hass):
    """A connection error is shown on the host form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    with patch(
        "custom_components.bwt_perla.config_flow.determine_bwt_model",
        AsyncMock(side_effect=ConnectException("boom")),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_HOST: HOST}
        )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_code_step_wrong_code(hass):
    """A wrong code shows an error and allows retrying."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    bad_api = _mock_api(AsyncMock(side_effect=WrongCodeException("bad")))
    with _patch_model(BwtModel.PERLA_LOCAL_API), _patch_local_api(bad_api):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_HOST: HOST}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_CODE: "wrong"}
        )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "code"
    assert result["errors"] == {"base": "invalid_code_or_api_disabled"}


async def test_reconfigure_flow(hass):
    """Reconfigure with a new host and code updates the existing entry."""
    entry = _entry()
    entry.add_to_hass(hass)

    result = await entry.start_reconfigure_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    with (
        _patch_model(BwtModel.PERLA_LOCAL_API),
        _patch_local_api(_mock_api()),
        patch.object(hass.config_entries, "async_schedule_reload"),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_HOST: "192.168.1.51"}
        )
        assert result["step_id"] == "code"
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_CODE: "new-code"}
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfiguration_successful"
    assert entry.data[CONF_HOST] == "192.168.1.51"
    assert entry.data[CONF_CODE] == "new-code"


async def test_reauth_flow_success(hass):
    """Reauth with a valid new code updates the entry and aborts."""
    entry = _entry()
    entry.add_to_hass(hass)

    result = await entry.start_reauth_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    with (
        _patch_model(BwtModel.PERLA_LOCAL_API),
        _patch_local_api(_mock_api()),
        patch.object(hass.config_entries, "async_reload", AsyncMock()) as reload,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_CODE: "new-code"}
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data[CONF_CODE] == "new-code"
    assert entry.data[CONF_HOST] == HOST
    reload.assert_awaited_once_with(entry.entry_id)


async def test_reauth_flow_wrong_code(hass):
    """Reauth with another wrong code shows the error and keeps the entry."""
    entry = _entry()
    entry.add_to_hass(hass)

    result = await entry.start_reauth_flow(hass)
    bad_api = _mock_api(AsyncMock(side_effect=WrongCodeException("bad")))
    with _patch_model(BwtModel.PERLA_LOCAL_API), _patch_local_api(bad_api):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_CODE: "still-wrong"}
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"
    assert result["errors"] == {"base": "invalid_code_or_api_disabled"}
    assert entry.data[CONF_CODE] == "old-code"


async def test_reauth_form_does_not_prefill_code(hass):
    """The rejected code must not be offered as a default."""
    entry = _entry()
    entry.add_to_hass(hass)

    result = await entry.start_reauth_flow(hass)
    key = next(k for k in result["data_schema"].schema if k == CONF_CODE)
    assert key.default is vol.UNDEFINED


async def test_reauth_non_local_model_aborts(hass):
    """Reauth must not succeed when the code could not be validated."""
    entry = _entry()
    entry.add_to_hass(hass)

    result = await entry.start_reauth_flow(hass)
    with (
        _patch_model(BwtModel.PERLA_SILK),
        patch("custom_components.bwt_perla.config_flow.BwtSilkApi") as silk,
    ):
        silk.return_value.__aenter__.return_value.get_registers = AsyncMock()
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_CODE: "x"}
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_unsupported_model"
    assert entry.data[CONF_CODE] == "old-code"


async def test_duplicate_host_aborts(hass):
    """A second flow for an already configured host aborts."""
    MockConfigEntry(
        domain=DOMAIN, version=3, unique_id=HOST, data={CONF_HOST: HOST}
    ).add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    with _patch_model(BwtModel.PERLA_SILK), patch(
        "custom_components.bwt_perla.config_flow.BwtSilkApi", return_value=_mock_api()
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_HOST: HOST.upper()}
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_created_entry_has_unique_id(hass):
    """New entries are keyed on the host."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    with _patch_model(BwtModel.PERLA_SILK), patch(
        "custom_components.bwt_perla.config_flow.BwtSilkApi", return_value=_mock_api()
    ), patch("custom_components.bwt_perla.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_HOST: HOST}
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["result"].unique_id == HOST


async def test_reconfigure_updates_unique_id(hass):
    """Changing the host re-keys the entry."""
    entry = _entry(unique_id=HOST)
    entry.add_to_hass(hass)
    result = await entry.start_reconfigure_flow(hass)
    with (
        _patch_model(BwtModel.PERLA_LOCAL_API),
        _patch_local_api(_mock_api()),
        patch.object(hass.config_entries, "async_schedule_reload"),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_HOST: "192.168.1.51"}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_CODE: "c"}
        )
    assert result["reason"] == "reconfiguration_successful"
    assert entry.unique_id == "192.168.1.51"


async def test_reconfigure_silk_updates_unique_id(hass):
    """The non-code branch of reconfigure re-keys the entry too."""
    entry = _entry(unique_id=HOST)
    entry.add_to_hass(hass)
    result = await entry.start_reconfigure_flow(hass)
    with (
        _patch_model(BwtModel.PERLA_SILK),
        patch(
            "custom_components.bwt_perla.config_flow.BwtSilkApi",
            return_value=_mock_api(),
        ),
        patch.object(hass.config_entries, "async_schedule_reload"),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_HOST: "Other.Local"}
        )
    assert result["reason"] == "reconfiguration_successful"
    assert entry.unique_id == "other.local"


async def test_reconfigure_to_existing_host_aborts(hass):
    """Reconfiguring onto a host another entry owns aborts."""
    entry = _entry(unique_id=HOST)
    entry.add_to_hass(hass)
    MockConfigEntry(
        domain=DOMAIN, version=3, unique_id="192.168.1.51", data={CONF_HOST: "192.168.1.51"}
    ).add_to_hass(hass)
    result = await entry.start_reconfigure_flow(hass)
    with (
        _patch_model(BwtModel.PERLA_LOCAL_API),
        _patch_local_api(_mock_api()),
        patch.object(hass.config_entries, "async_schedule_reload") as reload,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_HOST: "192.168.1.51"}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_CODE: "c"}
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert entry.unique_id == HOST
    assert entry.data[CONF_HOST] == HOST
    reload.assert_not_called()
