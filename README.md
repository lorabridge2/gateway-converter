# Gateway Converter

This repository is part of the [LoRaBridge](https://github.com/lorabridge2/lorabridge) project.  
It provides the docker image for the converter software used on our gateway device.  

The Converter is a self-provided Python3 application, which listens for the device data published by the ChirpStack Gateway Bridge via MQTT message on the Mosquitto. 
It decompresses the data, undoes the key substitution and reformats the data. 
Afterwards, the data is published back to the Mosquitto server with a custom MQTT topic. 
This behaviour allows easy creation of plugins for transforming the data in order to integrate other webinterfaces or similar.

## Environment Variables
- `CON_MQTT_HOST`: IP or hostname of MQTT host
- `CON_MQTT_PORT`: Port used by MQTT
- `CON_MQTT_USERNAME`: MQTT username if used (can be a file as well)
- `CON_MQTT_PASSWORD`: MQTT password if used (can be a file as well)
- `DEV_EUI`: Device eui of bridge
- `REDIS_HOST`: IP or hostname of Redis host
- `REDIS_PORT`: Port used by Redis
- `REDIS_DB`: Number of the database used inside Redis


## License

All the LoRaBridge software components and the documentation are licensed under GNU General Public License 3.0.

## Acknowledgements

The financial support from Internetstiftung/Netidee is gratefully acknowledged. The mission of Netidee is to support development of open-source tools for more accessible and versatile use of the Internet in Austria.
