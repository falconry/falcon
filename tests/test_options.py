from falcon.request import RequestOptions
import falcon.testing as testing


class TestRequestOptions(testing.TestBase):

    def test_correct_options(self):
        options = RequestOptions()
        self.assertFalse(options.keep_blank_qs_values)
        options.keep_blank_qs_values = True
        self.assertTrue(options.keep_blank_qs_values)
        options.keep_blank_qs_values = False
        self.assertFalse(options.keep_blank_qs_values)

    def test_incorrect_options(self):
        options = RequestOptions()

        def _assign_invalid():
            options.invalid_option_and_attribute = True

        self.assertRaises(AttributeError, _assign_invalid)
