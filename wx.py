#!/usr/bin/env python
import traceback
import signal
import syslog
from time import sleep
import pytz
from wx_data import wx
from render_html import render_hmtl
from datetime import datetime, timedelta
import urllib3
from cairosvg import svg2png
from PIL import Image
from inky.auto import auto
import argparse
import io
import json

USER_AGENT='rollbear inky wx https://github.com/rollbear/inky-wx'

def str2loglevel(name: str):
    if name == 'WARNING':
        return syslog.LOG_WARNING
    if name == 'ERROR':
        return syslog.LOG_ERR
    if name == 'CRITICAL':
        return syslog.LOG_CRIT
    if name == 'INFO':
        return syslog.LOG_INFO
    if name == 'DEBUG':
        return syslog.LOG_DEBUG


class wakeup(BaseException):
    pass

def sighup_handler(signum, frame):
    raise wakeup

def read_config(name):
    config_file = name if name else './config.json'
    with open(config_file) as config:
        conf = json.load(config)
        return conf

def run():

    pending_config = True

    signal.signal(signal.SIGHUP, sighup_handler)

    parser = argparse.ArgumentParser()

    parser.add_argument("--config", type=str, help="configuration file (defaults to ./config.json)")

    args, _ = parser.parse_known_args()

    lat = 0
    long = 0

    loglevel = syslog.LOG_INFO
    syslog.openlog()
    syslog.setlogmask(syslog.LOG_MASK(loglevel))

    syslog.syslog(syslog.LOG_INFO, "Starting")

    deadline=datetime.now(tz=pytz.UTC)
    http = urllib3.PoolManager()
    display = auto()
    while True:
        try:
            new_location = False
            if pending_config:
                syslog.syslog(syslog.LOG_INFO, "Reading configuration")
                config = read_config(args.config)

                old_lat = lat
                old_long = long

                lat = config['lat']
                long = config['long']
                name = config['placename']

                old_loglevel = loglevel
                loglevel = str2loglevel(config.get('loglevel', 'INFO'))
                if old_loglevel != loglevel:
                    syslog.setlogmask(syslog.LOG_MASK(loglevel))

                new_location = old_lat != old_lat or long != old_long

                colors = config.get('colors', {})
                pending_config = False

            now=datetime.now(tz=pytz.UTC)
            if now >= deadline or new_location:
                try:
                    syslog.syslog(syslog.LOG_INFO, "Get data for location lat={lat:}, long={long:}".format(lat=lat,long=long))
                    response = http.request(method='GET',
                                            url='https://api.met.no/weatherapi/locationforecast/2.0/complete?lat={lat:}&lon={lon:}'.format(lat=lat,lon=long),
                                            headers={"User-Agent": USER_AGENT})
                except Exception as e:
                    syslog.syslog(syslog.LOG_ERROR, "Failed to get data, err={}", e)
                else:
                    forecast = wx(response.json(), response.headers)
                    deadline = forecast.next_update() + timedelta(minutes=1)
            syslog.syslog(syslog.LOG_INFO, "Render new image")
            svg_image = render_hmtl(forecast, now, display.resolution, name, colors)
            png_image = Image.open(io.BytesIO(svg2png(svg_image, unsafe=True,output_width=600, output_height=448)))
            resized_image = png_image.resize(display.resolution)
            display.set_image(resized_image)
            display.show()
            next_hour = now.replace(hour=now.hour+1, minute=0, second=0)
            waittime = min(deadline - now, next_hour - now) if deadline > now else timedelta(seconds=10)
            seconds = waittime.total_seconds()
            try:
                sleep(seconds)
            except wakeup:
                pending_config = True
                continue
        except Exception as e:
            syslog.syslog(syslog.LOG_ERR, "Caught exception {}".format(e))
            for line in traceback.format_exception(e):
                syslog.syslog(syslog.LOG_ERR, line)
            sleep(20)
    

if __name__ == '__main__':
    run()
