#!/bin/python3

import datetime
import logging
import sched
import socket
import time
import xmlrpc.client

import requests

flrigServerUrl = 'http://my.flrig.server.de:12345/'  # change this
cloudlogUrl = 'https://my.cloudlog.server.de'  # change this
cloudlogApiKey = 'MY_CLOUDLOG_API_KEY'  # change this
update_delay_seconds = 1

flrigClient = xmlrpc.client.ServerProxy(flrigServerUrl)


class OldData(object):
    def __init__(self):
        self.frequency = ''
        self.mode = ''
        self.power_watts = ''


def do_update(schedule, old_data):
    schedule.enter(update_delay_seconds, 1, do_update, (scheduler, old_data))

    try:
        frequency = flrigClient.rig.get_vfo()
        mode = flrigClient.rig.get_mode()
        mode = map_mode(mode, frequency)
        power_watts = flrigClient.rig.get_power()

        if frequency == old_data.frequency and mode == old_data.mode and old_data.power_watts == power_watts:
            logging.debug('no update needed')
            return

        trxname = flrigClient.rig.get_xcvr()
        timestamp = datetime.datetime.now().strftime('%Y/%m/%d %H:%M')

        data = {
            "key": cloudlogApiKey,
            "radio": trxname,
            "frequency": str(frequency),
            "power": str(power_watts),
            "mode": mode,
            "timestamp": timestamp
        }

        r = requests.post(cloudlogUrl + '/api/radio', json=data)
        r.raise_for_status()

        logging.info('sent data to cloudlog: %s >> %s', r.status_code, data)

        old_data.frequency = frequency
        old_data.mode = mode
        old_data.power_watts = power_watts

    except requests.exceptions.HTTPError as e:
        logging.error("send data to cloudlog failed: [%s] %s", e.response.status_code, e.response.text)
    except socket.error as e:
        logging.error("receive data from flrig failed")


def map_mode(mode, frequency):
    u_mode = mode.upper()
    if u_mode.startswith('RTTY'):
        return 'RTTY'
    if u_mode.startswith('DATA'):
        match frequency:
            case '1840000' | '3573000' | '7074000' | '14074000' | '21140000' | '28074000' | '144174000' | '432174000' | '432500000' | '1296174000':
                return 'FT8'
            case '3575000' | '7047500' | '14080000' | '21140000' | '28180000' | '144120000' | '144170000' | '432065000' | '1296065000':
                return 'FT4'

        return 'DATA'

    index = u_mode.find('-')
    if index == -1:
        return u_mode
    return u_mode[0:index - 1]


logging.basicConfig(filename='flrig2cloudlog.log', encoding='utf-8', level=logging.INFO)

oldData = OldData()
scheduler = sched.scheduler(time.time, time.sleep)
scheduler.enter(update_delay_seconds, 1, do_update, (scheduler, oldData))
scheduler.run()
