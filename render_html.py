#!/usr/bin/env python

import pytz

import wx_data
from datetime import datetime, timedelta
import math
from cairosvg import svg2png
import os

def windbarb(mps, direction, pos_x, pos_y, scale):
    color = 'black'
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

def render_hmtl(forecast: wx_data, now: datetime, resolution, place: str):
    homedir=os.getcwd()
    width = resolution[0]
    height = resolution[1]
    top_margin = height/4.5
    bottom_margin = height/15
    left_margin = width/15
    right_margin = width/60

    graph_width = width - left_margin - right_margin
    graph_height = height - top_margin - bottom_margin

    image=''
    observations = forecast.observations(now)
    min_temp = 10000
    max_temp = -10000
    time=None
    for obs in observations.sequence:
        if time == None:
            time = obs[0].astimezone()
        temp = obs[1]['air_temperature']
        min_temp = min(min_temp, math.floor(temp))
        max_temp = max(max_temp, math.ceil(temp))
    image+='  <svg height="{}" width="{}" xmlns="http://www.w3.org/2000/svg">\n'.format(height, width)
    symbol_color = 'black'
    background_color = 'white'
    red = 'red'
    image += '    <path d="M {left:} {top:} L {right:} {top:} L {right:} {bottom:} L {left:} {bottom:} Z" style="fill:{color:}"/>'.format(top=0, left=0, right=width, bottom=height, color=background_color)
    image += '    <path d="M {left:} {top:} L {right:} {top:} L {right:} {bottom:} L {left:} {bottom:} Z" style="fill:none;stroke:blue;stroke-width:1"/>\n'.format(left=left_margin, top=top_margin, right=width-right_margin, bottom=height-bottom_margin)
    h2x = lambda h : h*graph_width/11+left_margin
    for h in range(12):
        x=h2x(h)
        image+='    <text x="{x:}" y="{top:}" fill="{color:}">{h:}</text>\n'.format(x=x-10, top=top_margin-5, h=datetime.strftime(time + timedelta(hours=h), "%H"), color=symbol_color)
        if h > 0 and h < 11:
            image+='    <line x1="{x:}" y1="{top:}" x2="{x:}" y2="{bottom:}" style="stroke:blue;stroke-width:1"/>\n'.format(x=x, top=top_margin, bottom=height-bottom_margin)
    temp_range = max_temp - min_temp
    temp2y = lambda temp: height - bottom_margin - graph_height/temp_range*(temp-min_temp)
    for t in range(min_temp, max_temp):
        y = temp2y(t)
        image+='    <line x1="{left:}" y1="{y:}" x2="{right:}" y2="{y:}" style="stroke:blue;stroke-width:1"/>\n'.format(y=y, left=left_margin, right=width-right_margin)
        image+='    <text x="2" y="{y:}" fill="{color:}">{text:}°</text>\n'.format(y=y, text=t, color=symbol_color)
    h=0
    for obs in observations.sequence:
        temp = obs[1]['air_temperature']
        y=temp2y(temp)
        if h > 0:
            image+= '    <line x1="{prevx:}" y1="{prevy:}" x2="{x:}" y2="{y:}" style="stroke:{red:};stroke-width:4"/>\n'.format(prevx=h2x(h-1), prevy=temp2y(prev_temp), x=h2x(h), y=y, red=red)
        icony = y - 35 if y > height/2 else y + 15
        image+= '    <image width="30" height="30" x="{x:}" y="{y:}" href="{ref:}"/>\n'.format(x=h2x(h)-15, y=icony, ref='file:{}/weather/svg/{}.svg'.format(homedir, obs[2]))
        image +='    {}\n'.format(windbarb(
            obs[1]['wind_speed'],
            obs[1]['wind_from_direction'],
            h2x(h)-2,
            height-bottom_margin+14,
            scale=0.4
        ))
        h+= 1
        prev_temp = temp
    image+='    <image height="55" width="55" x="5" y="5" href="file:{}/weather/svg/{}.svg"/>\n'.format(homedir, observations.current[2])
    image+='    <text x="70" y="55" fill="{red:}" font-size="55">{}°C</text>\n'.format(observations.current[1]['air_temperature'], red=red)
    image+='    {}\n'.format(windbarb(
        observations.current[1]['wind_speed'],
        observations.current[1]['wind_from_direction'],
        300, 35, 0.8))
    image+= '    <text x="350" y="55" fill="{color:}" font-size="40">{place:}</text>\n'.format(color=symbol_color, place=place)
    image+='  </svg>\n'
    return image

if __name__ == '__main__':
    img='<svg height="448" width="600" xmlns="http://www.w3.org/2000/svg">\n'
    for kts in range(110):
        x = (kts % 20) * 30 + 10
        y = math.floor(kts / 20)*4*20+10
        img+='<text x="{x:}" y="{y:}">{msg:}</text>\n'.format(x=x,y=y,msg=kts)
        img+=windbarb(kts*1852/3600, 0, x,y+30, 0.7)
    img+='</svg>\n'
    f = open('barbs.svg','w')
    f.write(img)
    f.close()

    #obs_data = json.load(open('/home/bjorn/compact_stugan.json')) #solna_yr.json'))
    #headers = { 'expires': 'Tue, 25 Jun 2024 05:22:48 GMT' }
    #forecast = wx_data.wx(obs_data, headers)
    #now = datetime.now(pytz.UTC)#fromisoformat('2024-06-25T09:00:00Z')
    #image = render_hmtl(forecast, now, "Bredsättra")
    #svg2png(image, unsafe=True, output_width=600, output_height=448, write_to='/tmp/stugan.png')
