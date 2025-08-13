# Copyright 2020-2025 by Vytautas Liuolia.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


def test_sse_broadcast(browser, clear_log):
    browser.slow_click('#button1')
    browser.assert_text('WS1 CONNECTED', 'div.sse', timeout=5)
    clear_log()

    browser.type('#input1', '/all Zombie alert!')
    browser.slow_click('#button1')
    browser.assert_text('[WS1] Zombie alert!', 'div.sse', timeout=5)
    clear_log()

    browser.type('#input1', '/all Zombie apocalypse averted (for now)')
    browser.slow_click('#button1')
    browser.assert_text(
        '[WS1] Zombie apocalypse averted (for now)', 'div.sse', timeout=5
    )
    clear_log()

    browser.type('#input1', '/quit')
    browser.slow_click('#button1')
    browser.assert_text('Bye, WS1!', 'div.ws1', timeout=5)
    browser.assert_text('WS1 DISCONNECTED', 'div.sse', timeout=5)


def test_chat(browser, clear_log):
    browser.slow_click('#button1')
    browser.assert_text('Hello, WS1!', 'div.ws1', timeout=5)
    browser.assert_text('WS1 CONNECTED', 'div.sse', timeout=5)
    clear_log()

    browser.slow_click('#button2')
    browser.assert_text('Hello, WS2!', 'div.ws2', timeout=5)
    browser.assert_text('WS2 CONNECTED', 'div.sse', timeout=5)
    clear_log()

    browser.type('#input1', '/msg WS2 Apples')
    browser.slow_click('#button1')
    browser.assert_text('[WS1] Apples', 'div.ws2', timeout=5)
    clear_log()

    browser.type('#input1', '/msg WS2 Oranges')
    browser.slow_click('#button1')
    browser.assert_text('[WS1] Oranges', 'div.ws2', timeout=5)
    clear_log()

    browser.type('#input1', '/msg WS2 Bananas')
    browser.slow_click('#button1')
    browser.assert_text('[WS1] Bananas', 'div.ws2', timeout=5)
    clear_log()

    browser.type('#input2', '/msg WS1 Talk to you later...')
    browser.slow_click('#button2')
    browser.assert_text('[WS2] Talk to you later...', 'div.ws1', timeout=5)
    clear_log()

    browser.type('#input1', '/quit')
    browser.slow_click('#button1')
    browser.assert_text('Bye, WS1!', 'div.ws1', timeout=5)
    browser.assert_text('DISCONNECTED (4001 quit command)', '#input1')

    browser.type('#input2', '/quit')
    browser.slow_click('#button2')
    browser.assert_text('Bye, WS2!', 'div.ws2', timeout=5)
    browser.assert_text('DISCONNECTED (4001 quit command)', '#input2')
