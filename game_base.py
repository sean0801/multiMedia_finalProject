
class GameBase:
    def __init__(self, name):
        self.name = name

    def handle_event(self, event):
        pass

    def update(self):
        pass

    def render(self, frame):
        pass