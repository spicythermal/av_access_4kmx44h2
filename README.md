# AV Access 4KMX44-H2 for Home Assistant

A custom Home Assistant integration for the [AV Access 4KMX44-H2](https://www.avaccess.com) 4x4 HDMI matrix switch.

Talks to the matrix's own web control endpoint (the same one its built-in Web UI uses) — reverse-engineered directly from that UI's JavaScript, since the device has no publicly documented IP control API.

## What it does

For each of the matrix's 4 outputs, this integration creates:

- **`select.output_N_input`** — choose which of the 4 HDMI inputs is routed to that output.
- **`switch.output_N_audio`** — turn that output's S/PDIF audio on (unmuted) or off (muted).

Both update automatically every 10 seconds, so changes made directly on the matrix's own Web UI or front panel show up in Home Assistant too.

## Installation

### Via HACS (custom repository)

1. In Home Assistant, go to **HACS → Integrations**.
2. Click the **⋮** menu (top right) → **Custom repositories**.
3. Add this repository's URL, category **Integration**.
4. Find "AV Access 4KMX44-H2" in HACS and install it.
5. Restart Home Assistant.

### Manual installation

1. Copy the `custom_components/av_access_4kmx44h2` folder into your Home Assistant `config/custom_components/` directory.
2. Restart Home Assistant.

## Setup

1. Go to **Settings → Devices & Services → Add Integration**.
2. Search for "AV Access 4KMX44-H2".
3. Enter the matrix's IP address and the Web UI login credentials (same ones used to log into the matrix's own web interface).

## Notes on the device's quirks

This matrix's embedded web server is fairly minimal and has a few non-standard behaviors this integration works around:

- Every hardware command must end with a literal `\r\n`, or the device hangs and resets the connection without responding.
- The login endpoint returns a bare `200 OK` with no headers or body at all. 
- There's no session cookie or token; each batch of commands opens a fresh connection and logs in immediately before use.
- This firmware has no live "signal present" / "HPD" status command for outputs — only `GET EDID_R hdmioutN`, which reflects whether a display has ever completed an EDID handshake on that port (cached), not whether it's currently powered on.

## License

MIT
