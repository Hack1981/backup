import tkinter as tk
from tkinter import scrolledtext, messagebox
import asyncio
import threading
import websockets
import sys
from datetime import datetime

# Configurações Padrão
SERVER_URL = "ws://127.0.0.1:8000/tunnel"
LOCAL_HOST = "127.0.0.1"
LOCAL_PORT = 8888

class TunnelApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Python Tunnel Controller")
        self.root.geometry("700x500")
        self.root.configure(bg="#1e1e1e")

        self.running = False
        self.loop = None
        self.server = None
        self.thread = None

        self.setup_ui()
        self.log("Sistema iniciado. Pronto para configurar.")

    def setup_ui(self):
        # Frame de Controles
        control_frame = tk.Frame(self.root, bg="#2d2d2d", pady=10)
        control_frame.pack(fill=tk.X)

        # Botão Iniciar
        self.btn_start = tk.Button(
            control_frame, 
            text="START TUNNEL", 
            command=self.start_tunnel,
            bg="#28a745", 
            fg="white", 
            font=("Arial", 10, "bold"),
            padx=20,
            relief=tk.FLAT
        )
        self.btn_start.pack(side=tk.LEFT, padx=10)

        # Botão Parar
        self.btn_stop = tk.Button(
            control_frame, 
            text="STOP TUNNEL", 
            command=self.stop_tunnel,
            bg="#dc3545", 
            fg="white", 
            font=("Arial", 10, "bold"),
            padx=20,
            relief=tk.FLAT,
            state=tk.DISABLED
        )
        self.btn_stop.pack(side=tk.LEFT, padx=10)

        # Status Label
        self.status_label = tk.Label(
            control_frame, 
            text="Status: Parado", 
            bg="#2d2d2d", 
            fg="#ffc107",
            font=("Arial", 10)
        )
        self.status_label.pack(side=tk.RIGHT, padx=20)

        # Console de Logs
        self.console = scrolledtext.ScrolledText(
            self.root, 
            bg="#000000", 
            fg="#00ff00", 
            font=("Consolas", 10),
            padx=10, 
            pady=10
        )
        self.console.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def log(self, message):
        """Adiciona uma mensagem ao console da interface"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        msg = f"[{timestamp}] {message}\n"
        self.console.insert(tk.END, msg)
        self.console.see(tk.END)
        print(f"[{timestamp}] {message}")

    async def handle_client(self, local_reader, local_writer):
        client_addr = local_writer.get_extra_info('peername')
        self.log(f"Nova conexão MSTSC de {client_addr}")
        
        try:
            async with websockets.connect(SERVER_URL, max_size=None) as ws:
                async def tcp_to_ws():
                    try:
                        while self.running:
                            data = await local_reader.read(4096)
                            if not data: break
                            await ws.send(data)
                    except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError, OSError):
                        pass # Erro de rede comum, ignorar log pesado
                    except Exception as e:
                        self.log(f"Aviso TCP -> WS: {e}")

                async def ws_to_tcp():
                    try:
                        while self.running:
                            data = await ws.recv()
                            if not data: break
                            local_writer.write(data)
                            await local_writer.drain()
                    except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError, OSError):
                        pass # Erro de rede comum, ignorar log pesado
                    except Exception as e:
                        self.log(f"Aviso WS -> TCP: {e}")

                await asyncio.gather(tcp_to_ws(), ws_to_tcp())
        except Exception as e:
            self.log(f"Conexão com servidor WS falhou ou foi fechada: {e}")
        finally:
            try:
                local_writer.close()
                await local_writer.wait_closed()
            except:
                pass
            self.log(f"Cliente {client_addr} desconectado.")

    async def run_tunnel(self):
        try:
            self.server = await asyncio.start_server(
                self.handle_client,
                LOCAL_HOST,
                LOCAL_PORT
            )
            self.log(f"Escutando localmente em {LOCAL_HOST}:{LOCAL_PORT}")
            async with self.server:
                await self.server.serve_forever()
        except asyncio.CancelledError:
            self.log("Servidor parado.")
        except Exception as e:
            self.log(f"Erro no servidor: {e}")

    def start_tunnel(self):
        if self.running:
            return

        self.running = True
        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.status_label.config(text="Status: Rodando", fg="#28a745")
        self.log("Iniciando túnel...")

        self.thread = threading.Thread(target=self._run_async_loop, daemon=True)
        self.thread.start()

    def _run_async_loop(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        try:
            self.loop.run_until_complete(self.run_tunnel())
        except Exception as e:
            # Ignora erros de cancelamento durante o fechamento
            if self.running:
                self.root.after(0, lambda: self.log(f"Loop error: {e}"))
        finally:
            # Não tentamos fechar o loop aqui imediatamente para evitar o RuntimeError
            # O Python lidará com o lixo ao encerrar a thread daemon
            pass

    def stop_tunnel(self):
        if not self.running:
            return

        self.running = False
        self.log("Parando túnel...")

        if self.loop and self.loop.is_running():
            # Cancela todas as tarefas pendentes
            for task in asyncio.all_tasks(self.loop):
                task.cancel()
            
            # Para o servidor de forma segura
            if self.server:
                self.loop.call_soon_threadsafe(self.server.close)
            
            # Para o próprio loop
            self.loop.call_soon_threadsafe(self.loop.stop)
        
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.status_label.config(text="Status: Parado", fg="#ffc107")
        self.log("Túnel interrompido.")

if __name__ == "__main__":
    root = tk.Tk()
    app = TunnelApp(root)
    root.protocol("WM_DELETE_WINDOW", lambda: sys.exit(0))
    root.mainloop()
