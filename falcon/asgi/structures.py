from json import dumps as json_dumps


__all__ = ['SSEvent']


class SSEvent:
    __slots__ = [
        'data',
        'text',
        'json',
        'event',
        'event_id',
        'retry',
        'comment',
    ]

    def __init__(
        self,
        data=None,
        text=None,
        json=None,
        event=None,
        event_id=None,
        retry=None,
        comment=None
    ):
        # NOTE(kgriffs): Check up front since this makes it a lot easier
        #   to debug the source of the problem in the app vs. waiting for
        #   an error to be raised from the framework when it calls serialize()
        #   after the fact.

        if data and not isinstance(data, bytes):
            raise TypeError('data must be a byte string')

        if text and not isinstance(text, str):
            raise TypeError('text must be a string')

        if event and not isinstance(event, str):
            raise TypeError('event name must be a string')

        if event_id and not isinstance(event_id, str):
            raise TypeError('event_id must be a string')

        if comment and not isinstance(comment, str):
            raise TypeError('comment must be a string')

        if retry and not isinstance(retry, int):
            raise TypeError('retry must be an int')

        self.data = data
        self.text = text
        self.json = json
        self.event = event
        self.event_id = event_id
        self.retry = retry

        self.comment = comment

    def serialize(self):
        if self.comment is not None:
            block = ': ' + self.comment + '\n'
        else:
            block = ''

        if self.event is not None:
            block += 'event: ' + self.event + '\n'

        if self.event_id is not None:
            # NOTE(kgriffs): f-strings are a tiny bit faster than str().
            block += f'id: {self.event_id}\n'

        if self.retry is not None:
            block += f'retry: {self.retry}\n'

        if self.data is not None:
            # NOTE(kgriffs): While this decode() may seem unnecessary, it
            #   does provide a check to ensure it is valid UTF-8. I'm also
            #   assuming for the moment that most people will not use this
            #   attribute, but rather the text and json ones instead. If that
            #   is true, it makes sense to construct the entire string
            #   first, then encode it all in one go at the end.
            block += 'data: ' + self.data.decode() + '\n'
        elif self.text is not None:
            block += 'data: ' + self.text + '\n'
        elif self.json is not None:
            block += 'data: ' + json_dumps(self.json, ensure_ascii=False) + '\n'

        if not block:
            return b': ping\n\n'

        return (block + '\n').encode()
