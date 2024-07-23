# gpio-mqtt

Сервис для взаимодействия с контактами контроллера


## Установка

### Через центральный репозиторий

1. Обновить индекс - ```apt update```
2. Установить драйвер - ```apt install gpio-mqtt```
3. проверить состояние службы - ```service gpio-mqtt status```

### Из оффлайн пакета

```
dpkg -i gpio-mqtt_<version>_<platform>.deb
```

### Управление сервисом:
```
service gpio-mqtt start    - запустить
service gpio-mqtt stop     - остановить
service gpio-mqtt restart  - перезапустить
service gpio-mqtt status   - статус
```

### Флаги запуска

Параметры командной строки имеют приоритет над всеми остальными настройками

'-a', '--adr-broker' : Адрес машины с Брокером
'-p', '--port-broker': Порт для подключения к Брокеру
'-u', '--user-broker': Имя пользователя для подключения к Брокеру
'-w', '--pass-broker': Пароль пользователя для подключения к Брокеру
-v', '--verbose': Включить вывод отладочных сообщений


## Основные положения по сервису:

Для корректной работы должен быть установлен и сконфигурирован брокер сообщений Mosquitto
<details>

```
sudo apt-add-repository ppa:mosquitto-dev/mosquitto-ppa.
sudo apt-get update.
sudo apt-get install mosquitto.
sudo apt-get install mosquitto-clients.
sudo apt clean
```

или, если пакет имеется в центральном репозитории:
```
sudo apt install -y mosquitto
```

для проверки работоспособности брокера можно выполнить комманду:
```
sudo systemctl status mosquitto
```
примерный вывод должен быть следующий:
```
● mosquitto.service - Mosquitto MQTT Broker
     Loaded: loaded (/lib/systemd/system/mosquitto.service; enabled; vendor pre>
     Active: active (running) since Tue 2024-05-07 14:02:34 +06; 1 day 3h ago
       Docs: man:mosquitto.conf(5)
             man:mosquitto(8)
   Main PID: 994 (mosquitto)
      Tasks: 1 (limit: 38373)
     Memory: 3.3M
        CPU: 35.176s
     CGroup: /system.slice/mosquitto.service
             └─994 /usr/sbin/mosquitto -c /etc/mosquitto/mosquitto.conf

мая 07 14:02:33 toor-SS systemd[1]: Starting Mosquitto MQTT Broker...
мая 07 14:02:34 toor-SS mosquitto[994]: 1715068954: Loading config file /etc/mo>
мая 07 14:02:34 toor-SS systemd[1]: Started Mosquitto MQTT Broker.
```
</details>


## Сборка пакета:

### Для инсталлятора в виде исполняемых файлов

- перейти в папку 'project/scripts'
- запустить скрипт build.sh с параметрами
    - адрес машины для сборки
    - порт для подключения ssh
    - пароль пользователя 
    - имя пользователя (с правами root)


пример:
```
cd project/scripts
./build.sh 192.168.1.100 22 test root
```

### Тестирование перед сборкой

Для запуска встроенных тестов может быть использована комманда:
```
python3 -m pytest
```

## Использование и настройка

### Модель поведения
TODO

### Настроечные файлы
Конфигурационные файлы (в папках `opt`, `etc` и `home` - `/gpio-mqtt`) - при старте сервиса - объединяются на основе своего содержимого. Благодаря этому имеется возможность перезаписать любое значение настроек без дополнительных прав доступа.




