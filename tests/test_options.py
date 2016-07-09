import ddt

from falcon.request import RequestOptions
import falcon.testing as testing


@ddt.ddt
class TestRequestOptions(testing.TestBase):

    def test_option_defaults(self):
        options = RequestOptions()

        self.assertFalse(options.keep_blank_qs_values)
        self.assertFalse(options.auto_parse_form_urlencoded)
        self.assertTrue(options.auto_parse_qs_csv)

    @ddt.data(
        'keep_blank_qs_values',
        'auto_parse_form_urlencoded',
        'auto_parse_qs_csv',
    )
    def test_options_toggle(self, option_name):
        options = RequestOptions()

        setattr(options, option_name, True)
        self.assertTrue(getattr(options, option_name))

        setattr(options, option_name, False)
        self.assertFalse(getattr(options, option_name))

    def test_incorrect_options(self):
        options = RequestOptions()

        def _assign_invalid():
            options.invalid_option_and_attribute = True

        self.assertRaises(AttributeError, _assign_invalid)
