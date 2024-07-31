#!/usr/bin/env python

from datetime import datetime
import unittest
import pytz
from collections import namedtuple

def parse_header_timestamp(timestamp):
    return datetime.strptime(timestamp, "%a, %d %b %Y %H:%M:%S %Z").replace(tzinfo=pytz.UTC)

def parse_timestamp(timestamp):
    return datetime.fromisoformat(timestamp)

class PredictionSet:
    def __init__(self, data, max = 12):
        self.data = data
        self.max = max

    def __iter__(self):
        self.current = 0
        return self

    def __next__(self):
        if self.current >= self.max or self.current >= len(self.data):
            raise StopIteration
        prediction = self.data[self.current]
        self.current += 1
        return prediction

WeatherData = namedtuple('WeatherData', ['current', 'sequence'])
class wx:
    def __init__(self, json_data, headers):
        self.prediction_data = []
        for obs in json_data['properties']['timeseries']:
            data = obs['data']
            if not 'next_1_hours' in data:
                continue
            instant = data['instant']['details']
            next_h = data['next_1_hours']
            self.prediction_data.append((parse_timestamp(obs['time']),
                                         {
                                             **instant,
                                             **next_h['details'],
                                             **next_h['summary']
                                         }))
        self.prediction_data.sort(key = lambda obs: obs[0])
        expiry_time = headers['expires']
        self.expiry = parse_header_timestamp(expiry_time)

    def next_update(self):
        return self.expiry

    def has_expired(self, now):
        return self.expiry > now

    def predictions(self, now, max = 12):
        current = None
        while len(self.prediction_data) > 0 and self.prediction_data[0][0] < now:
            current = self.prediction_data.pop(0)
        return WeatherData(current, PredictionSet(self.prediction_data))

class Test_wx(unittest.TestCase):
    def test_expiry(self):
        forecast = wx({'properties': { 'timeseries': []}},{'expires': 'Tue, 25 Jun 2024 05:22:48 GMT'})
        self.assertEqual(forecast.next_update(), datetime(2024, 6, 25, 5, 22, 48, 0, pytz.timezone('GMT')))

    def test_predictions(self):
        data = {
            'properties': {
                'timeseries': [
                    {
                        'time': '2024-06-25T04:00:00Z',
                        'data': {
                            'instant': {
                                'details': {
                                    'air_temperature': 21
                                }
                            },
                            'next_1_hours': {
                                'summary': {
                                    'symbol_code': 'clearsky_day'
                                }
                            }
                        }
                    },
                    {
                        'time': '2024-06-25T05:00:00Z',
                        'data': {
                            'instant': {
                                'details': {
                                    'air_temperature': 19
                                }
                            },
                            'next_1_hours': {
                                'summary': {
                                    'symbol_code': 'clearsky_day'
                                }
                            }
                        }
                    },
                    {
                        'time': '2024-06-25T06:00:00Z',
                        'data': {
                            'instant': {
                                'details': {
                                    'air_temperature': 17
                                }
                            },
                            'next_1_hours': {
                                'summary': {
                                    'symbol_code': 'fog'
                                }
                            }
                        }
                    }

                ]
            }
        }
        forecast = wx(data, { 'expires': 'Tue, 25 Jun 2024 05:22:48 GMT'})
        expected = [({'air_temperature': 19}, 'clearsky_day'),
                    ({'air_temperature': 17}, 'fog')]
        idx = 0
        weather = forecast.predictions(datetime(2024, 6, 25, 4, 30, 00, 0, pytz.utc))
        for predictions in weather.sequence:
            self.assertEqual(expected[idx][0], predictions[1])
            self.assertEqual(expected[idx][1], predictions[2])
            idx += 1
        self.assertEqual(idx, 2)

if __name__ == '__main__':
    unittest.main()
