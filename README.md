# inky-wx

Weather app for [RaspberryPi]() and [Pimoroni](https://shop.pimoroni.com/)
[Inky Impression 5.7"](https://shop.pimoroni.com/products/inky-impression-5-7)
7 colour e-paper display (it may work with other displays but this is not
tested). It uses weather forecast data from
[yr.no](https://api.met.no/weatherapi/locationforecast/2.0/documentation).

Very experimental. Requires a python environment with the Pimoroni Inky
[Python library](https://github.com/pimoroni/inky).
Depending on your raspberry pi version and OS version, you may have to search
forums  to find the right version/branch for you. Other required libraries are
`pytz`, `urllib3`, `cairosvg` and `pillow`

You also need to download [weather icons](https://github.com/metno/weathericons/)
and store them in the directory `weather/svg` relative to the working directory
of the program.

If you fork this to make a new product instead of contributing,
changes/fixes/enhancements, then I urge you to please change the `user_agent`
string in `wx.py` to comply with the `"User-Agent"` header rules, as per the
[terms of service](https://developer.yr.no/doc/TermsOfService/) for the API
from [yr.no](https://yr.no).

Usage:
Create a configuration file named `config.json` in the directory of the python
files. It must contain:

```JSON
{
  "lat": 0.0,                 //<numerical latitude in degrees North in decimal form>
  "long": 0.0,                //<numerical longitude in degrees East in decimal form>,
  "placename": "Null Island"  //<string with the name of the place at the coordinate>
}
```

Example:
```JSON
{
  "lat": 55.60,
  "long": 12.75,
  "placename": "Peberholm"
}
```

The configuration file may in addition contain:
```JSON
{
  "colors": {        // all colours are optional, values shown are the defaults
    "background":    "white",
    "grid":          "black",
    "temperature":   "red",
    "precipitation": "blue",
    "wind":          "black",
    "placename":     "black",
    "hour":          "black"
  }
}
```

Sending a `SIGHUP` to the process causes a re-read of the configuration
