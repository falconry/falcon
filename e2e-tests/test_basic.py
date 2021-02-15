def test_sse_message(browser):
    message = browser.find_element('div.sse', timeout=5)
    assert message.text == 'Hello'
