def test_basic(browser):
    src = browser.get_page_source()
    assert 'PONG' in src
