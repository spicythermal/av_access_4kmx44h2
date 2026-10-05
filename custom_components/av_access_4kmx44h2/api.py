"""
API client for the AV Access 4KMX44-H2 HDMI matrix.

This talks to the matrix's own web control endpoint (the same one its
built-in Web UI uses), reverse-engineered from that UI's own JavaScript:

  - All requests are POSTs to http://<host>/action
  - Every GET/SET hardware command (cmdtype=0) MUST end with a literal
    "\\r\\n" in the cmdstr field, or the device's embedded web server
    hangs and eventually resets the connection without responding.
  - Login/system commands (cmdtype=1, e.g. "postauthinfo") do NOT use
    the \\r\\n terminator.
  - There is no cookie or token issued on login -- the device's notion
    of "session" appears to be tied to keeping the same underlying TCP
    connection open. To avoid relying on a long-lived connection (this
    device's embedded HTTP stack is quite minimal and was unreliable
    about keep-alive during testing), every call here opens a fresh
    connection, logs in, does its work, and closes -- mirroring the
    exact pattern that was confirmed to work during manual testing.
"""

from __future__ import annotations

import logging

import aiohttp

_LOGGER = logging.getLogger(__name__)

NUM_PORTS = 4


class MatrixApiError(Exception):
    """Raised when a command to the matrix fails."""


class MatrixClient:
    """Thin async client for the 4KMX44-H2's /action endpoint."""

    def __init__(self, host: str, username: str, password: str) -> None:
        self._host = host
        self._username = username
        self._password = password
        self._base_url = f"http://{host}"

    def _headers(self) -> dict:
        return {
            "User-Agent": "Mozilla/5.0 (HomeAssistant av_access_4kmx44h2 integration)",
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "text/plain, */*; q=0.01",
            "Origin": self._base_url,
            "Referer": f"{self._base_url}/",
        }

    async def _transaction(self, commands: list[tuple[str, str]]) -> list[str]:
        """
        Open one connection, log in, run each (cmdtype, cmdstr) command in
        order, and return the raw response text for each. Login's own
        response is not included in the returned list.
        """
        timeout = aiohttp.ClientTimeout(total=8)
        async with aiohttp.ClientSession(
            headers=self._headers(), timeout=timeout
        ) as session:
            try:
                await session.post(
                    f"{self._base_url}/action",
                    data={
                        "cmdtype": "1",
                        "cmdstr": "postauthinfo",
                        "account": self._username,
                        "password": self._password,
                    },
                )
            except Exception as err:  # noqa: BLE001 -- see comment below
                # This device's login response is a bare "200 OK" with no
                # Content-Length/Transfer-Encoding/body at all. Confirmed via
                # curl -v and plain `requests` testing that this is the
                # device's normal (if non-compliant) login response shape --
                # both tolerated it as "200, empty body". aiohttp's stricter
                # parser raises on this instead of just returning an empty
                # body (seen in practice as an error whose message is a raw
                # RawResponseMessage repr showing code=200 but no headers),
                # so a parse failure specifically on THIS call is not
                # treated as a real login failure. We catch broadly here
                # (rather than a specific aiohttp exception class) because
                # the exact exception type for this malformed-response case
                # varies by aiohttp version, and silently swallowing it is
                # safe: if the credentials were actually wrong, the real
                # command below will fail instead (the device won't execute
                # commands pre-auth), and THAT failure is treated as fatal.
                _LOGGER.debug(
                    "Login response couldn't be parsed (expected with this "
                    "device's non-standard empty response) -- proceeding. "
                    "%s: %s",
                    type(err).__name__,
                    err,
                )

            results = []
            for i, (cmdtype, cmdstr) in enumerate(commands):
                if cmdtype == "0" and not cmdstr.endswith("\r\n"):
                    cmdstr = cmdstr + "\r\n"
                # The device has been observed to flake on the very first
                # command right after login (connection reset with no
                # response), while working reliably after that. Retry once
                # for exactly that case rather than failing the whole
                # transaction on a known transient hiccup.
                attempts = 2 if i == 0 else 1
                last_err: Exception | None = None
                text = None
                for attempt in range(attempts):
                    try:
                        resp = await session.post(
                            f"{self._base_url}/action",
                            data={"cmdtype": cmdtype, "cmdstr": cmdstr},
                        )
                        text = await resp.text()
                        last_err = None
                        break
                    except aiohttp.ClientError as err:
                        last_err = err
                        _LOGGER.debug(
                            "Command '%s' attempt %d/%d failed: %s",
                            cmdstr.strip(),
                            attempt + 1,
                            attempts,
                            err,
                        )
                if last_err is not None:
                    raise MatrixApiError(
                        f"Command '{cmdstr.strip()}' failed: {last_err}"
                    ) from last_err
                results.append(text.strip())
            return results

    async def async_test_connection(self) -> None:
        """Raise MatrixApiError if we can't log in and talk to the device."""
        # GET MP all has been reliable in testing, unlike GET VER which
        # has shown occasional first-command-after-login flakiness.
        await self._transaction([("0", "GET MP all")])

    async def async_get_status(self) -> dict:
        """
        Return current routing and mute state:
        {
          "routing": {1: <input routed to output 1>, 2: ..., 3: ..., 4: ...},
          "mute":    {1: <bool, True=muted>, 2: ..., 3: ..., 4: ...},
        }
        """
        mp_text, mute_text = await self._transaction(
            [("0", "GET MP all"), ("0", "GET MUTE all")]
        )

        routing: dict[int, int] = {}
        for line in mp_text.splitlines():
            # e.g. "MP hdmiin2 hdmiout3"
            parts = line.strip().split()
            if len(parts) != 3 or parts[0].upper() != "MP":
                continue
            try:
                in_num = int("".join(c for c in parts[1] if c.isdigit()))
                out_num = int("".join(c for c in parts[2] if c.isdigit()))
            except ValueError:
                continue
            routing[out_num] = in_num

        mute: dict[int, bool] = {}
        for line in mute_text.splitlines():
            # e.g. "MUTE audioout1 off"
            parts = line.strip().split()
            if len(parts) != 3 or parts[0].upper() != "MUTE":
                continue
            try:
                out_num = int("".join(c for c in parts[1] if c.isdigit()))
            except ValueError:
                continue
            mute[out_num] = parts[2].strip().lower() == "on"

        if not routing or not mute:
            raise MatrixApiError(
                f"Unexpected response format. MP={mp_text!r} MUTE={mute_text!r}"
            )

        return {"routing": routing, "mute": mute}

    async def async_set_input(self, output: int, input_: int) -> None:
        """Route hdmiin{input_} to hdmiout{output}."""
        await self._transaction(
            [("0", f"SET SW hdmiin{input_} hdmiout{output}")]
        )

    async def async_set_mute(self, output: int, mute: bool) -> None:
        """Mute or unmute audioout{output}."""
        state = "on" if mute else "off"
        await self._transaction([("0", f"SET MUTE audioout{output} {state}")])
