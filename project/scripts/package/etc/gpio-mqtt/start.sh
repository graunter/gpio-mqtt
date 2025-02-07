#!/bin/bash

if [ ! -d /var/log/gpio-mqtt ]; then
        mkdir /var/log/gpio-mqtt
        echo "Folder for logs was created"
fi

/opt/gpio-mqtt/gpio-mqtt -v &>> /var/log/gpio-mqtt/gpio-mqtt.log & #> /dev/null 2>&1

echo $! > /var/run/gpio-mqtt.pid
