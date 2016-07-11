from falcon.errors import HTTPBadRequest


# TODO: should non-configurable filters be defined in such a way that they do not allow the second param? Or
# should it just be ignored?
def int_filter(segments, filter_config=None):
    try:
        value = int(segments[0])
    except ValueError:
        raise HTTPBadRequest
    else:
        filter_matched = True
        filter_consumed_all_segments = False
        return (filter_matched, filter_consumed_all_segments, value)


def float_filter(segments, filter_config=None):
    try:
        value = float(segments[0])
    except ValueError:
        raise HTTPBadRequest
    else:
        filter_matched = True
        filter_consumed_all_segments = False
        return (filter_matched, filter_consumed_all_segments, value)


def path_filter(segments, filter_config=None):
    pass


def uuid_filter(segments, filter_config=None):
    pass


def re_filter(segments, filter_config=None):
    pass
