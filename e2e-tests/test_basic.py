def test_sse_message(browser):
    message = browser.find_element('div.ws1', timeout=5)
    assert message.text == 'Hello, WS1!'
