#!/bin/bash

/opt/gpio-mqtt/gpio-mqtt -v &>> /var/log/gpio-mqtt/gpio-mqtt.log & #> /dev/null 2>&1

echo $! > /var/run/gpio-mqtt.pid
