import asyncio
import time


async def _say_hi():
    print(f'[{time.time()}] Hi!')


async def app(scope, receive, send):
    await send({
        'type': 'http.response.start',
        'status': 200,
        'headers': [
            [b'content-type', b'application/json'],
        ]
    })
    await send({
        'type': 'http.response.body',
        'body': f'[{time.time()}] Hello world!'.encode(),
    })

    loop = asyncio.get_event_loop()
    loop.create_task(_say_hi())
