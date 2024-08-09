#!/usr/bin/env python

import pytz

import wx_data
from datetime import datetime, timedelta
import math
from cairosvg import svg2png
import os

def windbarb(mps, direction, pos_x, pos_y, scale, color):
    knots = round(mps*3600/1852)
    if knots <= 2:
        return '<circle r="{r:}" fill="none" style="stroke:{color:};stroke-width:2" transform="translate({x:} {y:})"/>'.format(x=pos_x,y=pos_y, r=32*scale, color=color)
    path="M-5 27 L0 32 L5 27 M0 32 L0 -32"
    base_y = -32
    delta_y = 12
    while knots >= 48:
        path+= " M0 {b1:} L20 {b2:} L0 {b3:} Z".format(b1=base_y,b2=base_y+5,b3=base_y+10)
        base_y+= delta_y
        knots -= 50
    while knots >= 8:
        path+= " M0 {b2:} L20 {b1:}".format(b1=base_y, b2=base_y + 5)
        knots-= 10
        delta_y = 9
        base_y+= delta_y
    while knots > 2:
        path+= " M0 {b2} L10 {b1:}".format(b1=base_y+2,b2=base_y+5)
        knots-= 5
        delta_y = 9
        base_y+= delta_y
    return '<path d="{path:}" style="stroke:{color:};stroke-width:3" transform="translate({x:} {y:}) rotate({direction:}) scale({scale:})"/>'.format(path=path, x=pos_x, y=pos_y, direction=direction, scale=scale, color=color)

class renderer:
    def __init__(self, resolution, place, colors):
        self.homedir=os.getcwd()
        self.width = resolution[0]
        self.height = resolution[1]
        self.top_margin = self.height/4.5
        self.bottom_margin = self.height/15
        self.left_margin = self.width/15
        self.right_margin = self.width/12

        self.color_background = colors.get('background','white')
        self.color_grid = colors.get('grid', 'black')
        self.color_temperature = colors.get('temperature', 'red')
        self.color_precipitation = colors.get('precipitation', 'blue')
        self.color_wind = colors.get('wind', 'black')
        self.color_placename = colors.get('placename', 'black')
        self.color_hour = colors.get('hour', 'black')

        self.graph_width = self.width - self.left_margin - self.right_margin
        self.graph_height = self.height - self.top_margin - self.bottom_margin

        self.hour_width = self.graph_width/12

        self.place = place

    def _get_limits(self, predictions):

        min_temp = 10000
        max_temp = -10000
        max_rain = 0
        time=None
        for prediction in predictions.sequence:
            if time == None:
                time = prediction[0].astimezone()
            temp = prediction[1]['air_temperature']
            min_temp = min(min_temp, math.floor(temp))
            max_temp = max(max_temp, math.ceil(temp))
            max_rain = max(max_rain, math.ceil(prediction[1]['precipitation_amount_max']))
        temp_range = max_temp - min_temp
        rain_multipliers = [0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50]
        rain_multiplier = 1
        for multiplier in rain_multipliers:
            if max_rain * multiplier > temp_range:
                break
            rain_multiplier = multiplier

        self.temp_range = temp_range
        self.rain_multiplier = rain_multiplier
        self.min_temp = min_temp
        self.max_temp = max_temp
        self.predictions = predictions

    def h2x(self, h: float):
        return h*self.graph_width/11+self.left_margin

    def temp2y(self, temp: float):
        return self.height - self.bottom_margin - self.graph_height/self.temp_range * (temp - self.min_temp)

    def rain2y(self, mm: float):
        return self.temp2y(mm * self.rain_multiplier + self.min_temp)

    def _render_background(self):
        return '    <path d="M {left:} {top:} L {right:} {top:} L {right:} {bottom:} L {left:} {bottom:} Z" style="fill:{color:}"/>'.format(
            top=0,
            left=0,
            right=self.width,
            bottom=self.height,
            color=self.color_background)

    def _render_grid(self, time: datetime):
        grid = ''
        grid += '    <path d="M {left:} {top:} L {right:} {top:} L {right:} {bottom:} L {left:} {bottom:} Z" style="fill:none;stroke:{color:};stroke-width:1"/>\n'.format(
            left=self.left_margin,
            top=self.top_margin,
            right=self.width - self.right_margin,
            bottom=self.height - self.bottom_margin,
            color=self.color_grid)
        for prediction in self.predictions.sequence:
            time = prediction.timestamp.astimezone()
            break
        for h in range(12):
            x=self.h2x(h)
            grid+='    <text x="{x:}" y="{top:}" fill="{color:}">{h:}</text>\n'.format(
                x=x-10,
                top=self.top_margin-5,
                h=datetime.strftime(time + timedelta(hours=h), "%H"),
                color=self.color_hour)

            if h > 0 and h < 11:
                grid+='    <line x1="{x:}" y1="{top:}" x2="{x:}" y2="{bottom:}" style="stroke:{color:};stroke-width:1"/>\n'.format(
                    x=x,
                    top=self.top_margin,
                    bottom=self.height-self.bottom_margin,
                    color=self.color_grid)

        for t in range(self.min_temp, self.max_temp):
            y = self.temp2y(t)
            grid+='    <line x1="{left:}" y1="{y:}" x2="{right:}" y2="{y:}" style="stroke:{color:};stroke-width:1"/>\n'.format(
                y=y,
                left=self.left_margin,
                right=self.width-self.right_margin,
                color=self.color_grid)

            grid+='    <text x="2" y="{y:}" fill="{color:}">{text:}°</text>\n'.format(
                y=y,
                text=t,
                color=self.color_temperature)

        for y in range(self.temp_range):
            mm=round(y/self.rain_multiplier)
            grid+='    <text x="{x:}" y="{y:}" fill="{color:}">{text:}mm</text>\n'.format(
                y=self.rain2y(mm),
                x=self.width - self.right_margin + 3,
                text=mm,
                color=self.color_precipitation)

        return grid

    def render_precipitation(self):
        graph=''
        h=0
        prev_precipitation_expected = 0
        prev_precipitation_min = 0
        for prediction in self.predictions.sequence:
            temp = prediction.data['air_temperature']
            y=self.temp2y(temp)
            precipitation_min = prediction.data['precipitation_amount_min']
            precipitation_expected = prediction.data['precipitation_amount']
            precipitation_max = prediction.data['precipitation_amount_max']
            if precipitation_max > 0:
                graph+= '    <path d="M {left:} {top:} L {right:} {top:} M {x:} {top:} L {x:} {bottom:} M {left:} {bottom:} L {right:} {bottom:} M {left:} {y:} L {right:} {y:}" style="stroke:{color:};stroke-width:3"/>\n'.format(
                    left=self.h2x(h) - 3,
                    right=self.h2x(h) + 3,
                    x=self.h2x(h),
                    top=self.rain2y(precipitation_max),
                    bottom=self.rain2y(precipitation_min),
                    y=self.rain2y(precipitation_expected),
                    color=self.color_precipitation)
                if prev_precipitation_expected > 0 or precipitation_expected > 0:
                    graph+= '    <path d="M {prev_x:} {prev_ymin:} L {prev_x:} {prev_y:} L {x:} {y:} L {x:} {ymin} Z" style="stroke:{color:};stroke-width:1;fill:{color:};fill-opacity:0.5"/>\n'.format(
                        prev_x=self.h2x(h - 1),
                        prev_ymin=self.rain2y(prev_precipitation_min),
                        prev_y=self.rain2y(prev_precipitation_expected),
                        x=self.h2x(h),
                        y=self.rain2y(precipitation_expected),
                        ymin=self.rain2y(precipitation_min),
                        color=self.color_precipitation
                    )
                if prev_precipitation_min > 0 or precipitation_min > 0:
                    graph+= '    <path d="M {prev_x:} {ymin:} L {prev_x:} {prev_y:} L {x:} {y:} L {x:} {ymin:} Z" style="stroke:{color:};stroke-width:1;fill:{color:}"/>\n'.format(
                        ymin=self.rain2y(0),
                        prev_x=self.h2x(h-1),
                        prev_y=self.rain2y(prev_precipitation_min),
                        x=self.h2x(h),
                        y=self.rain2y(precipitation_min),
                        color=self.color_precipitation
                    )
            prev_precipitation_min = precipitation_min
            prev_precipitation_expected = precipitation_expected
            h += 1
        return graph

    def render_temperature(self):
        graph = ''
        h=0
        for prediction in self.predictions.sequence:
            temp = prediction.data['air_temperature']
            y = self.temp2y(temp)
            if h > 0:
                graph+= '    <line x1="{prevx:}" y1="{prevy:}" x2="{x:}" y2="{y:}" style="stroke:{color:};stroke-width:4"/>\n'.format(
                    prevx=self.h2x(h-1),
                    prevy=prev_y,
                    x=self.h2x(h),
                    y=y,
                    color=self.color_temperature)
            prev_y = y
            h += 1

        return graph

    def render_sky_icons(self):
        icons = ''
        h=0
        for prediction in self.predictions.sequence:
            y = self.temp2y(prediction.data['air_temperature'])
            h += 1
            icony = y - 1.5*self.hour_width if y > self.height/2 else y + self.hour_width
            icons+= '    <image width="{size:}" height="{size:}" x="{x:}" y="{y:}" href="{ref:}"/>\n'.format(
                x=self.h2x(h)-self.hour_width/2,
                y=icony,
                size=self.hour_width,
                ref='file:{}/weather/svg/{}.svg'.format(self.homedir, prediction.data['symbol_code']))
        return icons

    def render_wind(self):
        icons = ''
        h=0
        for prediction in self.predictions.sequence:
            icons +='    {}\n'.format(windbarb(
                prediction.data['wind_speed_percentile_90'],
                prediction.data['wind_from_direction'],
                self.h2x(h) - 2,
                self.height - self.bottom_margin + 14,
                scale=0.4,
                color=self.color_wind
            ))
            h+= 1
        return icons

    def render_header(self):
        header = ''
        header+='    <image height="60" width="60" x="5" y="5" href="file:{}/weather/svg/{}.svg"/>\n'.format(
            self.homedir,
            self.predictions.current.data['symbol_code'])
        header+='    <text x="70" y="55" fill="{color:}" font-size="55">{}°C</text>\n'.format(
            self.predictions.current.data['air_temperature'],
            color=self.color_temperature)
        header+='    {}\n'.format(windbarb(
            self.predictions.current.data['wind_speed_percentile_90'],
            self.predictions.current.data['wind_from_direction'],
            300, 35, 0.8, color=self.color_wind))
        header+= '    <text x="350" y="55" fill="{color:}" font-size="40">{place:}</text>\n'.format(
            color=self.color_placename,
            place=self.place)
        return header

    def render_svg(self, forecast: wx_data, now: datetime):
        self._get_limits(forecast.predictions(now))
        image ='  <svg height="{}" width="{}" xmlns="http://www.w3.org/2000/svg">\n'.format(self.height, self.width)
        image += self._render_background()
        image += self.render_precipitation()
        image += self.render_temperature()
        image += self._render_grid(now)
        image += self.render_sky_icons()
        image += self.render_wind()
        image += self.render_header()
        image+='  </svg>\n'
        return image


if __name__ == '__main__':
    img='<svg height="448" width="600" xmlns="http://www.w3.org/2000/svg">\n'
    for kts in range(110):
        x = (kts % 20) * 30 + 10
        y = math.floor(kts / 20)*4*20+10
        img+='<text x="{x:}" y="{y:}">{msg:}</text>\n'.format(x=x,y=y,msg=kts)
        img+=windbarb(kts*1852/3600, 0, x,y+30, 0.7, color='black')
    img+='</svg>\n'
    f = open('barbs.svg','w')
    f.write(img)
    f.close()
