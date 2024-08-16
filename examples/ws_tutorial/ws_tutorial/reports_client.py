# This is a simple example of a WebSocket client that sends a message to the server.
# Since it's an example using the `websockets` library and it isn't using anything
# specific to Falcon, there are no tests. Coverage is skipped for this module.

import asyncio

import websockets


async def send_message():
    uri = 'ws://localhost:8000/reports'

    async with websockets.connect(uri) as websocket:
        # Send the authentication token
        await websocket.send('very secure token')

        while True:
            message = input('Name of the log (q to exit): ')
            if message.casefold() == 'q':
                break
            await websocket.send(message)
            response = await websocket.recv()
            print(response)


if __name__ == '__main__':
    asyncio.run(send_message())
