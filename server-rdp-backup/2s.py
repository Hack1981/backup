import asyncio
from fastapi import FastAPI, WebSocket

app = FastAPI()

TARGET_HOST = "192.168.90.124"
TARGET_PORT = 3389


@app.websocket("/tunnel")
async def tunnel(ws: WebSocket):
    await ws.accept()

    print("Cliente conectado")

    try:
        reader, writer = await asyncio.open_connection(
            TARGET_HOST,
            TARGET_PORT
        )

        async def ws_to_tcp():
            try:
                while True:
                    data = await ws.receive_bytes()

                    if not data:
                        break

                    writer.write(data)
                    await writer.drain()

            except Exception as e:
                print("ws_to_tcp:", e)

            finally:
                writer.close()

        async def tcp_to_ws():
            try:
                while True:
                    data = await reader.read(4096)

                    if not data:
                        break

                    await ws.send_bytes(data)

            except Exception as e:
                print("tcp_to_ws:", e)

            finally:
                await ws.close()

        await asyncio.gather(
            ws_to_tcp(),
            tcp_to_ws()
        )

    except Exception as e:
        print("Erro geral:", e)