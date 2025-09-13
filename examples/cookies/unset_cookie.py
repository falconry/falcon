# Set a cookie in middleware or in a previous request.
resp.set_cookie('my_cookie', 'my cookie value')  # noqa: F821

# -- snip --

# Clear the cookie for the current request and instruct the user agent
#   to expire its own copy of the cookie (if any).
resp.unset_cookie('my_cookie')  # noqa: F821
