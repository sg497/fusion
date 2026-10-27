
import os
import json
import re
import asyncio
from typing import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("TWELVE_DATA_API_KEY", "").strip()
BASE_URL = os.getenv(
    "TWELVE_DATA_BASE_URL", "https://api.twelvedata.com"
).rstrip("/")

SYMBOL_RE = re.compile(r"^[A-Za-z0-9_#./:-]{1,40}$")

# Timeframes suportados pela Twelve Data, em segundos.
TIMEFRAMES = {
    60: "1min",
    300: "5min",
    900: "15min",
    1800: "30min",
    3600: "1h",
    7200: "2h",
    14400: "4h",
    28800: "8h",
    86400: "1day",
}

app = FastAPI(
    title="Cabo de Força — Data Connector",
    version="0.4.0",
    description="Conector somente de leitura para dados da Twelve Data."
)

app.mount("/static", StaticFiles(directory="static"), name="static")


def require_key():
    if not API_KEY:
        raise HTTPException(
            503,
            "TWELVE_DATA_API_KEY não configurada no ambiente do servidor."
        )
    return API_KEY


def safe_symbol(symbol: str) -> str:
    symbol = symbol.strip()
    if not SYMBOL_RE.fullmatch(symbol):
        raise HTTPException(400, "Símbolo inválido.")
    return symbol


def normalize_symbol(symbol: str) -> str:
    # EURUSD passa a EUR/USD; EUR/USD mantém-se igual.
    symbol = safe_symbol(symbol)
    if "/" not in symbol and len(symbol) == 6 and symbol.isalpha():
        return symbol[:3] + "/" + symbol[3:]
    return symbol


async def td_get(path: str, params: dict | None = None):
    key = require_key()
    query = dict(params or {})
    query["apikey"] = key

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(
                f"{BASE_URL}{path}",
                params=query,
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            data = response.json()

    except httpx.TimeoutException:
        raise HTTPException(504, "A Twelve Data demorou demasiado a responder.")
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            502,
            f"Twelve Data respondeu HTTP {exc.response.status_code}."
        )
    except (httpx.RequestError, ValueError):
        raise HTTPException(
            502, "Não foi possível obter uma resposta válida da Twelve Data."
        )

    if isinstance(data, dict) and data.get("status") == "error":
        message = str(data.get("message", "Erro do fornecedor"))
        code = data.get("code")

        if code in (401, 403):
            raise HTTPException(502, "Chave inválida ou acesso não autorizado.")
        if code == 429:
            raise HTTPException(429, "Limite de utilização da Twelve Data atingido.")

        raise HTTPException(502, f"Twelve Data: {message[:200]}")

    return data


@app.get("/")
async def home():
    return FileResponse("static/index.html")


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "provider": "Twelve Data",
        "market": "Forex e outros instrumentos suportados",
        "api_key_configured": bool(API_KEY),
        "trading_execution": False,
    }


@app.get("/api/symbols")
async def symbols():
    return await td_get("/forex_pairs")


@app.get("/api/candles")
async def candles(
    symbol: str,
    tf: int = Query(60, ge=5),
    limit: int = Query(100, ge=1, le=500),
):
    symbol = normalize_symbol(symbol)

    if tf not in TIMEFRAMES:
        raise HTTPException(
            400,
            "Timeframe não suportado. Usa: "
            + ", ".join(str(x) for x in TIMEFRAMES)
            + " segundos."
        )

    data = await td_get(
        "/time_series",
        {
            "symbol": symbol,
            "interval": TIMEFRAMES[tf],
            "outputsize": limit,
            "order": "asc",
            "timezone": "UTC",
        },
    )

    # A Twelve Data devolve velas em "values".
    # Mantemos meta e values para facilitar a integração com o frontend.
    if not isinstance(data, dict) or "values" not in data:
        raise HTTPException(
            502, "A Twelve Data não devolveu velas para este símbolo."
        )

    return data


@app.get("/api/stream")
async def stream(
    symbols: str = Query(..., min_length=1, max_length=1000)
):
    names = [
        normalize_symbol(s)
        for s in symbols.split(",")
        if s.strip()
    ]

    if (
        not names
        or len(names) > 10
        or len(set(names)) != len(names)
    ):
        raise HTTPException(
            400, "Indica entre 1 e 10 símbolos únicos."
        )

    require_key()

    async def event_generator() -> AsyncIterator[str]:
        # Polling: não é um feed WebSocket nem uma cotação OTC.
        while True:
            try:
                data = await td_get(
                    "/time_series",
                    {
                        "symbol": ",".join(names),
                        "interval": "1min",
                        "outputsize": 1,
                        "timezone": "UTC",
                    },
                )

                # Resposta de um símbolo ou resposta em lote.
                if len(names) == 1:
                    results = {names[0]: data}
                else:
                    results = data if isinstance(data, dict) else {}

                for name in names:
                    item = results.get(name)
                    if not isinstance(item, dict):
                        continue

                    values = item.get("values", [])
                    if values:
                        payload = {
                            "symbol": name,
                            "meta": item.get("meta", {}),
                            "candle": values[0],
                        }
                        yield (
                            "event: tick\n"
                            f"data: {json.dumps(payload)}\n\n"
                        )

            except HTTPException as exc:
                payload = {
                    "status": exc.status_code,
                    "message": exc.detail,
                }
                yield (
                    "event: provider_error\n"
                    f"data: {json.dumps(payload)}\n\n"
                )

                if exc.status_code in (401, 403, 429, 503):
                    return

            except Exception:
                yield (
                    "event: provider_error\n"
                    'data: {"message":"Falha ao consultar a Twelve Data."}\n\n'
                )

            # Intervalo conservador para limitar o consumo de créditos.
            await asyncio.sleep(15)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/strategy-info")
async def strategy_info():
    return {
        "name": "Cabo de Força",
        "status": "experimental",
        "provider": "Twelve Data",
        "rules": [
            "Só avaliar velas fechadas.",
            "Confirmar estrutura e força direcional.",
            "Verificar a qualidade e atualidade dos dados.",
            "Bloquear sinais quando houver dados em falta ou erros.",
            "Os dados Forex não equivalem às cotações OTC da Quotex.",
            "Sinais não garantem vitórias nem rentabilidade.",
        ],
        "execution": "disabled",
    }
