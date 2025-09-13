class Resource:
    def on_get(self, req, resp):
        # Get a dict of name/value cookie pairs.
        cookies = req.cookies  # noqa: F841

        my_cookie_values = req.get_cookie_values('my_cookie')

        if my_cookie_values:
            # NOTE: If there are multiple values set for the cookie, you
            #   will need to choose how to handle the additional values.
            v = my_cookie_values[0]  # noqa: F841
