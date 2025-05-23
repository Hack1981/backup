import os
import json
import base64
import requests
import asyncio
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from google import genai
from google.genai import types

# === MÚLTIPLAS API KEYS ===
API_KEYS = [
    "AIzaSyCDd7mBF9ov2sMETta-iDa7XCU9rJN7SyU",
    "AIzaSyCRqHRaNKDe2c2YooMcSldO8g2jvPoXllA",
    "AIzaSyCDl-FH4ZsCv37eWXVIrZMoCea-Is2zWoE"
]

api_index = 0
api_index_lock = asyncio.Lock()
model = "gemini-2.0-flash"

app = FastAPI()

# Middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

limite_requisicoes = len(API_KEYS) * 15
semaforo = asyncio.Semaphore(limite_requisicoes)
ultimas_requisicoes = []

# === MODELS ===

class ChatRequest(BaseModel):
    email: str
    pergunta: str
    web: str = "off"  # "on" ou "off"

class ImageRequest(BaseModel):
    email: str
    prompt: str

# === FUNÇÕES AUXILIARES ===

async def controlar_taxa():
    global ultimas_requisicoes

    agora = datetime.utcnow()
    ultimas_requisicoes[:] = [t for t in ultimas_requisicoes if (agora - t) < timedelta(seconds=60)]

    while len(ultimas_requisicoes) >= limite_requisicoes:
        await asyncio.sleep(1)
        agora = datetime.utcnow()
        ultimas_requisicoes[:] = [t for t in ultimas_requisicoes if (agora - t) < timedelta(seconds=60)]

    ultimas_requisicoes.append(datetime.utcnow())

def verificar_email(email: str):
    url = f"https://api-criar-conta.vercel.app//check-account/?email={email}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if data.get("exists"):
            return data.get("id")
    return None

def get_user_path(user_id: str):
    dir_path = os.path.join("usuarios", user_id)
    os.makedirs(dir_path, exist_ok=True)
    return os.path.join(dir_path, "historico.json")

def salvar_historico(path: str, historico):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(historico, f, ensure_ascii=False, indent=4)

def carregar_historico(path: str):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        historico_inicial = [
            {
                "role": "user",
                "text": "Sempre que eu perguntar diretamente 'qual é o seu nome?' ou algo parecido, responda com: 'Meu nome é Zippy.' Não inclua isso em outras respostas, mesmo que sejam sobre outros assuntos. Está claro?"
            },
            {
                "role": "model",
                "text": "Entendido. Só direi que meu nome é Zippy quando perguntado diretamente sobre isso."
            }
        ]
        salvar_historico(path, historico_inicial)
        return historico_inicial

def converter_para_contents(historico):
    contents = []
    for msg in historico:
        contents.append(
            types.Content(
                role=msg["role"],
                parts=[types.Part.from_text(text=msg["text"])]
            )
        )
    return contents

async def get_proxima_api_key():
    global api_index
    async with api_index_lock:
        key = API_KEYS[api_index]
        api_index = (api_index + 1) % len(API_KEYS)
        return key

# === ROTAS ===

@app.post("/chat")
async def chat(req: ChatRequest):
    await controlar_taxa()
    async with semaforo:
        user_id = verificar_email(req.email)
        if not user_id:
            raise HTTPException(status_code=404, detail="E-mail não encontrado ou erro na verificação.")

        user_path = get_user_path(user_id)
        historico = carregar_historico(user_path)
        historico.append({"role": "user", "text": req.pergunta})
        contents = converter_para_contents(historico)

        if req.web == "on":
            tools = [types.Tool(google_search=types.GoogleSearch())]
        else:
            tools = []

        generate_content_config = types.GenerateContentConfig(
            tools=tools,
            response_mime_type="text/plain",
        )

        api_key = await get_proxima_api_key()
        client = genai.Client(api_key=api_key)

        resposta = ""
        try:
            for chunk in client.models.generate_content_stream(
                model=model,
                contents=contents,
                config=generate_content_config,
            ):
                resposta += chunk.text
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erro com o Gemini: {e}")

        historico.append({"role": "model", "text": resposta})
        salvar_historico(user_path, historico)

        return {"resposta": resposta}

@app.post("/generate-image")
async def generate_image(req: ImageRequest):
    await controlar_taxa()
    async with semaforo:
        user_id = verificar_email(req.email)
        if not user_id:
            raise HTTPException(status_code=404, detail="E-mail não encontrado ou erro na verificação.")

        api_key = await get_proxima_api_key()
        client = genai.Client(api_key=api_key)

        prompt_final = f"{req.prompt} with a 16:9 aspect ratio and 1024x1024 pixels"

        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash-preview-image-generation",
                contents=prompt_final,
                config=types.GenerateContentConfig(
                    temperature=1.5,
                    response_modalities=["IMAGE", "TEXT"],
                )
            )

            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    mime_type = part.inline_data.mime_type or "image/png"
                    data_bytes = part.inline_data.data
                    image_base64 = base64.b64encode(data_bytes).decode("utf-8")
                    data_uri = f"data:{mime_type};base64,{image_base64}"
                    return {"image": data_uri}

            raise HTTPException(status_code=500, detail="Imagem não retornada.")

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erro com o Gemini: {e}")

@app.get("/historico")
def obter_historico(email: str):
    user_id = verificar_email(email)
    if not user_id:
        raise HTTPException(status_code=404, detail="E-mail não encontrado.")

    user_path = get_user_path(user_id)

    try:
        historico = carregar_historico(user_path)

        instrucoes_iniciais = [
            "qual é o seu nome",
            "responda com",
            "responda sempre com",
            "meu nome é zippy",
            "não inclua isso em outras respostas"
        ]

        historico_filtrado = [
            msg for msg in historico
            if not any(instr.lower() in msg["text"].lower() for instr in instrucoes_iniciais)
        ]

        return {"historico": historico_filtrado}
    except Exception as e:
        return JSONResponse(status_code=500, content={"erro": f"Não foi possível carregar o histórico: {e}"})

@app.delete("/apagar-historico")
def apagar_historico(email: str):
    user_id = verificar_email(email)
    if not user_id:
        raise HTTPException(status_code=404, detail="E-mail não encontrado.")

    user_path = get_user_path(user_id)

    try:
        if os.path.exists(user_path):
            os.remove(user_path)
            return {"mensagem": "Histórico apagado com sucesso."}
        else:
            return {"mensagem": "Nenhum histórico encontrado para este usuário."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao apagar o histórico: {e}")

@app.get("/requisicoes-por-minuto")
def obter_requisicoes_por_minuto():
    agora = datetime.utcnow()
    requisicoes_recentes = [t.isoformat() for t in ultimas_requisicoes if (agora - t) < timedelta(seconds=60)]
    return {
        "quantidade": len(requisicoes_recentes),
        "timestamps": requisicoes_recentes
    }

@app.get("/check")
async def check_server():
    return {"status": "ok", "message": "Servidor funcionando corretamente!"}
