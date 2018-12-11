import pytest

from falcon.request import RequestOptions


class TestRequestOptions(object):

    def test_option_defaults(self):
        options = RequestOptions()

        assert options.keep_blank_qs_values
        assert not options.auto_parse_form_urlencoded
        assert not options.auto_parse_qs_csv
        assert not options.strip_url_path_trailing_slash

    @pytest.mark.parametrize('option_name', [
        'keep_blank_qs_values',
        'auto_parse_form_urlencoded',
        'auto_parse_qs_csv',
        'strip_url_path_trailing_slash',
    ])
    def test_options_toggle(self, option_name):
        options = RequestOptions()

        setattr(options, option_name, True)
        assert getattr(options, option_name)

        setattr(options, option_name, False)
        assert not getattr(options, option_name)

    def test_incorrect_options(self):
        options = RequestOptions()

        def _assign_invalid():
            options.invalid_option_and_attribute = True

        with pytest.raises(AttributeError):
            _assign_invalid()
