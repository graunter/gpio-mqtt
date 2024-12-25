import logging
import paho.mqtt.client as mqtt

LoggerClient = None
logger_global_topic = 'app/log'
logger_localal_topic = 'app/gpio-mqtt/log'

def LinkLoggerToBroker(client: mqtt.Client):
    global LoggerClient
    LoggerClient = client

def log_inf(msg, *args, **kwargs):

    logging.debug(msg, *args, **kwargs)

    if LoggerClient:
        LoggerClient.publish( f'{logger_global_topic}/I', str(msg))
        LoggerClient.publish( f'{logger_localal_topic}/I', f'gpio-mqtt: {str(msg)}')
        LoggerClient.publish( f'{logger_global_topic}/A', f'gpio-mqtt inf: {str(msg)}')
    
def log_dbg(msg, *args, **kwargs):

    logging.debug(msg, *args, **kwargs)

    if LoggerClient:
        LoggerClient.publish( f'{logger_global_topic}/D', str(msg))
        LoggerClient.publish( f'{logger_localal_topic}/D', f'gpio-mqtt: {str(msg)}')
        LoggerClient.publish( f'{logger_global_topic}/A', f'gpio-mqtt dbg: {str(msg)}')

def log_err(msg, *args, **kwargs):

    logging.debug(msg, *args, **kwargs)

    if LoggerClient:
        LoggerClient.publish( f'{logger_global_topic}/E', str(msg))
        LoggerClient.publish( f'{logger_localal_topic}/E', f'gpio-mqtt: {str(msg)}')      
        LoggerClient.publish( f'{logger_global_topic}/A', f'gpio-mqtt err: {str(msg)}')  