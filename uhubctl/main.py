import argparse
import datetime
import json
import logging
import os
import re
import subprocess

import paho.mqtt.client as mqtt
from paho.mqtt.client import CallbackAPIVersion

APP_VERSION = "1.1.2"

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
logger.addHandler(handler)
handler.setFormatter(logging.Formatter("[%(asctime)s] [%(funcName)s] %(message)s"))
logger.propagate = False


def run_in_shell(command, timeout=10):
    try:
        logger.debug("Command kicked: {command}".format(command=command))
        ret = subprocess.run(
            command, shell=True, timeout=timeout, stdout=subprocess.PIPE, text=True
        )
        logger.debug(
            "Command exited with exit code {exit_code}".format(exit_code=ret.returncode)
        )
        return ret
    except Exception:
        logger.exception("Fatal error in running a command")
        raise


class USBHUB:
    def __init__(self, location, vid, pid, usbversion, nports, ports, powerswitching="unknown"):
        self._location = location
        self._vid = vid
        self._pid = pid
        self._usbversion = usbversion
        self._nports = nports
        self._ports = ports
        self._powerswitching = powerswitching

    def add_port(self, number, status):
        self._ports.append(USBPORT(self.location, number, status))

    @property
    def location(self):
        return self._location

    @property
    def vid(self):
        return self._vid

    @property
    def pid(self):
        return self._pid

    @property
    def usbversion(self):
        return self._usbversion

    @property
    def nports(self):
        return self._nports

    @property
    def powerswitching(self):
        return self._powerswitching


class USBPORT:
    def __init__(self, hub_location, number, status):
        self._hub_location = hub_location
        self._number = number
        self._enabled = status

    def on(self):
        self._enabled = True

    def off(self):
        self._enabled = False

    @property
    def hub_location(self):
        return self._hub_location

    @property
    def number(self):
        return self._number

    @property
    def enabled(self):
        return self._enabled


class UHUBCTL:
    def _parser(self, stdout, action=False):
        ret = []

        result = stdout.strip().split("\n")

        try:
            lineidxs_hubheader = [
                index for index, line in enumerate(result) if "status for hub" in line
            ]
            if not len(lineidxs_hubheader) > 0:
                raise ValueError("No hub headers found")
        except ValueError as e:
            logger.error("Failed to find any smart hubs: {}".format(str(e)))
            return []

        logger.debug("Found {count} hub(s) in output".format(count=len(lineidxs_hubheader)))

        for lineidx_hubheader in lineidxs_hubheader:
            parsed_line = re.search(
                r"status for hub ([0-9A-Za-z_.:-]+) \[([0-9a-fA-F]{4}):([0-9a-fA-F]{4}).*USB (\d)\.\d{2}, (\d+) ports, ([^\]]+)\]",
                result[lineidx_hubheader],
            )
            if parsed_line is None:
                continue

            hub = USBHUB(
                location=parsed_line.group(1),
                vid=int(parsed_line.group(2), 16),
                pid=int(parsed_line.group(3), 16),
                usbversion=int(parsed_line.group(4)),
                nports=int(parsed_line.group(5)),
                ports=[],
                powerswitching=parsed_line.group(6).strip().lower(),
            )

            lineidx_port_start = lineidx_hubheader + 1
            lineidx_port_end = (
                lineidx_port_start + hub.nports
                if not action
                else lineidx_port_start + 1
            )

            for lineidx in range(lineidx_port_start, min(lineidx_port_end, len(result))):
                # Port Information
                parsed_line = re.search(r"Port (\d+): (\d{4})", result[lineidx])
                if parsed_line is None:
                    continue
                port_number = int(parsed_line.group(1))
                port_status_bit = int(parsed_line.group(2), 16)
                logger.debug(
                    "Hub {location} Port {port_number} = {port_status_bit:#06x}".format(
                        location=hub.location,
                        port_number=port_number,
                        port_status_bit=port_status_bit,
                    )
                )

                if hub.usbversion == 3:
                    # USB 3.0 spec Table 10-10
                    # USB_SS_PORT_STAT_POWER = 0x0200
                    POWER_ON_BIT = 0x0200
                else:
                    # USB 2.0 spec Table 11-21
                    # USB_PORT_STAT_POWER = 0x0100
                    POWER_ON_BIT = 0x0100

                if port_status_bit & POWER_ON_BIT:
                    port_status = True
                else:
                    port_status = False

                hub.add_port(port_number, port_status)

            ret.append(hub)

        return ret

    def fetch_allinfo(self):
        try:
            logger.debug("Fetch current status for all smart hubs")
            ret = run_in_shell("uhubctl")
            stdout = ret.stdout

            result = self._parser(stdout)
            return result if result else []
            
        except Exception:
            logger.exception("Failed to fetch current status")
            return []

    def do_action(self, port, action):
        try:
            action = action.lower()
            if action not in ["on", "off"]:
                raise ValueError
        except ValueError:
            logger.error(
                "Illegal action to the port: action={action}".format(action=action)
            )
            return False

        logger.debug(
            "Send command to the port: hub={location}, port={port}, action={action}".format(
                location=port.hub_location, port=port.number, action=action
            )
        )

        try:
            ret = run_in_shell(
                "uhubctl -l {location} -p {port} -a {action} -r 100".format(
                    location=port.hub_location, port=port.number, action=action
                )
            )
            stdout = ret.stdout

            # _parser returns [Current status, New status]
            parsed = self._parser(stdout, action=True)
            if not parsed or not parsed[-1]._ports:
                logger.error(
                    "Failed to parse uhubctl action output: hub={location}, port={port}".format(
                        location=port.hub_location,
                        port=port.number,
                    )
                )
                return False

            newstatus_hub = parsed[-1]
            newstatus_port = newstatus_hub._ports[0]

            if newstatus_port.enabled:
                port.on()
            else:
                port.off()

            return True
        except Exception:
            logger.exception(
                "Failed to change port status: hub={location}, port={port}, action={action}".format(
                    location=port.hub_location, port=port.number, action=action
                )
            )
            return False


class USBHUB_MQTT_Error(Exception):
    pass


class USBHUB_MQTT:
    def __init__(self, opt_file):
        with opt_file:
            self._cfg = json.load(opt_file)
            self._usbhubs = []
            self._will = (self._cfg["AVAILABILITY_TOPIC"], "Offline", 1, True)

        self._cfg.setdefault("DISCOVERY_ENABLED", True)
        self._cfg.setdefault("DISCOVERY_PREFIX", "homeassistant")
        self._cfg.setdefault("FORCE_OPTIMISTIC", False)
        
        # Validate required config keys
        required_keys = ["AVAILABILITY_TOPIC", "STATUS_TOPIC", "COMMAND_TOPIC"]
        for key in required_keys:
            if key not in self._cfg:
                raise USBHUB_MQTT_Error("Missing required configuration: {}".format(key))
        
        logger.info("Configuration loaded successfully")

    def _to_object_id(self, value):
        return re.sub(r"[^a-z0-9_]+", "_", value.lower()).strip("_")

    def _discovery_device_payload(self, usbhub):
        hub_id = self._to_object_id("uhubctl_hub_{}".format(usbhub.location))
        return {
            "identifiers": [hub_id],
            "name": "USB Hub {}".format(usbhub.location),
            "manufacturer": "uhubctl",
            "model": "{:04x}:{:04x}".format(usbhub.vid, usbhub.pid),
            "sw_version": APP_VERSION,
        }

    def _discovery_payload(self, usbhub, port):
        object_id = self._to_object_id(
            "uhubctl_hub_{}_power{}".format(usbhub.location, port.number)
        )
        payload = {
            "name": "HUB{} POWER{}".format(usbhub.location, port.number),
            "unique_id": object_id,
            "object_id": object_id,
            "state_topic": "{prefix}/HUB{location}/STATE".format(
                prefix=self._cfg["STATUS_TOPIC"], location=usbhub.location
            ),
            "value_template": "{{{{ value_json.POWER{} }}}}".format(port.number),
            "command_topic": "{prefix}/HUB{location}/POWER{number}".format(
                prefix=self._cfg["COMMAND_TOPIC"],
                location=usbhub.location,
                number=port.number,
            ),
            "payload_on": "ON",
            "payload_off": "OFF",
            "availability_topic": self._cfg["AVAILABILITY_TOPIC"],
            "payload_available": "Online",
            "payload_not_available": "Offline",
            "icon": "mdi:usb-port",
            "device": self._discovery_device_payload(usbhub),
        }

        if self._cfg["FORCE_OPTIMISTIC"]:
            payload["optimistic"] = True

        return object_id, payload

    def send_mqtt_discovery(self, client):
        if not self._cfg["DISCOVERY_ENABLED"]:
            logger.info("MQTT autodiscovery is disabled")
            return

        if not self._usbhubs:
            logger.debug("No USB hubs found for MQTT autodiscovery")
            return

        discovery_prefix = self._cfg["DISCOVERY_PREFIX"].rstrip("/")
        if not discovery_prefix:
            discovery_prefix = "homeassistant"
        for hub in self._usbhubs:
            for port in hub._ports:
                object_id, payload = self._discovery_payload(hub, port)
                topic = "{}/switch/{}/config".format(discovery_prefix, object_id)
                client.publish(
                    topic=topic,
                    payload=json.dumps(payload),
                    qos=1,
                    retain=True,
                )
                logger.info(
                    "Published MQTT discovery: topic={topic}".format(topic=topic)
                )

    def make_json_portstatus(self, usbhub):
        ret = {
            "Time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Location": usbhub.location,
            "Vid": usbhub.vid,
            "Pid": usbhub.pid,
            "USBVersion": usbhub.usbversion,
        }

        for port in usbhub._ports:
            idx = "POWER{number}".format(number=port.number)
            ret[idx] = "ON" if port.enabled else "OFF"

        return json.dumps(ret)

    def send_mqtt_hubstatus(self, client, usbhub=None):
        usbhubs = self._usbhubs if usbhub is None else [usbhub]

        if not usbhubs:
            logger.debug("No USB hubs to report status for")
            return

        for usbhub in usbhubs:
            topic = "{prefix}/HUB{location}/STATE".format(
                prefix=self._cfg["STATUS_TOPIC"], location=usbhub.location
            )
            payload = self.make_json_portstatus(usbhub)

            logger.debug(
                "MQTT Publish current status: topic={topic}, payload={payload}".format(
                    topic=topic, payload=payload
                )
            )

            try:
                client.publish(
                    topic=topic,
                    payload=payload,
                    qos=1,
                    retain=True,
                )
            except Exception:
                logger.exception("Failed to publish hub status to MQTT")

    def _supports_per_port_control(self, usbhub):
        return usbhub.powerswitching in {"ppps", "individual", "per-port", "per_port"}

    def _log_hub_capabilities(self):
        if not self._usbhubs:
            return

        for hub in self._usbhubs:
            logger.info(
                "Hub %s capability: power_switching=%s",
                hub.location,
                hub.powerswitching,
            )
            if not self._supports_per_port_control(hub):
                logger.warning(
                    "Hub %s may not support true per-port power switching (mode=%s). "
                    "Toggling one port can affect the whole hub.",
                    hub.location,
                    hub.powerswitching,
                )

    def on_mqtt_connect(self, client, userdata, flags, rc):
        if rc != 0:
            logger.error("MQTT connection failed with reason code: {}".format(str(rc)))
            logger.error("Connection failed - will attempt to reconnect...")
            return
        
        logger.info("MQTT Connected successfully")

        result, mid = client.subscribe(self._cfg["COMMAND_TOPIC"] + "/#", 1)
        logger.info(
            "MQTT Subscribe: topic={topic}, result={result}".format(
                topic=self._cfg["COMMAND_TOPIC"] + "/#",
                result="Success" if result == mqtt.MQTT_ERR_SUCCESS else "Failed",
            )
        )

        self._usbhubs = UHUBCTL().fetch_allinfo()
        if not self._usbhubs:
            logger.warning("No USB hubs found or uhubctl not available")
        else:
            logger.info("Found {count} USB hub(s)".format(count=len(self._usbhubs)))
            self._log_hub_capabilities()

        self.send_mqtt_discovery(client)
        self.send_mqtt_hubstatus(client)
        client.publish(
            topic=self._cfg["AVAILABILITY_TOPIC"], payload="Online", qos=1, retain=True
        )

    def on_mqtt_disconnect(self, client, userdata, rc):
        if rc == 0:
            logger.info("MQTT Disconnected cleanly")
        else:
            logger.warning("MQTT Connection lost (rc={})".format(str(rc)))

    def on_mqtt_message(self, client, userdata, message):
        """Generic message handler - routed to specific handlers via message_callback_add"""
        pass

    def on_mqtt_ctrl_message(self, client, userdata, message):
        payload = message.payload.decode(errors="replace")
        logger.info(
            "Received a control message: topic={topic}, payload={payload}".format(
                topic=message.topic, payload=payload
            )
        )

        if not self._usbhubs:
            logger.warning("No USB hubs available. Ignoring control message.")
            return False

        # Topic will be "hoge/usbhub/HUB1-3/POWER1
        parsed_topic = message.topic.split("/")
        try:
            command = parsed_topic[-1]
            hub_name = parsed_topic[-2]
            hub_location_match = re.search(r"HUB([0-9A-Za-z_.:-]+)", hub_name)
            if hub_location_match is None:
                raise AttributeError
            hub_location = hub_location_match.group(1)
        except (IndexError, AttributeError):
            logger.error("Failed to parse the topic string")
            return False

        parsed_command = re.search(r"([A-Z]+)(\d+)", command)
        if parsed_command is None:
            logger.error("Failed to parse the command string")
            return False

        if parsed_command.group(1) == "POWER":
            hub = None
            try:
                port_number = int(parsed_command.group(2))
                hub = [hub for hub in self._usbhubs if hub.location == hub_location][0]
                port = [port for port in hub._ports if port.number == port_number][0]
            except (IndexError, ValueError):
                logger.error("Illegal action request to unknown hub / port")
                return False

            before_map = self._port_state_map(hub)

            try:
                action = payload.strip()
                action_ok = UHUBCTL().do_action(port, action)
            except Exception:
                logger.exception("Failed to execute an action")
                action_ok = False

            if hub is not None and action_ok:
                refreshed_hubs = UHUBCTL().fetch_allinfo()
                if refreshed_hubs:
                    self._usbhubs = refreshed_hubs
                    refreshed_hub = next(
                        (entry for entry in refreshed_hubs if entry.location == hub_location),
                        None,
                    )
                    if refreshed_hub is not None:
                        self._log_unexpected_port_changes(
                            hub_location,
                            port_number,
                            before_map,
                            self._port_state_map(refreshed_hub),
                        )
                        hub = refreshed_hub
                    else:
                        logger.warning(
                            "Hub %s missing after refresh; keeping previous in-memory status",
                            hub_location,
                        )
                else:
                    logger.warning(
                        "Could not refresh hub status after action; using in-memory status"
                    )

                self.send_mqtt_hubstatus(client, hub)

    def _port_state_map(self, usbhub):
        return {port.number: port.enabled for port in usbhub._ports}

    def _log_unexpected_port_changes(self, hub_location, target_port, before_map, after_map):
        changed_ports = []
        for port_number, before_state in before_map.items():
            if port_number == target_port or port_number not in after_map:
                continue
            after_state = after_map[port_number]
            if before_state != after_state:
                changed_ports.append((port_number, before_state, after_state))

        if changed_ports:
            logger.warning(
                "Possible whole-hub side effect detected on HUB%s while toggling POWER%s: %s",
                hub_location,
                target_port,
                ", ".join(
                    "POWER{} {}->{}".format(
                        number,
                        "ON" if before else "OFF",
                        "ON" if after else "OFF",
                    )
                    for number, before, after in changed_ports
                ),
            )
        else:
            logger.info(
                "Verified targeted change on HUB%s POWER%s without side effects",
                hub_location,
                target_port,
            )

    def loop_forever(self):
        try:
            mqtt_hostname = os.environ.get("MQTT_HOST")
            mqtt_port_str = os.environ.get("MQTT_PORT")
            mqtt_username = os.environ.get("MQTT_USERNAME")
            mqtt_password = os.environ.get("MQTT_PASSWORD")

            if not all([mqtt_hostname, mqtt_port_str, mqtt_username, mqtt_password]):
                missing = []
                if not mqtt_hostname:
                    missing.append("MQTT_HOST")
                if not mqtt_port_str:
                    missing.append("MQTT_PORT")
                if not mqtt_username:
                    missing.append("MQTT_USERNAME")
                if not mqtt_password:
                    missing.append("MQTT_PASSWORD")
                raise KeyError("Missing required MQTT environment variables: {}".format(", ".join(missing)))

            try:
                mqtt_port = int(mqtt_port_str)
            except ValueError:
                raise ValueError("MQTT_PORT must be a valid integer, got: {}".format(mqtt_port_str))

            logger.info("MQTT Configuration found:")
            logger.info("  Host: {}".format(mqtt_hostname))
            logger.info("  Port: {}".format(mqtt_port))
            logger.info("  Username: {}".format(mqtt_username))

        except (KeyError, ValueError) as e:
            logger.error("Configuration error: {}".format(str(e)))
            return False

        try:
            logger.info("Creating MQTT client...")
            mqc = mqtt.Client(CallbackAPIVersion.VERSION1)

            mqc.on_connect = self.on_mqtt_connect
            mqc.on_disconnect = self.on_mqtt_disconnect
            mqc.on_message = self.on_mqtt_message
            mqc.message_callback_add(
                self._cfg["COMMAND_TOPIC"] + "/#", self.on_mqtt_ctrl_message
            )

            mqc.username_pw_set(mqtt_username, mqtt_password)
            mqc.will_set(*self._will)

            logger.info("Connecting to MQTT broker at {}:{}".format(mqtt_hostname, mqtt_port))
            mqc.connect(mqtt_hostname, mqtt_port, keepalive=60)

            logger.info("Starting MQTT event loop...")
            mqc.loop_forever()

        except OSError as e:
            logger.error("Network error: {}".format(str(e)))
            logger.info("Is the MQTT broker running at {}:{}?".format(mqtt_hostname, mqtt_port))
            return False
        except Exception as e:
            logger.error("MQTT error: {}".format(str(e)))
            logger.exception("Full stack trace")
            return False


if __name__ == "__main__":
    try:
        argp = argparse.ArgumentParser(description="MQTT - uhubctl bridge")
        argp.add_argument(
            "-c",
            "--config",
            type=argparse.FileType(),
            default="/data/options.json",
            help="User configuration file generated by Home Assistant",
        )

        log_levels = ["DEBUG", "INFO", "WARN", "ERROR", "CRITICAL"]
        log_levels = log_levels + list(map(lambda w: w.lower(), log_levels))
        argp.add_argument("--log", choices=log_levels, default="INFO", help="Logging level")

        args = vars(argp.parse_args())

        logger.setLevel(level=args["log"].upper())
        handler.setLevel(level=args["log"].upper())

        logger.info("Starting MQTT - uhubctl bridge v{}".format(APP_VERSION))
        usbhub_mqtt = USBHUB_MQTT(args["config"])
        usbhub_mqtt.loop_forever()
    except USBHUB_MQTT_Error as e:
        logger.error("Configuration error: {}".format(str(e)))
        exit(1)
    except Exception:
        logger.exception("Fatal error during startup")
        exit(1)
