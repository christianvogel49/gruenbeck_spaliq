"""Config flow for Grünbeck spaliQ integration."""
import socket
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT

from .const import DOMAIN

CONF_UNIT_ID = "unit_id"
CONF_POLL_INTERVAL = "poll_interval"

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_PORT, default=502): int,
        vol.Optional(CONF_UNIT_ID, default=1): int,
        vol.Optional(CONF_POLL_INTERVAL, default=30): int,
    }
)


class GruenbeckConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Grünbeck spaliQ."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            port = user_input.get(CONF_PORT, 502)
            try:
                await self.hass.async_add_executor_job(
                    self._test_connection, host, port
                )
            except Exception:
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title=f"Grünbeck spaliQ ({host})",
                    data={
                        "host": host,
                        "port": port,
                        "unit_id": user_input.get(CONF_UNIT_ID, 1),
                        "poll_interval": user_input.get(CONF_POLL_INTERVAL, 30),
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    @staticmethod
    def _test_connection(host: str, port: int) -> None:
        """Attempt a TCP connection to verify the device is reachable."""
        with socket.create_connection((host, port), timeout=5):
            pass
