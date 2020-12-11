import cgi

__version__ = '1.6.0'
__author__ = 'Joe Gregorio'
__email__ = 'joe@bitworking.org'
__license__ = 'MIT License'
__credits__ = ''


class MimeTypeParseException(ValueError):
    pass


def parse_mime_type(mime_type):
    """Parses a mime-type into its component parts.

    Carves up a mime-type and returns a tuple of the (type, subtype, params)
    where 'params' is a dictionary of all the parameters for the media range.
    For example, the media range 'application/xhtml;q=0.5' would get parsed
    into:

       ('application', 'xhtml', {'q', '0.5'})

    :rtype: (str,str,dict)
    """
    full_type, params = cgi.parse_header(mime_type)
    # Java URLConnection class sends an Accept header that includes a
    # single '*'. Turn it into a legal wildcard.
    if full_type == '*':
        full_type = '*/*'

    type_parts = full_type.split('/') if '/' in full_type else None
    if not type_parts or len(type_parts) > 2:
        raise MimeTypeParseException(
            "Can't parse type \"{}\"".format(full_type))

    (type, subtype) = type_parts

    return (type.strip(), subtype.strip(), params)


def parse_media_range(range):
    """Parse a media-range into its component parts.

    Carves up a media range and returns a tuple of the (type, subtype,
    params) where 'params' is a dictionary of all the parameters for the media
    range.  For example, the media range 'application/*;q=0.5' would get parsed
    into:

       ('application', '*', {'q', '0.5'})

    In addition this function also guarantees that there is a value for 'q'
    in the params dictionary, filling it in with a proper default if
    necessary.

    :rtype: (str,str,dict)
    """
    (type, subtype, params) = parse_mime_type(range)
    params.setdefault('q', params.pop('Q', None))  # q is case insensitive
    try:
        if not params['q'] or not 0 <= float(params['q']) <= 1:
            params['q'] = '1'
    except ValueError:  # from float()
        params['q'] = '1'

    return (type, subtype, params)


def quality_and_fitness_parsed(mime_type, parsed_ranges):
    """Find the best match for a mime-type amongst parsed media-ranges.

    Find the best match for a given mime-type against a list of media_ranges
    that have already been parsed by parse_media_range(). Returns a tuple of
    the fitness value and the value of the 'q' quality parameter of the best
    match, or (-1, 0) if no match was found. Just as for quality_parsed(),
    'parsed_ranges' must be a list of parsed media ranges.

    :rtype: (float,int)
    """
    best_fitness = -1
    best_fit_q = 0
    (target_type, target_subtype, target_params) = \
        parse_media_range(mime_type)

    for (type, subtype, params) in parsed_ranges:

        # check if the type and the subtype match
        type_match = (
            type in (target_type, '*') or
            target_type == '*'
        )
        subtype_match = (
            subtype in (target_subtype, '*') or
            target_subtype == '*'
        )

        # if they do, assess the "fitness" of this mime_type
        if type_match and subtype_match:

            # 100 points if the type matches w/o a wildcard
            fitness = type == target_type and 100 or 0

            # 10 points if the subtype matches w/o a wildcard
            fitness += subtype == target_subtype and 10 or 0

            # 1 bonus point for each matching param besides "q"
            param_matches = sum([
                1 for (key, value) in target_params.items()
                if key != 'q' and key in params and value == params[key]
            ])
            fitness += param_matches

            # finally, add the target's "q" param (between 0 and 1)
            fitness += float(target_params.get('q', 1))

            if fitness > best_fitness:
                best_fitness = fitness
                best_fit_q = params['q']

    return float(best_fit_q), best_fitness


def quality_parsed(mime_type, parsed_ranges):
    """Find the best match for a mime-type amongst parsed media-ranges.

    Find the best match for a given mime-type against a list of media_ranges
    that have already been parsed by parse_media_range(). Returns the 'q'
    quality parameter of the best match, 0 if no match was found. This function
    behaves the same as quality() except that 'parsed_ranges' must be a list of
    parsed media ranges.

    :rtype: float
    """

    return quality_and_fitness_parsed(mime_type, parsed_ranges)[0]


def quality(mime_type, ranges):
    """Return the quality ('q') of a mime-type against a list of media-ranges.

    Returns the quality 'q' of a mime-type when compared against the
    media-ranges in ranges. For example:

    >>> quality('text/html','text/*;q=0.3, text/html;q=0.7,
                  text/html;level=1, text/html;level=2;q=0.4, */*;q=0.5')
    0.7

    :rtype: float
    """
    parsed_ranges = [parse_media_range(r) for r in ranges.split(',')]

    return quality_parsed(mime_type, parsed_ranges)


def best_match(supported, header):
    """Return mime-type with the highest quality ('q') from list of candidates.

    Takes a list of supported mime-types and finds the best match for all the
    media-ranges listed in header. The value of header must be a string that
    conforms to the format of the HTTP Accept: header. The value of 'supported'
    is a list of mime-types. The list of supported mime-types should be sorted
    in order of increasing desirability, in case of a situation where there is
    a tie.

    >>> best_match(['application/xbel+xml', 'text/xml'],
                   'text/*;q=0.5,*/*; q=0.1')
    'text/xml'

    :rtype: str
    """
    split_header = _filter_blank(header.split(','))
    parsed_header = [parse_media_range(r) for r in split_header]
    weighted_matches = []
    pos = 0
    for mime_type in supported:
        weighted_matches.append((
            quality_and_fitness_parsed(mime_type, parsed_header),
            pos,
            mime_type
        ))
        pos += 1
    weighted_matches.sort()

    return weighted_matches[-1][0][0] and weighted_matches[-1][2] or ''


def _filter_blank(i):
    """Return all non-empty items in the list."""
    for s in i:
        if s.strip():
            yield s
