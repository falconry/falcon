import asyncio
import websockets


async def send_message():
    uri = 'ws://localhost:8000/echo/hello'

    async with websockets.connect(uri) as websocket:
        while True:
            message = input('Enter a message: ')
            await websocket.send(message)
            response = await websocket.recv()
            print(response)


if __name__ == '__main__':
    asyncio.run(send_message())
