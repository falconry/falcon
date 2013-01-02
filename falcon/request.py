class Request:
    __slots__ = ('path')

    def __init__(self, path):
        self.path = path