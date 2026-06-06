# Home Assistant Addon: MQTT Bridge for uhubctl

This project was spawned by the desire to control [`uhubctl`](https://github.com/mvp/uhubctl) from within Home Assistant.

This add-on takes advantage of the API provided by Home Assistant and is extremely easy to use. You no longer even need to set up credentials to connect to the MQTT server.

## Features

- ✅ Control USB power per-port on smart USB hubs
- ✅ MQTT-based communication
- ✅ Real-time status reporting
- ✅ Support for multiple hub architectures (amd64, armhf, armv7, aarch64, i386)
- ✅ Home Assistant integration ready
- ✅ Health checks included
- ✅ Comprehensive error handling

## Changelog

### v1.0.0 (Current)
- **Modernized**: Updated paho-mqtt to version 2.0.0+ (from 1.5.1)
- **Improved**: Better error handling throughout the application
- **Enhanced**: Comprehensive logging for debugging
- **Fixed**: Build configuration errors (removed malformed base image tag)
- **Optimized**: Docker image size reduction (removed unnecessary dependencies)
- **Added**: Configuration validation
- **Added**: Health checks for container monitoring
- **Improved**: Shell script error handling (set -eu)

## Add-on Install Instructions
1. Navigate in your Home Assistant frontend to <kbd>Supervisor</kbd> -> <kbd>Add-on Store</kbd>.

2. Click the 3-dots menu at upper right <kbd>...</kbd> > <kbd>Repositories</kbd> and add this repository's URL: [https://github.com/mochipon/hassio-uhubctl](https://github.com/mochipon/hassio-uhubctl)

3. Scroll down the page to find the new repository, and click the new add-on named "MQTT Bridge for uhubctl"

4. Click <kbd>Install</kbd> and give it a few minutes to finish downloading.

5. Click <kbd>Start</kbd>, give it a few seconds to spin up.

## Configuration

By default, the add-on publishes telemetry data to the topic `tele/uhubctl/localhost`. Find the target hub you want to control by checking Vendor ID (`Vid`), Product ID (`Pid`), and number of ports of each hub. 

<img src="images/mqtt.png" width="1000"/>

### Configuration Options

| Option             | Type   | Default                      | Description                                        |
|--------------------|--------|------------------------------|----------------------------------------------------|
| AVAILABILITY_TOPIC | string | `tele/uhubctl/localhost/LWT` | MQTT topic for availability status                 |
| STATUS_TOPIC       | string | `tele/uhubctl/localhost`     | MQTT topic prefix for hub status                   |
| COMMAND_TOPIC      | string | `cmnd/uhubctl/localhost`     | MQTT topic prefix for commands                     |
| LOG_LEVEL          | list   | `info`                       | Logging level (debug, info, warn, error, critical) |

### Example Home Assistant Configuration

Here is an example of a yaml entry in Home Assistant to control `Port 1` of `HUB3-4`.

```yaml
mqtt:
  switch:
    - name: USB Fan
      unique_id: usb-fan
      icon: "mdi:fan"
      state_topic: "tele/uhubctl/localhost/HUB3-4/STATE"
      value_template: "{{ value_json.POWER1 }}"
      command_topic: "cmnd/uhubctl/localhost/HUB3-4/POWER1"
      availability_topic: "tele/uhubctl/localhost/LWT"
      payload_available: "Online"
      payload_not_available: "Offline"
```

## Troubleshooting

If you encounter issues:

1. **Check Logs**: View add-on logs in Home Assistant for detailed error messages
2. **MQTT Connection**: Ensure the MQTT broker is running and accessible
3. **USB Device**: Verify that your USB hub is properly connected and supported by uhubctl
4. **Log Level**: Set LOG_LEVEL to `debug` for more detailed logging

## Requirements

- Home Assistant with MQTT Broker add-on running
- Compatible USB hub (with uhubctl support)

## License

MIT - See LICENSE file for details


