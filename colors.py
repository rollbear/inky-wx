class colors:
    def __init__(self, settings):
        self.background = settings.get('background', 'white')
        self.grid = settings.get('grid', 'black')
        self.temperature = settings.get('temperature', 'red')
        self.precipitation = settings.get('precipitation', 'blue')
        self.wind = settings.get('wind', 'black')
        self.placename = settings.get('placename', 'black')
        self.hour = settings.get('hour', 'black')
