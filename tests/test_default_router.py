import textwrap

import pytest

import falcon
from falcon import testing
from falcon.routing import DefaultRouter


@pytest.fixture
def client():
    return testing.TestClient(falcon.API())


@pytest.fixture
def router():
    router = DefaultRouter()

    router.add_route(
        '/repos', ResourceWithId(1))
    router.add_route(
        '/repos/{org}', ResourceWithId(2))
    router.add_route(
        '/repos/{org}/{repo}', ResourceWithId(3))
    router.add_route(
        '/repos/{org}/{repo}/commits', ResourceWithId(4))
    router.add_route(
        u'/repos/{org}/{repo}/compare/{usr0}:{branch0}...{usr1}:{branch1}',
        ResourceWithId(5))

    router.add_route(
        '/teams/{id}', ResourceWithId(6))
    router.add_route(
        '/teams/{id}/members', ResourceWithId(7))

    router.add_route(
        '/teams/default', ResourceWithId(19))
    router.add_route(
        '/teams/default/members/thing', ResourceWithId(19))

    router.add_route(
        '/user/memberships', ResourceWithId(8))
    router.add_route(
        '/emojis', ResourceWithId(9))
    router.add_route(
        '/repos/{org}/{repo}/compare/{usr0}:{branch0}...{usr1}:{branch1}/full',
        ResourceWithId(10))
    router.add_route(
        '/repos/{org}/{repo}/compare/all', ResourceWithId(11))

    # NOTE(kgriffs): The ordering of these calls is significant; we
    # need to test that the {id} field does not match the other routes,
    # regardless of the order they are added.
    router.add_route(
        '/emojis/signs/0', ResourceWithId(12))
    router.add_route(
        '/emojis/signs/{id}', ResourceWithId(13))
    router.add_route(
        '/emojis/signs/42', ResourceWithId(14))
    router.add_route(
        '/emojis/signs/42/small.jpg', ResourceWithId(23))
    router.add_route(
        '/emojis/signs/78/small.png', ResourceWithId(24))

    # Test some more special chars
    router.add_route(
        '/emojis/signs/78/small(png)', ResourceWithId(25))
    router.add_route(
        '/emojis/signs/78/small_png', ResourceWithId(26))
    router.add_route('/images/{id}.gif', ResourceWithId(27))

    router.add_route(
        '/repos/{org}/{repo}/compare/{usr0}:{branch0}...{usr1}:{branch1}/part',
        ResourceWithId(15))
    router.add_route(
        '/repos/{org}/{repo}/compare/{usr0}:{branch0}', ResourceWithId(16))
    router.add_route(
        '/repos/{org}/{repo}/compare/{usr0}:{branch0}/full', ResourceWithId(17))

    router.add_route(
        '/gists/{id}/{representation}', ResourceWithId(21))
    router.add_route(
        '/gists/{id}/raw', ResourceWithId(18))
    router.add_route(
        '/gists/first', ResourceWithId(20))

    router.add_route('/item/{q}', ResourceWithId(28))

    # ----------------------------------------------------------------
    # Routes with field converters
    # ----------------------------------------------------------------

    router.add_route(
        '/cvt/teams/{id:int(min=7)}', ResourceWithId(29))
    router.add_route(
        '/cvt/teams/{id:int(min=7)}/members', ResourceWithId(30))
    router.add_route(
        '/cvt/teams/default', ResourceWithId(31))
    router.add_route(
        '/cvt/teams/default/members/{id:int}-{tenure:int}', ResourceWithId(32))

    router.add_route(
        '/cvt/repos/{org}/{repo}/compare/{usr0}:{branch0:int}...{usr1}:{branch1:int}/part',
        ResourceWithId(33))
    router.add_route(
        '/cvt/repos/{org}/{repo}/compare/{usr0}:{branch0:int}', ResourceWithId(34))
    router.add_route(
        '/cvt/repos/{org}/{repo}/compare/{usr0}:{branch0:int}/full', ResourceWithId(35))

    return router


class ResourceWithId(object):
    def __init__(self, resource_id):
        self.resource_id = resource_id

    def __repr__(self):
        return 'ResourceWithId({})'.format(self.resource_id)

    def on_get(self, req, resp):
        resp.body = self.resource_id


class SpamConverter(object):
    def __init__(self, times, eggs=False):
        self._times = times
        self._eggs = eggs

    def convert(self, fragment):
        item = fragment
        if self._eggs:
            item += '&eggs'

        return ', '.join(item for i in range(self._times))


# =====================================================================
# Regression tests for use cases reported by users
# =====================================================================


def test_user_regression_versioned_url():
    router = DefaultRouter()
    router.add_route('/{version}/messages', ResourceWithId(2))

    resource, __, __, __ = router.find('/v2/messages')
    assert resource.resource_id == 2

    router.add_route('/v2', ResourceWithId(1))

    resource, __, __, __ = router.find('/v2')
    assert resource.resource_id == 1

    resource, __, __, __ = router.find('/v2/messages')
    assert resource.resource_id == 2

    resource, __, __, __ = router.find('/v1/messages')
    assert resource.resource_id == 2

    route = router.find('/v1')
    assert route is None


def test_user_regression_recipes():
    router = DefaultRouter()
    router.add_route(
        '/recipes/{activity}/{type_id}',
        ResourceWithId(1)
    )
    router.add_route(
        '/recipes/baking',
        ResourceWithId(2)
    )

    resource, __, __, __ = router.find('/recipes/baking/4242')
    assert resource.resource_id == 1

    resource, __, __, __ = router.find('/recipes/baking')
    assert resource.resource_id == 2

    route = router.find('/recipes/grilling')
    assert route is None


@pytest.mark.parametrize('uri_template,path,expected_params', [
    ('/serviceRoot/People|{field}', '/serviceRoot/People|susie', {'field': 'susie'}),
    ('/serviceRoot/People[{field}]', "/serviceRoot/People['calvin']", {'field': "'calvin'"}),
    ('/serviceRoot/People({field})', "/serviceRoot/People('hobbes')", {'field': "'hobbes'"}),
    ('/serviceRoot/People({field})', "/serviceRoot/People('hob)bes')", {'field': "'hob)bes'"}),
    ('/serviceRoot/People({field})(z)', '/serviceRoot/People(hobbes)(z)', {'field': 'hobbes'}),
    ("/serviceRoot/People('{field}')", "/serviceRoot/People('rosalyn')", {'field': 'rosalyn'}),
    ('/^{field}', '/^42', {'field': '42'}),
    ('/+{field}', '/+42', {'field': '42'}),
    (
        '/foo/{first}_{second}/bar',
        '/foo/abc_def_ghijk/bar',

        # NOTE(kgriffs): The regex pattern is greedy, so this is
        # expected. We can not change this behavior in a minor
        # release, since it would be a breaking change. If there
        # is enough demand for it, we could introduce an option
        # to toggle this behavior.
        {'first': 'abc_def', 'second': 'ghijk'},
    ),

    # NOTE(kgriffs): Why someone would use a question mark like this
    # I have no idea (esp. since it would have to be encoded to avoid
    # being mistaken for the query string separator). Including it only
    # for completeness.
    ('/items/{x}?{y}', '/items/1080?768', {'x': '1080', 'y': '768'}),

    ('/items/{x}|{y}', '/items/1080|768', {'x': '1080', 'y': '768'}),
    ('/items/{x},{y}', '/items/1080,768', {'x': '1080', 'y': '768'}),
    ('/items/{x}^^{y}', '/items/1080^^768', {'x': '1080', 'y': '768'}),
    ('/items/{x}*{y}*', '/items/1080*768*', {'x': '1080', 'y': '768'}),
    ('/thing-2/something+{field}+', '/thing-2/something+42+', {'field': '42'}),
    ('/thing-2/something*{field}/notes', '/thing-2/something*42/notes', {'field': '42'}),
    (
        '/thing-2/something+{field}|{q}/notes',
        '/thing-2/something+else|z/notes',
        {'field': 'else', 'q': 'z'},
    ),
    (
        "serviceRoot/$metadata#Airports('{field}')/Name",
        "serviceRoot/$metadata#Airports('KSFO')/Name",
        {'field': 'KSFO'},
    ),
])
def test_user_regression_special_chars(uri_template, path, expected_params):
    router = DefaultRouter()

    router.add_route(uri_template, ResourceWithId(1))

    route = router.find(path)
    assert route is not None

    resource, __, params, __ = route
    assert resource.resource_id == 1
    assert params == expected_params


# =====================================================================
# Other tests
# =====================================================================


@pytest.mark.parametrize('uri_template', [
    {},
    set(),
    object()
])
def test_not_str(uri_template):
    app = falcon.API()
    with pytest.raises(TypeError):
        app.add_route(uri_template, ResourceWithId(-1))


def test_root_path():
    router = DefaultRouter()
    router.add_route('/', ResourceWithId(42))

    resource, __, __, __ = router.find('/')
    assert resource.resource_id == 42

    expected_src = textwrap.dedent("""
        def find(path, return_values, patterns, converters, params):
            path_len = len(path)
            if path_len > 0:
                if path[0] == '':
                    if path_len == 1:
                        return return_values[0]
                    return None
                return None
            return None
    """).strip()

    assert router.finder_src == expected_src


@pytest.mark.parametrize('uri_template', [
    '/{field}{field}',
    '/{field}...{field}',
    '/{field}/{another}/{field}',
    '/{field}/something/something/{field}/something',
])
def test_duplicate_field_names(uri_template):
    router = DefaultRouter()
    with pytest.raises(ValueError):
        router.add_route(uri_template, ResourceWithId(1))


@pytest.mark.parametrize('uri_template,path', [
    ('/items/thing', '/items/t'),
    ('/items/{x}|{y}|', '/items/1080|768'),
    ('/items/{x}*{y}foo', '/items/1080*768foobar'),
    ('/items/{x}*768*', '/items/1080*768***'),
])
def test_match_entire_path(uri_template, path):
    router = DefaultRouter()

    router.add_route(uri_template, ResourceWithId(1))

    route = router.find(path)
    assert route is None


@pytest.mark.parametrize('uri_template', [
    '/teams/{conflict}',  # simple vs simple
    '/emojis/signs/{id_too}',  # another simple vs simple
    '/repos/{org}/{repo}/compare/{complex}:{vs}...{complex2}:{conflict}',
    '/teams/{id:int}/settings',  # converted vs. non-converted
])
def test_conflict(router, uri_template):
    with pytest.raises(ValueError):
        router.add_route(uri_template, ResourceWithId(-1))


@pytest.mark.parametrize('uri_template', [
    '/repos/{org}/{repo}/compare/{simple_vs_complex}',
    '/repos/{complex}.{vs}.{simple}',
    '/repos/{org}/{repo}/compare/{complex}:{vs}...{complex2}/full',
])
def test_non_conflict(router, uri_template):
    router.add_route(uri_template, ResourceWithId(-1))


@pytest.mark.parametrize('uri_template', [
    # Missing field name
    '/{}',
    '/repos/{org}/{repo}/compare/{}',
    '/repos/{complex}.{}.{thing}',

    # Field names must be valid Python identifiers
    '/{9v}',
    '/{524hello}/world',
    '/hello/{1world}',
    '/repos/{complex}.{9v}.{thing}/etc',
    '/{*kgriffs}',
    '/{@kgriffs}',
    '/repos/{complex}.{v}.{@thing}/etc',
    '/{-kgriffs}',
    '/repos/{complex}.{-v}.{thing}/etc',
    '/repos/{simple-thing}/etc',

    # Neither fields nor literal segments may not contain whitespace
    '/this and that',
    '/this\tand\tthat'
    '/this\nand\nthat'
    '/{thing }/world',
    '/{thing\t}/world',
    '/{\nthing}/world',
    '/{th\ving}/world',
    '/{ thing}/world',
    '/{ thing }/world',
    '/{thing}/wo rld',
    '/{thing} /world',
    '/repos/{or g}/{repo}/compare/{thing}',
    '/repos/{org}/{repo}/compare/{th\ting}',
])
def test_invalid_field_name(router, uri_template):
    with pytest.raises(ValueError):
        router.add_route(uri_template, ResourceWithId(-1))


def test_print_src(router):
    """Diagnostic test that simply prints the router's find() source code.

    Example:

        $ tox -e py27_debug -- -k test_print_src -s
    """
    print('\n\n' + router.finder_src + '\n')


def test_override(router):
    router.add_route('/emojis/signs/0', ResourceWithId(-1))

    resource, __, __, __ = router.find('/emojis/signs/0')
    assert resource.resource_id == -1


def test_literal_segment(router):
    resource, __, __, __ = router.find('/emojis/signs/0')
    assert resource.resource_id == 12

    resource, __, __, __ = router.find('/emojis/signs/1')
    assert resource.resource_id == 13

    resource, __, __, __ = router.find('/emojis/signs/42')
    assert resource.resource_id == 14

    resource, __, __, __ = router.find('/emojis/signs/42/small.jpg')
    assert resource.resource_id == 23

    route = router.find('/emojis/signs/1/small')
    assert route is None


@pytest.mark.parametrize('path', [
    '/teams',
    '/emojis/signs',
    '/gists',
    '/gists/42',
])
def test_dead_segment(router, path):
    route = router.find(path)
    assert route is None


@pytest.mark.parametrize('path', [
    '/repos/racker/falcon/compare/foo',
    '/repos/racker/falcon/compare/foo/full',
])
def test_malformed_pattern(router, path):
    route = router.find(path)
    assert route is None


def test_literal(router):
    resource, __, __, __ = router.find('/user/memberships')
    assert resource.resource_id == 8


@pytest.mark.parametrize('path,expected_params', [
    ('/cvt/teams/007', {'id': 7}),
    ('/cvt/teams/1234/members', {'id': 1234}),
    ('/cvt/teams/default/members/700-5', {'id': 700, 'tenure': 5}),
    (
        '/cvt/repos/org/repo/compare/xkcd:353',
        {'org': 'org', 'repo': 'repo', 'usr0': 'xkcd', 'branch0': 353},
    ),
    (
        '/cvt/repos/org/repo/compare/gunmachan:1234...kumamon:5678/part',
        {
            'org': 'org',
            'repo': 'repo',
            'usr0': 'gunmachan',
            'branch0': 1234,
            'usr1': 'kumamon',
            'branch1': 5678,
        }
    ),
    (
        '/cvt/repos/xkcd/353/compare/susan:0001/full',
        {'org': 'xkcd', 'repo': '353', 'usr0': 'susan', 'branch0': 1},
    )
])
def test_converters(router, path, expected_params):
    __, __, params, __ = router.find(path)
    assert params == expected_params


@pytest.mark.parametrize('uri_template', [
    '/foo/{bar:int(0)}',
    '/foo/{bar:int(num_digits=0)}',
    '/foo/{bar:int(-1)}/baz',
    '/foo/{bar:int(num_digits=-1)}/baz',
])
def test_converters_with_invalid_options(router, uri_template):
    # NOTE(kgriffs): Sanity-check that errors are properly bubbled up
    # when calling add_route(). Additional checks can be found
    # in test_uri_converters.py
    with pytest.raises(ValueError):
        router.add_route(uri_template, ResourceWithId(1))


@pytest.mark.parametrize('uri_template', [
    '/foo/{bar:}',
    '/foo/{bar:unknown}/baz',
])
def test_converters_malformed_specification(router, uri_template):
    with pytest.raises(ValueError):
        router.add_route(uri_template, ResourceWithId(1))


def test_variable(router):
    resource, __, params, __ = router.find('/teams/42')
    assert resource.resource_id == 6
    assert params == {'id': '42'}

    __, __, params, __ = router.find('/emojis/signs/stop')
    assert params == {'id': 'stop'}

    __, __, params, __ = router.find('/gists/42/raw')
    assert params == {'id': '42'}

    __, __, params, __ = router.find('/images/42.gif')
    assert params == {'id': '42'}


def test_single_character_field_name(router):
    __, __, params, __ = router.find('/item/1234')
    assert params == {'q': '1234'}


@pytest.mark.parametrize('path,expected_id', [
    ('/teams/default', 19),
    ('/teams/default/members', 7),
    ('/cvt/teams/default', 31),
    ('/cvt/teams/default/members/1234-10', 32),
    ('/teams/1234', 6),
    ('/teams/1234/members', 7),
    ('/gists/first', 20),
    ('/gists/first/raw', 18),
    ('/gists/first/pdf', 21),
    ('/gists/1776/pdf', 21),
    ('/emojis/signs/78', 13),
    ('/emojis/signs/78/small.png', 24),
    ('/emojis/signs/78/small(png)', 25),
    ('/emojis/signs/78/small_png', 26),
])
def test_literal_vs_variable(router, path, expected_id):
    resource, __, __, __ = router.find(path)
    assert resource.resource_id == expected_id


@pytest.mark.parametrize('path', [
    # Misc.
    '/this/does/not/exist',
    '/user/bogus',
    '/repos/racker/falcon/compare/johndoe:master...janedoe:dev/bogus',

    # Literal vs variable (teams)
    '/teams',
    '/teams/42/members/undefined',
    '/teams/42/undefined',
    '/teams/42/undefined/segments',
    '/teams/default/members/undefined',
    '/teams/default/members/thing/undefined',
    '/teams/default/members/thing/undefined/segments',
    '/teams/default/undefined',
    '/teams/default/undefined/segments',

    # Literal vs. variable (converters)
    '/cvt/teams/default/members',  # 'default' can't be converted to an int
    '/cvt/teams/NaN',
    '/cvt/teams/default/members/NaN',

    # Literal vs variable (emojis)
    '/emojis/signs',
    '/emojis/signs/0/small',
    '/emojis/signs/0/undefined',
    '/emojis/signs/0/undefined/segments',
    '/emojis/signs/20/small',
    '/emojis/signs/20/undefined',
    '/emojis/signs/42/undefined',
    '/emojis/signs/78/undefined',
])
def test_not_found(router, path):
    route = router.find(path)
    assert route is None


def test_subsegment_not_found(router):
    route = router.find('/emojis/signs/0/x')
    assert route is None


def test_multivar(router):
    resource, __, params, __ = router.find('/repos/racker/falcon/commits')
    assert resource.resource_id == 4
    assert params == {'org': 'racker', 'repo': 'falcon'}

    resource, __, params, __ = router.find('/repos/racker/falcon/compare/all')
    assert resource.resource_id == 11
    assert params == {'org': 'racker', 'repo': 'falcon'}


@pytest.mark.parametrize('url_postfix,resource_id', [
    ('', 5),
    ('/full', 10),
    ('/part', 15),
])
def test_complex(router, url_postfix, resource_id):
    uri = '/repos/racker/falcon/compare/johndoe:master...janedoe:dev'
    resource, __, params, __ = router.find(uri + url_postfix)

    assert resource.resource_id == resource_id
    assert (params == {
        'org': 'racker',
        'repo': 'falcon',
        'usr0': 'johndoe',
        'branch0': 'master',
        'usr1': 'janedoe',
        'branch1': 'dev',
    })


@pytest.mark.parametrize('url_postfix,resource_id,expected_template', [
    ('', 16, '/repos/{org}/{repo}/compare/{usr0}:{branch0}'),
    ('/full', 17, '/repos/{org}/{repo}/compare/{usr0}:{branch0}/full')
])
def test_complex_alt(router, url_postfix, resource_id, expected_template):
    uri = '/repos/falconry/falcon/compare/johndoe:master' + url_postfix
    resource, __, params, uri_template = router.find(uri)

    assert resource.resource_id == resource_id
    assert (params == {
        'org': 'falconry',
        'repo': 'falcon',
        'usr0': 'johndoe',
        'branch0': 'master',
    })
    assert uri_template == expected_template


def test_options_converters_set(router):
    router.options.converters['spam'] = SpamConverter

    router.add_route('/{food:spam(3, eggs=True)}', ResourceWithId(1))
    resource, __, params, __ = router.find('/spam')

    assert params == {'food': 'spam&eggs, spam&eggs, spam&eggs'}


@pytest.mark.parametrize('converter_name', [
    'spam',
    'spam_2'
])
def test_options_converters_update(router, converter_name):
    router.options.converters.update({
        'spam': SpamConverter,
        'spam_2': SpamConverter,
    })

    template = '/{food:' + converter_name + '(3, eggs=True)}'
    router.add_route(template, ResourceWithId(1))
    resource, __, params, __ = router.find('/spam')

    assert params == {'food': 'spam&eggs, spam&eggs, spam&eggs'}


@pytest.mark.parametrize('name', [
    'has whitespace',
    'whitespace ',
    ' whitespace ',
    ' whitespace',
    'funky$character',
    '42istheanswer',
    'with-hyphen',
])
def test_options_converters_invalid_name(router, name):
    with pytest.raises(ValueError):
        router.options.converters[name] = object


def test_options_converters_invalid_name_on_update(router):
    with pytest.raises(ValueError):
        router.options.converters.update({
            'valid_name': SpamConverter,
            '7eleven': SpamConverter,
        })
