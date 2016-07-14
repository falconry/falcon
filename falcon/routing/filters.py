import re
import uuid

from falcon.errors import HTTPNotFound


class FilterRegistry(object):
    def __init__(self):
        self.registry = {}

        self.register_filter('int', int_filter)
        self.register_filter('float', float_filter)
        self.register_filter('path', path_filter)
        self.register_filter('re', re_filter)
        self.register_filter('uuid', uuid_filter)

    def __getitem__(self, filter_name):
        return self.registry.__getitem__(filter_name)

    def register_filter(self, name, func):
        self.registry[name] = self._wrap_filter(func)

    @staticmethod
    def _wrap_filter(filter_function):
        def wrapped_filter(segments, config=None):
            try:
                num_segments_matched, value = filter_function(segments, config)
                # NOTE(lindseybrockman): Currently only filters that match either the
                # first filtered segment or all the remaining segments are supported
                assert num_segments_matched == 1 or num_segments_matched == len(segments)
            except:
                raise HTTPNotFound()
            else:
                return (num_segments_matched, value)

        return wrapped_filter

def int_filter(segments, config=None):
    return 1, int(segments[0])

def float_filter(segments, config=None):
    return 1, float(segments[0])

def path_filter(segments, config=None):
    config='(^.+)'

    return re_filter(segments, config)

def re_filter(segments, config=None):
    if not config.startswith('(') and not config.endswith(')'):
        config = '({})'.format(config)

    re_config = re.compile(config)
    remaining_url = '/'.join(segments)

    match = re_config.match(remaining_url)

    if match.group() == segments[0]:
        num_segments_matched = 1
    elif match.group() == remaining_url:
        num_segments_matched = len(segments)

    return num_segments_matched, match.groups()

def uuid_filter(segments, config=None):
    return 1, uuid.UUID(segments[0], version=4)
