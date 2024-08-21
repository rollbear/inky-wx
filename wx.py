#!/usr/bin/env python
import traceback
import signal
import syslog
from time import sleep
import pytz
from wx_data import wx
import render_svg
from datetime import datetime, timedelta
import urllib3
from cairosvg import svg2png
from PIL import Image
from inky.auto import auto
import argparse
import io
import json
from colors import colors

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

def str2display_color(name: str, display):
    if name == 'black':
        return display.BLACK
    if name == 'white':
        return display.WHITE
    if name == 'blue':
        return display.BLUE
    if name == 'green':
        return display.GREEN
    if name == 'orange':
        return display.ORANGE
    if name == 'red':
        return display.RED
    if name == 'yellow':
        return display.YELLOW

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
    renderer = None
    color_settings = None
    while True:
        try:
            new_location = False
            if renderer == None:
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

                color_settings = colors(config.get('colors', {}))
                renderer = render_svg.renderer(display.resolution, name, color_settings)

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
            svg_image = renderer.render_svg(forecast, now)
            png_image = Image.open(io.BytesIO(svg2png(svg_image, unsafe=True,output_width=600, output_height=448)))
            resized_image = png_image.resize(display.resolution)
            display.set_image(resized_image)
            border_color = str2display_color(color_settings.background, display)
            display.set_border(border_color)
            display.show()
            next_hour = now.replace(minute=0, second=0) + timedelta(hours=1)
            waittime = min(deadline - now, next_hour - now) if deadline > now else timedelta(seconds=10)
            seconds = waittime.total_seconds()
            sleep(seconds)

        except wakeup:
            renderer = None

        except Exception as e:
            syslog.syslog(syslog.LOG_ERR, "Caught exception {}".format(e))
            for line in traceback.format_exception(e):
                syslog.syslog(syslog.LOG_ERR, line)
            sleep(20)
    

if __name__ == '__main__':
    run()
