import tkinter as tk
from tkinter import scrolledtext, messagebox, font as tkfont
import asyncio
import threading
import websockets
import sys
from datetime import datetime

# Configurações Padrão
DEFAULT_SERVER_URL = "ws://127.0.0.1:8000/tunnel"
LOCAL_HOST = "127.0.0.1"
LOCAL_PORT = 8888

class TunnelApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Tunnel Prime Plus +")
        self.root.geometry("900x680")
        self.root.configure(bg="#0f172a")  # Slate 900
        
        # Cores Premium
        self.colors = {
            "bg": "#0f172a",
            "card": "#1e293b",
            "accent": "#f59e0b", # Gold/Amber 500
            "success": "#22c55e",
            "danger": "#ef4444",
            "text": "#f8fafc",
            "text_dim": "#94a3b8",
            "console_bg": "#020617",
            "border": "#334155"
        }

        self.running = False
        self.loop = None
        self.server = None
        self.thread = None
        self.connection_count = 0
        self.current_server_url = DEFAULT_SERVER_URL

        self.setup_ui()
        self.log("SISTEMA INICIALIZADO - VERSÃO PRIME GOLD +")

    def setup_ui(self):
        # Definição de Fontes
        self.title_font = tkfont.Font(family="Segoe UI", size=22, weight="bold")
        self.header_font = tkfont.Font(family="Segoe UI", size=10, weight="bold")
        self.normal_font = tkfont.Font(family="Segoe UI", size=10)
        self.mono_font = tkfont.Font(family="Consolas", size=9)

        # 1. Header Premium
        header = tk.Frame(self.root, bg=self.colors["accent"], height=110)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        title_frame = tk.Frame(header, bg=self.colors["accent"])
        title_frame.pack(side=tk.LEFT, padx=30)
        
        tk.Label(
            title_frame, 
            text="TUNNEL PRIME PLUS +", 
            font=self.title_font, 
            bg=self.colors["accent"], 
            fg="#0f172a"
        ).pack(anchor=tk.W)
        
        tk.Label(
            title_frame, 
            text="PONTE AVANÇADA TCP-WS | EDIÇÃO OURO", 
            font=("Segoe UI", 9, "bold"), 
            bg=self.colors["accent"], 
            fg="#451a03"
        ).pack(anchor=tk.W)

        # Status Badge no Header
        self.status_container = tk.Frame(header, bg=self.colors["accent"])
        self.status_container.pack(side=tk.RIGHT, padx=30)

        self.status_indicator = tk.Canvas(self.status_container, width=14, height=14, bg=self.colors["accent"], highlightthickness=0)
        self.status_indicator.pack(side=tk.LEFT, padx=10)
        self.status_dot = self.status_indicator.create_oval(2, 2, 12, 12, fill="#7f1d1d")

        self.status_text = tk.Label(
            self.status_container, 
            text="OFFLINE", 
            font=self.header_font, 
            bg=self.colors["accent"], 
            fg="#0f172a"
        )
        self.status_text.pack(side=tk.LEFT)

        # 2. Área de Conteúdo
        main_content = tk.Frame(self.root, bg=self.colors["bg"], padx=25, pady=25)
        main_content.pack(fill=tk.BOTH, expand=True)

        # Top Section (Config & Controls)
        top_section = tk.Frame(main_content, bg=self.colors["bg"])
        top_section.pack(fill=tk.X, pady=(0, 20))

        # Card de Configuração (Esquerda)
        config_card = tk.Frame(top_section, bg=self.colors["card"], padx=20, pady=20, highlightbackground=self.colors["border"], highlightthickness=1)
        config_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        tk.Label(config_card, text="CONFIGURAÇÕES DE REDE", font=self.header_font, bg=self.colors["card"], fg=self.colors["accent"]).pack(anchor=tk.W)
        
        sep = tk.Frame(config_card, height=1, bg=self.colors["border"])
        sep.pack(fill=tk.X, pady=10)

        # Grid de Configuração
        fields_frame = tk.Frame(config_card, bg=self.colors["card"])
        fields_frame.pack(fill=tk.X)

        # Local Gateway (Read Only)
        tk.Label(fields_frame, text="GATEWAY LOCAL:", font=self.header_font, bg=self.colors["card"], fg=self.colors["text_dim"]).grid(row=0, column=0, sticky=tk.W, pady=5)
        tk.Label(fields_frame, text=f"{LOCAL_HOST}:{LOCAL_PORT}", font=self.mono_font, bg=self.colors["card"], fg=self.colors["text"]).grid(row=0, column=1, sticky=tk.W, padx=10)

        # Remote URL (Editable)
        tk.Label(fields_frame, text="URL REMOTA (WS):", font=self.header_font, bg=self.colors["card"], fg=self.colors["text_dim"]).grid(row=1, column=0, sticky=tk.W, pady=5)
        
        self.url_entry = tk.Entry(
            fields_frame, 
            font=self.mono_font, 
            bg=self.colors["console_bg"], 
            fg=self.colors["text"], 
            insertbackground="white",
            borderwidth=0,
            highlightbackground=self.colors["border"],
            highlightthickness=1
        )
        self.url_entry.grid(row=1, column=1, sticky=tk.EW, padx=10, ipady=3)
        self.url_entry.insert(0, DEFAULT_SERVER_URL)
        fields_frame.columnconfigure(1, weight=1)

        # Card de Controle (Direita)
        self.controls_card = tk.Frame(top_section, bg=self.colors["card"], padx=20, pady=20, width=300, highlightbackground=self.colors["accent"], highlightthickness=1)
        self.controls_card.pack(side=tk.RIGHT, fill=tk.Y)
        self.controls_card.pack_propagate(False)

        tk.Label(self.controls_card, text="CENTRO DE OPERAÇÕES", font=self.header_font, bg=self.colors["card"], fg=self.colors["accent"]).pack(anchor=tk.W, pady=(0, 15))

        # Botão Toggle (Start/Stop)
        self.btn_toggle = tk.Button(
            self.controls_card, 
            text="INICIAR SISTEMA", 
            command=self.toggle_system,
            bg=self.colors["success"], 
            fg="white", 
            font=self.header_font,
            relief=tk.FLAT,
            height=2,
            cursor="hand2",
            activebackground="#16a34a",
            activeforeground="white"
        )
        self.btn_toggle.pack(fill=tk.X, pady=10)

        self.tip_label = tk.Label(
            self.controls_card, 
            text="Pronto para processar dados rdp.", 
            font=("Segoe UI", 8), 
            bg=self.colors["card"], 
            fg=self.colors["text_dim"],
            wraplength=240
        )
        self.tip_label.pack(pady=5)

        # 3. Console Card
        console_card = tk.Frame(main_content, bg=self.colors["card"], highlightbackground=self.colors["border"], highlightthickness=1)
        console_card.pack(fill=tk.BOTH, expand=True)

        console_header = tk.Frame(console_card, bg=self.colors["card"], padx=15, pady=10)
        console_header.pack(fill=tk.X)
        
        tk.Label(console_header, text="LOGS DE PERFORMANCE EM TEMPO REAL", font=self.header_font, bg=self.colors["card"], fg=self.colors["text_dim"]).pack(side=tk.LEFT)
        
        self.conn_label = tk.Label(console_header, text="CONEXÕES ATIVAS: 0", font=self.header_font, bg=self.colors["card"], fg=self.colors["success"])
        self.conn_label.pack(side=tk.RIGHT)

        self.console = scrolledtext.ScrolledText(
            console_card, 
            bg=self.colors["console_bg"], 
            fg="#4ade80", # Green 400
            font=self.mono_font,
            padx=15, 
            pady=15,
            borderwidth=0,
            highlightthickness=0
        )
        self.console.pack(fill=tk.BOTH, expand=True)

    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.console.insert(tk.END, f"➜ [{timestamp}] {message}\n")
        self.console.see(tk.END)
        print(f"[{timestamp}] {message}")

    def update_conns(self, delta):
        self.connection_count += delta
        self.conn_label.config(text=f"CONEXÕES ATIVAS: {max(0, self.connection_count)}")

    async def handle_client(self, local_reader, local_writer):
        client_addr = local_writer.get_extra_info('peername')
        self.root.after(0, lambda: self.update_conns(1))
        self.log(f"Conexão RDP estabelecida com {client_addr}")
        
        try:
            async with websockets.connect(self.current_server_url, max_size=None) as ws:
                async def tcp_to_ws():
                    try:
                        while self.running:
                            data = await local_reader.read(8192)
                            if not data: break
                            await ws.send(data)
                    except: pass

                async def ws_to_tcp():
                    try:
                        while self.running:
                            data = await ws.recv()
                            if not data: break
                            local_writer.write(data)
                            await local_writer.drain()
                    except: pass

                await asyncio.gather(tcp_to_ws(), ws_to_tcp())
        except Exception as e:
            self.log(f"Erro na ponte: {e}")
        finally:
            self.root.after(0, lambda: self.update_conns(-1))
            try:
                local_writer.close()
                await local_writer.wait_closed()
            except: pass
            self.log(f"Sessão finalizada para {client_addr}")

    async def run_tunnel(self):
        try:
            self.server = await asyncio.start_server(self.handle_client, LOCAL_HOST, LOCAL_PORT)
            self.log(f"MOTOR PRIME RODANDO EM {LOCAL_HOST}:{LOCAL_PORT}")
            self.root.after(0, self._set_ui_active)
            async with self.server:
                await self.server.serve_forever()
        except asyncio.CancelledError:
            self.log("DESLIGAMENTO DO MOTOR CONCLUÍDO.")
        except Exception as e:
            self.log(f"ERRO CRÍTICO NO MOTOR: {e}")
            self.root.after(0, self.stop_tunnel)

    def _set_ui_active(self):
        self.status_indicator.itemconfig(self.status_dot, fill=self.colors["success"])
        self.status_text.config(text="SISTEMA ATIVO")
        self.btn_toggle.config(text="PARAR SISTEMA", bg=self.colors["danger"], activebackground="#dc2626")
        self.url_entry.config(state=tk.DISABLED)

    def toggle_system(self):
        if self.running:
            self.stop_tunnel()
        else:
            self.start_tunnel()

    def start_tunnel(self):
        if self.running: return
        
        # Validação da URL
        url = self.url_entry.get().strip()
        if not url.startswith("ws"):
            messagebox.showerror("Erro Prime", "A URL deve começar com 'ws://' ou 'wss://'")
            return
        
        self.current_server_url = url
        self.running = True
        self.log("INICIALIZANDO MOTOR PRINCIPAL...")
        
        self.thread = threading.Thread(target=self._run_async_loop, daemon=True)
        self.thread.start()

    def _run_async_loop(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self.run_tunnel())
        except: pass

    def stop_tunnel(self):
        if not self.running: return
        self.running = False
        self.log("SOLICITANDO PARADA DO MOTOR...")
        
        if self.loop:
            for task in asyncio.all_tasks(self.loop): task.cancel()
            if self.server: self.loop.call_soon_threadsafe(self.server.close)
            self.loop.call_soon_threadsafe(self.loop.stop)
        
        self.btn_toggle.config(text="INICIAR SISTEMA", bg=self.colors["success"], activebackground="#16a34a")
        self.status_indicator.itemconfig(self.status_dot, fill="#7f1d1d")
        self.status_text.config(text="OFFLINE")
        self.url_entry.config(state=tk.NORMAL)
        self.log("SISTEMA EM STANDBY.")

if __name__ == "__main__":
    root = tk.Tk()
    # Estilização geral de janelas Tkinter no Windows
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass
        
    app = TunnelApp(root)
    root.protocol("WM_DELETE_WINDOW", lambda: sys.exit(0))
    root.mainloop()
