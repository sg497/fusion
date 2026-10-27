    if isinstance(raw, dict):
        pairs = raw.get("data", [])
    elif isinstance(raw, list):
        pairs = raw
    else:
        pairs = []

    if not isinstance(pairs, list):
        pairs = []

    market_open = forex_market_open_approx()
    adapted = []
    for pair in pairs:
        if not isinstance(pair, dict):
            continue
        symbol = pair.get("symbol") or pair.get("ticker")
        if not isinstance(symbol, str) or not symbol.strip():
            continue
        symbol = symbol.strip()
        base = pair.get("currency_base", "")
        quote = pair.get("currency_quote", "")
        name = pair.get("name") or (f"{base}/{quote}" if base and quote else symbol)
        adapted.append({
            **pair,
            "symbol": symbol,
            "name": name,
            # Campo compatível com o frontend. É uma estimativa geral do horário Forex,
            # não um estado de mercado fornecido diretamente pela Twelve Data.
            "is_open": market_open,
            "available": True,
        })

    return {
        "provider": "Twelve Data",
        "count": len(adapted),
        "market_open_approx": market_open,
        "data": adapted,
        # Alias para interfaces que procuram uma propriedade chamada "symbols".
        "symbols": adapted,
    }


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
            "Timeframe não suportado. Usa: " + ", ".join(str(x) for x in TIMEFRAMES) + " segundos.",
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
    if not isinstance(data, dict) or "values" not in data:
        raise HTTPException(502, "A Twelve Data não devolveu velas para este símbolo.")
    return data


@app.get("/api/stream")
async def stream(symbols: str = Query(..., min_length=1, max_length=1000)):
    names = [normalize_symbol(s) for s in symbols.split(",") if s.strip()]
    if not names or len(names) > 10 or len(set(names)) != len(names):
        raise HTTPException(400, "Indica entre 1 e 10 símbolos únicos.")
    require_key()

    async def event_generator() -> AsyncIterator[str]:
        while True:
            try:
                # Consultar individualmente para evitar assumir suporte a símbolos em lote.
                for name in names:
                    data = await td_get(
                        "/time_series",
                        {
                            "symbol": name,
                            "interval": "1min",
                            "outputsize": 1,
                            "timezone": "UTC",
                        },
                    )
                    values = data.get("values", []) if isinstance(data, dict) else []
                    if values:
                        payload = {"symbol": name, "meta": data.get("meta", {}), "candle": values[0]}
                        yield "event: tick\n" + f"data: {json.dumps(payload)}\n\n"
            except HTTPException as exc:
                payload = {"status": exc.status_code, "message": exc.detail}
                yield "event: provider_error\n" + f"data: {json.dumps(payload)}\n\n"
                if exc.status_code in (401, 403, 429, 503):
                    return
            except Exception:
                yield "event: provider_error\n" + 'data: {"message":"Falha ao consultar a Twelve Data."}\n\n'
            await asyncio.sleep(15)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
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
