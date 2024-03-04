#!/bin/python3

import datetime
import sched
import time
import xmlrpc.client
import logging
import requests

flrigServerUrl = 'http://my.flrig.server.de:12345/' # change this
cloudlogUrl = 'https://my.cloudlog.server.de' # change this
cloudlogApiKey = 'MY_CLOUDLOG_API_KEY' # change this
update_delay_seconds = 1

flrigClient = xmlrpc.client.ServerProxy(flrigServerUrl)


class OldData(object):
    def __init__(self):
        self.frequency = ''
        self.mode = ''
        self.power_watts = ''


def do_update(schedule, old_data):
    schedule.enter(update_delay_seconds, 1, do_update, (scheduler, old_data))

    mode = flrigClient.rig.get_mode()

    frequency = flrigClient.rig.get_vfo()
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
    if r.status_code == 200:
        logging.debug('sent data to cloudlog: %s >> %s', r.status_code, data)

    old_data.frequency = frequency
    old_data.mode = mode
    old_data.power_watts = power_watts


logging.basicConfig(filename='cloudlogbridge.log', encoding='utf-8', level=logging.INFO)

oldData = OldData()
scheduler = sched.scheduler(time.time, time.sleep)
scheduler.enter(update_delay_seconds, 1, do_update, (scheduler, oldData))
scheduler.run()
