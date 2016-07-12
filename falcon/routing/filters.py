import re
import uuid

from falcon.errors import HTTPNotFound


# TODO: should non-configurable filters be defined in such a way that they do not allow the second param? Or
# should it just be ignored?
def int_filter(segments, config=None):
    try:
        value = int(segments[0])
    except ValueError:
        raise HTTPNotFound()
    else:
        filter_matched = True
        filter_consumed_all_segments = False
        return (filter_matched, filter_consumed_all_segments, value)


def float_filter(segments, config=None):
    try:
        value = float(segments[0])
    except ValueError:
        raise HTTPNotFound()
    else:
        filter_matched = True
        filter_consumed_all_segments = False
        return (filter_matched, filter_consumed_all_segments, value)


def path_filter(segments, config=None):
    config = '^.+'
    re_config = re.compile(config)
    remaining_url = '/'.join(segments)

    first_segment_match = re_config.match(segments[0])
    all_segments_match = re_config.match(remaining_url)

    try:
        assert first_segment_match or all_segments_match
    except AssertionError:
        raise HTTPNotFound()
    else:
        value = all_segments_match or first_segment_match
        filter_matched = True
        filter_consumed_all_segments = bool(all_segments_match)
        return (filter_matched, filter_consumed_all_segments, value)


def re_filter(segments, config=None):
    re_config = re.compile(config)
    remaining_url = '/'.join(segments)

    first_segment_match = re_config.match(segments[0])
    all_segments_match = re_config.match(remaining_url)

    try:
        assert first_segment_match or all_segments_match
    except AssertionError:
        raise HTTPNotFound()
    else:
        value = all_segments_match or first_segment_match
        filter_matched = True
        filter_consumed_all_segments = bool(all_segments_match)
        return (filter_matched, filter_consumed_all_segments, value)


def uuid_filter(segments, config=None):
    try:
        value = uuid.UUID(segments[0], version=4)
    except ValueError:
        raise HTTPNotFound()
    else:
        filter_matched = True
        filter_consumed_all_segments = False
        return (filter_matched, filter_consumed_all_segments, value)


