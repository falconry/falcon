import asyncio
import websockets


async def send_message():
    uri = 'ws://localhost:8000/reports'

    async with websockets.connect(uri) as websocket:
        # Send the authentication token
        await websocket.send('very secure token!')

        while True:
            message = input('Name of the log: ')
            await websocket.send(message)
            response = await websocket.recv()
            print(response)


if __name__ == '__main__':
    asyncio.run(send_message())
