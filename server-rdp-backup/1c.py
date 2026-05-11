import asyncio
import websockets

SERVER_URL = "ws://127.0.0.1:8000/tunnel"

LOCAL_HOST = "127.0.0.1"
LOCAL_PORT = 8888


async def handle_client(local_reader, local_writer):

    print("mstsc conectado")

    async with websockets.connect(
        SERVER_URL,
        max_size=None
    ) as ws:

        async def tcp_to_ws():
            try:
                while True:
                    data = await local_reader.read(4096)

                    if not data:
                        break

                    await ws.send(data)

            except Exception as e:
                print("tcp_to_ws:", e)

        async def ws_to_tcp():
            try:
                while True:
                    data = await ws.recv()

                    if not data:
                        break

                    local_writer.write(data)
                    await local_writer.drain()

            except Exception as e:
                print("ws_to_tcp:", e)

        await asyncio.gather(
            tcp_to_ws(),
            ws_to_tcp()
        )

    local_writer.close()


async def main():

    server = await asyncio.start_server(
        handle_client,
        LOCAL_HOST,
        LOCAL_PORT
    )

    print(f"Escutando em {LOCAL_HOST}:{LOCAL_PORT}")

    async with server:
        await server.serve_forever()


asyncio.run(main())