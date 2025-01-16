#!/usr/bin/env python3
# -*- coding=utf-8 -*-

import base64
import binascii
import json
import logging
import os
import sys
import uuid
import time
from enum import IntEnum

import msgpack
import paho.mqtt.client as mqtt
import redis


def get_fileenv(var: str):
    """Tries to read the provided env var name + _FILE first and read the file at the path of env var value.
    If that fails, it looks at /run/secrets/<env var>, otherwise uses the env var itself.
    Args:
        var (str): Name of the provided environment variable.

    Returns:
        Content of the environment variable file if exists, or the value of the environment variable.
        None if the environment variable does not exist.
    """
    if path := os.environ.get(var + "_FILE"):
        with open(path) as file:
            return file.read().strip()
    else:
        try:
            with open(os.path.join("run", "secrets", var.lower())) as file:
                return file.read().strip()
        except IOError:
            # mongo username needs to be string and not empty (fix for sphinx)
            if "sphinx" in sys.modules:
                return os.environ.get(var, "fail")
            else:
                return os.environ.get(var)


MQTT_HOST = os.environ.get("CON_MQTT_HOST", "127.0.0.1")
MQTT_PORT = int(os.environ.get("CON_MQTT_PORT", 1883))
MQTT_USERNAME = get_fileenv("CON_MQTT_USERNAME") or "lorabridge"
MQTT_PASSWORD = get_fileenv("CON_MQTT_PASSWORD") or "lorabridge"
CHIRP_TOPIC = os.environ.get("CON_CHIRP_TOPIC", "chirp/stack")
DEV_MAN_TOPIC = os.environ.get("CON_DEV_MAN_TOPIC", "devicemanager")
REDIS_HOST = os.environ.get("DEV_REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("DEV_REDIS_PORT", 6379))
REDIS_DB = int(os.environ.get("DEV_REDIS_DB", 0))

# DEVICE_CLASSES = ("None", "apparent_power", "aqi", "battery", "carbon_dioxide", "carbon_monoxide", "current", "date",
#                   "duration", "energy", "frequency", "gas", "humidity", "illuminance", "monetary", "nitrogen_dioxide",
#                   "nitrogen_monoxide", "nitrous_oxide", "ozone", "pm1", "pm10", "pm25", "power_factor", "power",
#                   "pressure", "reactive_power", "signal_strength", "sulphur_dioxide", "temperature", "timestamp",
#                   "volatile_organic_compounds", "voltage")

DEVICE_CLASSES = (
    "ac_frequency",
    "action",
    "action_group",
    "angle",
    "angle_axis",
    "aqi",
    "auto_lock",
    "auto_relock_time",
    "away_mode",
    "away_preset_days",
    "away_preset_temperature",
    "battery",
    "battery_low",
    "battery_voltage",
    "boost_time",
    "button_lock",
    "carbon_monoxide",
    "child_lock",
    "co2",
    "co",
    "comfort_temperature",
    "consumer_connected",
    "contact",
    "cover_position",
    "cover_position_tilt",
    "cover_tilt",
    "cpu_temperature",
    "cube_side",
    "current",
    "current_phase_b",
    "current_phase_c",
    "deadzone_temperature",
    "device_temperature",
    "eco2",
    "eco_mode",
    "eco_temperature",
    "effect",
    "energy",
    "fan",
    "flip_indicator_light",
    "force",
    "formaldehyd",
    "gas",
    "hcho",
    "holiday_temperature",
    "humidity",
    "illuminance",
    "illuminance_lux",
    "brightness_state",
    "keypad_lockout",
    "led_disabled_night",
    "light_brightness",
    "light_brightness_color",
    "light_brightness_colorhs",
    "light_brightness_colortemp",
    "light_brightness_colortemp_color",
    "light_brightness_colortemp_colorhs",
    "light_brightness_colortemp_colorxy",
    "light_brightness_colorxy",
    "light_colorhs",
    "linkquality",
    "local_temperature",
    "lock",
    "lock_action",
    "lock_action_source_name",
    "lock_action_source_user",
    "max_temperature",
    "max_temperature_limit",
    "min_temperature",
    "noise",
    "noise_detected",
    "occupancy",
    "occupancy_level",
    "open_window",
    "open_window_temperature",
    "pm10",
    "pm25",
    "position",
    "power",
    "power_factor",
    "power_apparent",
    "power_on_behavior",
    "power_outage_count",
    "power_outage_memory",
    "presence",
    "pressure",
    "programming_operation_mode",
    "smoke",
    "soil_moisture",
    "sos",
    "sound_volume",
    "switch",
    "switch_type",
    "switch_type_2",
    "tamper",
    "temperature",
    "test",
    "valve_position",
    "valve_switch",
    "valve_state",
    "valve_detection",
    "vibration",
    "voc",
    "voltage",
    "voltage_phase_b",
    "voltage_phase_c",
    "water_leak",
    "warning",
    "week",
    "window_detection",
    "moving",
    "x_axis",
    "y_axis",
    "z_axis",
    "pincode",
    "squawk",
    "state",
)

REDIS_SEPARATOR = ":"
REDIS_PREFIX = "lorabridge:flowman"
REDIS_MSG_PREFIX = "lorabridge:events"


class lbdata_types(IntEnum):
    data = 7
    timesync_req = 1
    system_event = 2
    user_event = 3
    lbflow_digest = 4
    lbdevice_join = 5
    heartbeat = 6
    lbdevice_name = 8


# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    logging.info("Connected with result code " + str(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe(userdata["chirp"] + "+/event/up")


# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    # get payload from chirpstack message
    try:
        lora_payload = base64.b64decode(json.loads(msg.payload)["data"])
        msg_type = lora_payload[0]
        lora_payload = lora_payload[1:]
        print(str(msg_type))
        # topic, data = brotli.decompress(lora_payload).split(b" ", maxsplit=1)
    # KeyError = filter chirpstack garbage
    except (json.decoder.JSONDecodeError, KeyError, IndexError) as err:
        # do nothing if zigbee2mqtt publishes garbage message
        print(json.loads(msg.payload))
        print(err)
        return
    match msg_type:
        # lbdata_types as dict and lbdata_types["data"] is not allowed
        # Any non-dotted identifiers are considered capture patterns - NOT PATTERNS
        # https://stackoverflow.com/a/77694460
        case lbdata_types.data:
            try:
                data = msgpack.loads(lora_payload, strict_map_key=False)
                topic = data[-1]
                del data[-1]
                if isinstance(topic, int):
                    topic = "0x{:016x}".format(topic)
                # topic, data = brotli.decompress(lora_payload).split(b" ", maxsplit=1)
                print(topic)
                print(data)
            except msgpack.UnpackException as err:
                print(json.loads(msg.payload))
                print(err)
                return

            # data = yaml.load(data, Loader=Loader)

            res = {}
            for key, value in data.items():
                try:
                    res[DEVICE_CLASSES[int(key)]] = value
                except ValueError:
                    res[key] = value

            logging.info(
                DEV_MAN_TOPIC + "/data" + " " + str({"type": "data", "data": res, "ieee_id": topic})
            )
            client.publish(
                DEV_MAN_TOPIC + "/data",
                json.dumps({"type": "data", "data": res, "ieee_id": topic}),
            )
        case lbdata_types.timesync_req | lbdata_types.heartbeat:
            print("timesync/heartbeat")
        case lbdata_types.system_event:
            print("system_event")
            print(lora_payload)
            r_client: redis.Redis = userdata["r_client"]
            userdata["r_client"]
            id = str(uuid.uuid4())
            timestamp = time.time()
            r_client.hset(
                REDIS_SEPARATOR.join([REDIS_MSG_PREFIX, "system", id]),
                mapping={
                    "msg": lora_payload.decode(),
                    "timestamp": timestamp,
                    "seen": 0,  # False,
                    "id": id,
                },
            )
            r_client.zadd(
                REDIS_SEPARATOR.join([REDIS_MSG_PREFIX, "system", "msgs"]), mapping={id: timestamp}
            )
        case lbdata_types.user_event:
            print("user_event")
            print(lora_payload)
        case lbdata_types.lbflow_digest:
            print("lbflow_digest")
            id = lora_payload[0]
            hash = lora_payload[1:]

            print(hash)
            print(binascii.hexlify(hash).decode())

            userdata["r_client"].lpush(
                REDIS_SEPARATOR.join([REDIS_PREFIX, "hash-check"]),
                json.dumps({"id": id, "hash": binascii.hexlify(hash).decode()}),
            )
        case lbdata_types.lbdevice_join:
            print("lbdevice_join")
            print(lora_payload)
            dev_key = lora_payload[0]
            # attributes = list(lora_payload[1:])
            attributes = [DEVICE_CLASSES[x] for x in lora_payload[1:]]
            print(str(dev_key))
            print(attributes)
            logging.info(
                DEV_MAN_TOPIC
                + "/join"
                + " "
                + str({"type": "attributes", "attributes": attributes, "lb_id": dev_key})
            )
            client.publish(
                DEV_MAN_TOPIC + "/join",
                json.dumps({"type": "attributes", "attributes": attributes, "lb_id": dev_key}),
            )
        case lbdata_types.lbdevice_name:
            print("lbdevice_name")
            print(lora_payload)
            lb_id = lora_payload[0]
            ieee_id = "0x{:016x}".format(int.from_bytes(lora_payload[1:9], "big"))
            name = lora_payload[9:].decode()
            print(str(lb_id))
            print(ieee_id)
            print(name)
            logging.info(
                DEV_MAN_TOPIC
                + "/name"
                + " "
                + str({"type": "name", "name": name, "lb_id": lb_id, "ieee_id": ieee_id})
            )
            client.publish(
                DEV_MAN_TOPIC + "/name",
                json.dumps({"type": "name", "name": name, "lb_id": lb_id, "ieee_id": ieee_id}),
            )


def main():
    logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    client.connect(MQTT_HOST, MQTT_PORT, 60)
    r_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)
    client.user_data_set({"chirp": CHIRP_TOPIC, "r_client": r_client})

    # Blocking call that processes network traffic, dispatches callbacks and
    # handles reconnecting.
    # Other loop*() functions are available that give a threaded interface and a
    # manual interface.
    client.loop_forever()


if __name__ == "__main__":
    main()
