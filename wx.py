#!/usr/bin/env python

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

def read_config(name):
    config_file = name if name else './config.json'
    with open(config_file) as config:
        return json.load(config)

def run():

    parser = argparse.ArgumentParser()

    parser.add_argument("--config", type=str, help="configuration file (defaults to ./config.json)")

    args, _ = parser.parse_known_args()

    config = read_config(args.config)

    lat = config['lat']
    long = config['long']
    name = config['placename']

    deadline=datetime.now(tz=pytz.UTC)
    http = urllib3.PoolManager()
    display = auto()
    print('display resolution={}'.format(display.resolution))
    while True:
        #try:
            now=datetime.now(tz=pytz.UTC)
            if now >= deadline:
                response = http.request(method='GET',
                                        url='https://api.met.no/weatherapi/locationforecast/2.0/complete?lat={lat:}&lon={lon:}'.format(lat=lat,lon=long),
                                        headers={"User-Agent": USER_AGENT})
                forecast = wx(response.json(), response.headers)
                deadline = forecast.next_update() + timedelta(minutes=1)
            svg_image = render_hmtl(forecast, now, display.resolution, name)
            png_image = Image.open(io.BytesIO(svg2png(svg_image, unsafe=True,output_width=600, output_height=448)))
            resized_image = png_image.resize(display.resolution)
            display.set_image(resized_image)
            display.show()
            waittime = min(deadline - now, timedelta(hours=1)) if deadline > now else timedelta(seconds=10)
            seconds = waittime.total_seconds()
            sleep(seconds)
        #except:
        #    sleep(20)
    

if __name__ == '__main__':
    run()
