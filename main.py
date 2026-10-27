import os, json, re, time
from typing import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("OTCHARTS_API_KEY", "").strip()
BASE_URL = os.getenv("OTCHARTS_BASE_URL", "https://otcharts.com").rstrip("/")
VENUE = "quotex"
SYMBOL_RE = re.compile(r"^[A-Za-z0-9_#./-]{1,40}$")
TIMEFRAMES = {5, 15, 30, 60, 120, 180, 300, 600, 900, 1800, 3600, 14400, 86400}

app = FastAPI(title="Cabo de Força — Data Connector", version="0.3.0",
              description="Read-only connector. No broker login and no order execution.")
app.mount("/static", StaticFiles(directory="static"), name="static")

def require_key():
    if not API_KEY:
        raise HTTPException(503, "OTCHARTS_API_KEY não configurada. Copia .env.example para .env e adiciona a tua chave.")
    return API_KEY

def safe_symbol(symbol: str) -> str:
    if not SYMBOL_RE.fullmatch(symbol):
        raise HTTPException(400, "Símbolo inválido.")
    return symbol

async def otc_get(path: str, params: dict | None = None):
    key = require_key()
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"{BASE_URL}{path}", params=params,
                headers={"Authorization": f"Bearer {key}", "Accept": "application/json"}
            )
        if response.status_code == 401:
            raise HTTPException(502, "OTCharts recusou a chave. Verifica a chave no painel do fornecedor.")
        if response.status_code == 429:
            raise HTTPException(429, "Limite de pedidos OTCharts atingido. Aguarda o reset indicado pelo fornecedor.")
        if response.status_code >= 400:
            raise HTTPException(502, f"OTCharts respondeu HTTP {response.status_code}: {response.text[:250]}")
        return response.json()
    except httpx.RequestError:
        raise HTTPException(502, "Não foi possível ligar ao OTCharts. Verifica a internet e tenta novamente.")

@app.get("/")
async def home():
    return FileResponse("static/index.html")

@app.get("/api/health")
async def health():
    return {"status": "ok", "provider": "OTCharts", "venue": VENUE,
            "api_key_configured": bool(API_KEY), "trading_execution": False}

@app.get("/api/symbols")
async def symbols():
    data = await otc_get("/v1/symbols", {"venue": VENUE})
    return data

@app.get("/api/candles")
async def candles(symbol: str, tf: int = Query(60, ge=5), limit: int = Query(100, ge=1, le=500)):
    symbol = safe_symbol(symbol)
    if tf not in TIMEFRAMES:
        raise HTTPException(400, f"Timeframe não permitido. Opções: {sorted(TIMEFRAMES)}")
    data = await otc_get("/v1/candles", {"venue": VENUE, "symbol": symbol, "tf": tf, "limit": limit})
    # Fail closed on data gaps or closed instrument; callers can inspect metadata.
    return data

@app.get("/api/stream")
async def stream(symbols: str = Query(..., min_length=1, max_length=1000)):
    names = [safe_symbol(s.strip()) for s in symbols.split(",") if s.strip()]
    if not names or len(names) > 50 or len(set(names)) != len(names):
        raise HTTPException(400, "Indica entre 1 e 50 símbolos únicos.")
    key = require_key()

    async def event_generator() -> AsyncIterator[str]:
        params = {"venue": VENUE, "symbol": ",".join(names)}
        headers = {"Authorization": f"Bearer {key}", "Accept": "text/event-stream"}
        try:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream("GET", f"{BASE_URL}/v1/stream", params=params, headers=headers) as response:
                    if response.status_code >= 400:
                        yield f"event: provider_error\ndata: {json.dumps({'status': response.status_code, 'message': 'OTCharts não aceitou o stream; verifica plano, símbolos e limite de ligações.'})}\n\n"
                        return
                    event_name = "message"
                    data_lines = []
                    async for line in response.aiter_lines():
                        if not line:
                            if data_lines:
                                payload = "\n".join(data_lines)
                                # Keep only provider events needed by the read-only dashboard.
                                if event_name in {"connected", "tick", "dropped", "closed", "replaced", "error"}:
                                    yield f"event: {event_name}\ndata: {payload}\n\n"
                                data_lines = []
                                event_name = "message"
                            continue
                        if line.startswith(":"):
                            continue
                        if line.startswith("event:"):
                            event_name = line[6:].strip()
                        elif line.startswith("data:"):
                            data_lines.append(line[5:].strip())
        except Exception:
            yield f"event: provider_error\ndata: {json.dumps({'message':'A ligação ao feed foi interrompida. Tenta ligar novamente.'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

@app.get("/api/strategy-info")
async def strategy_info():
    return {
        "name": "Cabo de Força",
        "status": "experimental",
        "rules": [
            "Só avalia velas fechadas.",
            "Requer estrutura/contexto e força direcional definidos.",
            "Requer rejeição no lado oposto e confirmação posterior.",
            "Dados em falta, atrasados, com gaps ou ativo fechado devem bloquear sinais.",
            "Sinais não representam probabilidade de vitória nem promessa de rentabilidade."
        ],
        "execution": "disabled"
    }
