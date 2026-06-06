# Home Assistant Add-on: uhubctl MQTT Bridge

This add-on exposes `uhubctl` USB port power control over MQTT so you can switch USB ports from Home Assistant.

## What it does

- Detects supported USB smart hubs via `uhubctl`
- Publishes hub and port state to MQTT
- Accepts MQTT commands to turn individual hub ports `ON`/`OFF`
- Publishes Last Will and availability status (`Online`/`Offline`)

## Requirements

- Home Assistant (Supervisor / Add-on system)
- MQTT broker configured in Home Assistant
- USB hub supported by `uhubctl`

## Install

1. Open **Settings -> Add-ons -> Add-on Store**.
2. Add this repository URL to your add-on repositories.
3. Install **uhubctl**.
4. Start the add-on.
5. Check logs and confirm MQTT topics are being published.

## Configuration

The add-on supports these options:

| Option | Type | Default |
|---|---|---|
| `AVAILABILITY_TOPIC` | string | `tele/uhubctl/localhost/LWT` |
| `STATUS_TOPIC` | string | `tele/uhubctl/localhost` |
| `COMMAND_TOPIC` | string | `cmnd/uhubctl/localhost` |
| `LOG_LEVEL` | enum | `info` |

`LOG_LEVEL` values: `debug`, `info`, `warn`, `error`, `critical`.

## MQTT topic patterns

- Availability: `<AVAILABILITY_TOPIC>`
- Hub state: `<STATUS_TOPIC>/HUB<location>/STATE`
- Commands: `<COMMAND_TOPIC>/HUB<location>/POWER<port>`

Example command topic:

```text
cmnd/uhubctl/localhost/HUB3-4/POWER1
```

Example command payload:

```text
ON
```

## Home Assistant example

```yaml
mqtt:
  switch:
    - name: USB Fan
      unique_id: usb-fan
      state_topic: "tele/uhubctl/localhost/HUB3-4/STATE"
      value_template: "{{ value_json.POWER1 }}"
      command_topic: "cmnd/uhubctl/localhost/HUB3-4/POWER1"
      availability_topic: "tele/uhubctl/localhost/LWT"
      payload_available: "Online"
      payload_not_available: "Offline"
      payload_on: "ON"
      payload_off: "OFF"
```

## More details

See `docs.md` in this folder for a deeper technical reference and troubleshooting guide.

