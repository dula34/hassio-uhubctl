# uhubctl Add-on Documentation

This document provides the operational and technical details for the `uhubctl` Home Assistant add-on.

## Overview

The add-on runs a Python bridge that:

1. Discovers USB hubs using `uhubctl`
2. Connects to Home Assistant's configured MQTT service
3. Publishes hub/port status as JSON
4. Listens for MQTT control commands
5. Executes `uhubctl` actions and republishes updated state

## Runtime behavior

- Add-on startup script: `run.sh`
- Bridge process: `python3 main.py`
- If MQTT is not available, startup loop retries every 30 seconds
- If the bridge exits, supervisor loop restarts it after 30 seconds

## MQTT integration

MQTT connection parameters are provided by Home Assistant service discovery.

### Availability

- Topic: `AVAILABILITY_TOPIC`
- Payloads:
  - `Online` when connected
  - `Offline` via MQTT Last Will

### State publishing

State topic format:

```text
<STATUS_TOPIC>/HUB<location>/STATE
```

Example:

```text
tele/uhubctl/localhost/HUB3-4/STATE
```

Example state payload:

```json
{
  "Time": "2026-06-06 12:34:56",
  "Location": "3-4",
  "Vid": 1234,
  "Pid": 5678,
  "USBVersion": 3,
  "POWER1": "ON",
  "POWER2": "OFF"
}
```

### Command subscription

Command topic format:

```text
<COMMAND_TOPIC>/HUB<location>/POWER<port>
```

Payloads supported:

- `ON`
- `OFF`

Command example:

- Topic: `cmnd/uhubctl/localhost/HUB3-4/POWER1`
- Payload: `OFF`

## Add-on options

Defined in `config.json`.

| Option | Required | Description |
|---|---|---|
| `AVAILABILITY_TOPIC` | Yes | MQTT topic used for availability/LWT |
| `STATUS_TOPIC` | Yes | Prefix for hub state topics |
| `COMMAND_TOPIC` | Yes | Prefix for command topics |
| `LOG_LEVEL` | No | Verbosity level (`debug`, `info`, `warn`, `error`, `critical`) |

## Logging

- Main log output is emitted from both `run.sh` and `main.py`
- `LOG_LEVEL` controls Python bridge verbosity
- Use `debug` when validating topic mapping or parsing issues

## Troubleshooting

1. **No hubs discovered**
   - Verify the USB hub supports `uhubctl`
   - Check hardware passthrough and host USB visibility
2. **No MQTT messages**
   - Confirm MQTT add-on/integration is running in Home Assistant
   - Check that the add-on starts without credential errors
3. **Commands not applied**
   - Confirm command topic matches exact format (`HUB<location>/POWER<port>`)
   - Confirm payload is `ON` or `OFF`
4. **Unexpected restarts**
   - Check add-on logs for Python exceptions
   - Temporarily set `LOG_LEVEL` to `debug`

## Notes and limitations

- Port state values are represented as strings: `ON` / `OFF`
- Hub location is parsed from `uhubctl` output (for example `3-4`)
- Topic format is strict; malformed topic paths are ignored

## Files

- Bridge code: `main.py`
- Startup loop: `run.sh`
- Add-on metadata and schema: `config.json`
- Build architecture mapping: `build.json`

