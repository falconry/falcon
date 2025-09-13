# Set the maximum age of the cookie to 10 minutes (600 seconds)
#   and the cookie's domain to 'example.com'
resp.set_cookie('my_cookie', 'my cookie value', max_age=600, domain='example.com')  # noqa: F821
