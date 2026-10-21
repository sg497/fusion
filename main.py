from pathlib import Path
import zipfile

html = r'''<!doctype html>
<html lang="pt">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Cabo de Força — Conector de dados</title>
<style>
:root{color-scheme:dark;--bg:#0b1020;--panel:#131d31;--line:#2c3a55;--muted:#9fb0ca;--text:#eef4ff;--blue:#38bdf8;--green:#4ade80;--red:#fb7185;--gold:#fbbf24}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:15px/1.5 system-ui,Arial}.wrap{max-width:1200px;margin:auto;padding:22px 14px 40px}.top{display:flex;align-items:center;justify-content:space-between;gap:14px;flex-wrap:wrap}.brand{display:flex;gap:12px;align-items:center}.logo{background:#0e7490;border-radius:13px;padding:12px;font-weight:900}.muted{color:var(--muted)}h1{font-size:clamp(23px,4vw,32px);margin:0}h2{font-size:18px;margin:0 0 12px}.pill{border:1px solid #28536a;color:#bae6fd;background:#10253b;border-radius:999px;padding:6px 10px;font-size:12px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:15px;margin-top:18px}.panel{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:17px;min-width:0}label{display:block;font-size:13px;color:#cbd5e1;margin:10px 0 5px}select,input{width:100%;background:#0b1324;border:1px solid #34435e;border-radius:9px;padding:10px;color:var(--text);font:inherit}button{border:0;border-radius:10px;padding:11px 14px;font-weight:700;cursor:pointer}.primary{background:linear-gradient(90deg,#0891b2,#2563eb);color:white}.secondary{background:#263650;color:white;border:1px solid #40516c}.actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:13px}.status{margin-top:12px;padding:11px;border-radius:10px;background:#0b1324;border:1px solid var(--line);font-size:13px;overflow-wrap:anywhere}.good{color:var(--green)}.bad{color:var(--red)}.wait{color:var(--gold)}.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:12px}.metric{background:#0b1324;border:1px solid var(--line);border-radius:10px;padding:10px}.metric b{display:block;font-size:18px;overflow-wrap:anywhere}.metric small{color:var(--muted)}.tablewrap{overflow:auto}table{width:100%;border-collapse:collapse;min-width:700px;font-size:13px}td,th{text-align:left;padding:9px;border-bottom:1px solid var(--line);white-space:nowrap}th{color:var(--muted)}.notice{background:#2b2514;border:1px solid #6b5519;color:#fef3c7;border-radius:11px;padding:12px;font-size:13px;margin-top:14px}.signal{font-weight:900;font-size:22px}.signal.call{color:var(--green)}.signal.put{color:var(--red)}.signal.wait{color:var(--gold)}.footer{font-size:12px;color:var(--muted);margin-top:17px;overflow-wrap:anywhere}@media(max-width:760px){.grid{grid-template-columns:1fr}.cards{grid-template-columns:repeat(3,minmax(0,1fr))}.metric{padding:8px}.metric b{font-size:16px}}
</style>
</head>
<body>
<main class="wrap">
<header class="top"><div class="brand"><div class="logo">CF</div><div><h1>Cabo de Força</h1><div class="muted">Conector OTCharts · Somente leitura</div></div></div><div class="pill">SEM EXECUÇÃO DE ORDENS</div></header>
<div class="grid">
<section class="panel">
<h2>1. Feed de dados</h2><div class="muted">A chave API permanece no servidor.</div>
<div class="actions"><button id="health" class="secondary">Testar servidor</button><button id="load" class="primary">Carregar ativos Quotex</button></div>
<div id="healthStatus" class="status">Estado: ainda não testado.</div>
<label for="symbols">Ativos a monitorizar (seleção múltipla)</label><select id="symbols" multiple size="8"></select>
<label for="tf">Timeframe das velas históricas</label><select id="tf"><option value="60">M1 — 1 minuto</option><option value="300">M5 — 5 minutos</option><option value="900">M15 — 15 minutos</option><option value="1800">M30 — 30 minutos</option><option value="3600">H1 — 1 hora</option></select>
<div class="actions"><button id="history" class="secondary">Carregar velas</button><button id="start" class="primary">Iniciar feed ao vivo</button><button id="stop" class="secondary">Parar</button></div>
<div id="feedStatus" class="status">Feed parado.</div>
</section>
<section class="panel">
<h2>2. Últimos preços recebidos</h2><div class="cards"><div class="metric"><b id="nTicks">0</b><small>Ticks recebidos</small></div><div class="metric"><b id="nSymbols">0</b><small>Ativos com dados</small></div><div class="metric"><b id="lastTime">—</b><small>Último horário</small></div></div>
<div class="tablewrap" style="margin-top:12px"><table><thead><tr><th>Ativo</th><th>Preço</th><th>Hora do feed</th><th>Direção do preço</th></tr></thead><tbody id="ticks"><tr><td colspan="4" class="muted">Sem dados ainda.</td></tr></tbody></table></div>
<div class="notice">O estado do feed mostra a variação do último preço recebido: <span class="good">ALTA</span>, <span class="bad">BAIXA</span> ou <span class="wait">SEM ALTERAÇÃO</span>. No primeiro tick de cada ativo, é necessário aguardar pelo próximo preço para determinar a direção. Isto não representa o volume real de compras e vendas.</div>
</section>
</div>
<section class="panel" style="margin-top:15px">
<h2>3. Verificação das velas e volume</h2>
<div id="candleMeta" class="muted">Escolhe um ativo e carrega o histórico.</div>
<div class="tablewrap" style="margin-top:10px"><table><thead><tr><th>Hora (UTC)</th><th>Abertura</th><th>Máxima</th><th>Mínima</th><th>Fecho</th><th>Volume total</th><th>Volume de alta</th><th>Volume de baixa</th><th>Direção</th></tr></thead><tbody id="candles"><tr><td colspan="9" class="muted">Sem velas.</td></tr></tbody></table></div>
<div id="volumeStatus" class="status">O volume ainda não foi verificado.</div>
</section>
<div class="footer">Feed independente, não oficial e ainda não validado contra o terminal Quotex. Não introduzas credenciais Quotex neste projeto. A chave OTCharts deve permanecer apenas no ficheiro .env do servidor. O protótipo não envia ordens.</div>
</main>
<script>
let source=null,tickCount=0,lastBySymbol={},catalog=[];
const $=id=>document.getElementById(id);
async function api(url){
  const r=await fetch(url);
  const d=await r.json().catch(()=>({detail:'Resposta inválida do servidor'}));
  if(!r.ok)throw Error(d.detail||d.message||`HTTP ${r.status}`);
  return d;
}
function esc(s){return String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function formatNumber(v){
  if(v===null||v===undefined||v==='')return 'Não fornecido';
  const n=Number(v);
  return Number.isFinite(n)?n.toLocaleString('pt-PT',{maximumFractionDigits:8}):String(v);
}
function formatTime(value){
  const n=Number(value);
  if(!Number.isFinite(n))return 'Hora indisponível';
  const date=new Date(n<1e12?n*1000:n);
  return Number.isNaN(date.getTime())?'Hora indisponível':date.toISOString().replace('T',' ').slice(0,19);
}
function getCandleVolume(c){
  const fields=['volume','tick_volume','real_volume','tickVolume','realVolume','vol'];
  for(const field of fields){
    const v=c?.[field];
    if(v===null||v===undefined||v===''||typeof v==='boolean')continue;
    const n=Number(v);
    if(Number.isFinite(n)&&n>=0)return {value:n,field};
  }
  return {value:null,field:null};
}
function analyzeCandle(c){
  const open=Number(c?.open),close=Number(c?.close);
  let direction='INDETERMINADA';
  if(Number.isFinite(open)&&Number.isFinite(close)){
    direction=close>open?'ALTA':close<open?'BAIXA':'NEUTRA';
  }
  const vol=getCandleVolume(c);
  return {
    direction,
    volume:vol.value,
    volumeField:vol.field,
    volumeHigh:direction==='ALTA'?vol.value:null,
    volumeLow:direction==='BAIXA'?vol.value:null
  };
}
$('health').onclick=async()=>{
  try{
    const d=await api('/api/health');
    $('healthStatus').innerHTML=`<span class="${d.api_key_configured?'good':'wait'}">Servidor ${esc(d.status)}; chave ${d.api_key_configured?'configurada':'não configurada'}; ordens ${d.trading_execution?'ativas':'desativadas'}.</span>`;
  }catch(e){$('healthStatus').innerHTML=`<span class="bad">${esc(e.message)}</span>`;}
};
$('load').onclick=async()=>{
  try{
    const d=await api('/api/symbols');
    catalog=Array.isArray(d.symbols)?d.symbols:[];
    $('symbols').innerHTML=catalog.map(s=>`<option value="${esc(s.symbol)}">${esc(s.name||s.symbol)}${s.open===false?' — FECHADO':''}</option>`).join('');
    $('healthStatus').textContent=`Catálogo carregado: ${catalog.length} ativos. Escolhe os ativos marcados como abertos pelo fornecedor.`;
  }catch(e){$('healthStatus').innerHTML=`<span class="bad">${esc(e.message)}</span>`;}
};
function selected(){return [...$('symbols').selectedOptions].map(o=>o.value);}
$('history').onclick=async()=>{
  const symbol=selected()[0];
  if(!symbol){alert('Escolhe pelo menos um ativo.');return;}
  try{
    const tf=$('tf').value;
    $('candleMeta').textContent='A carregar histórico...';
    $('volumeStatus').textContent='A verificar os campos de volume devolvidos pelo servidor...';
    const d=await api(`/api/candles?symbol=${encodeURIComponent(symbol)}&tf=${tf}&limit=50`);
    const bars=Array.isArray(d.candles)?d.candles:[];
    $('candleMeta').textContent=`${d.symbol||symbol} · intervalo ${d.interval??tf+'s'} · ${bars.length} velas · falhas: ${d.gaps?.missingBars??'não informado'} · aberto: ${d.open??'não informado'}`;
    if(!bars.length){
      $('candles').innerHTML='<tr><td colspan="9">O servidor não devolveu velas reconhecidas. Verifica a resposta do fornecedor.</td></tr>';
      $('volumeStatus').innerHTML='<span class="wait">Sem velas para verificar o volume.</span>';
      if(d.diagnostic)$('candleMeta').textContent+=' · '+d.diagnostic;
      return;
    }
    $('candles').innerHTML=bars.slice(-30).reverse().map(c=>{
      const a=analyzeCandle(c);
      const directionClass=a.direction==='ALTA'?'good':a.direction==='BAIXA'?'bad':'wait';
      return `<tr>
        <td>${esc(formatTime(c.time??c.timestamp))}</td>
        <td>${esc(formatNumber(c.open))}</td>
        <td>${esc(formatNumber(c.high))}</td>
        <td>${esc(formatNumber(c.low))}</td>
        <td>${esc(formatNumber(c.close))}</td>
        <td>${esc(formatNumber(a.volume))}</td>
        <td>${esc(formatNumber(a.volumeHigh))}</td>
        <td>${esc(formatNumber(a.volumeLow))}</td>
        <td class="${directionClass}">${esc(a.direction)}</td>
      </tr>`;
    }).join('');
    const withVolume=bars.filter(c=>getCandleVolume(c).value!==null);
    const volumeFields=[...new Set(withVolume.map(c=>getCandleVolume(c).field))];
    if(withVolume.length){
      $('volumeStatus').innerHTML=`<span class="good">Volume recebido em ${withVolume.length}/${bars.length} velas. Campo(s) detetado(s): ${esc(volumeFields.join(', '))}. Volume de alta/baixa classificado pela direção de cada vela.</span>`;
    }else{
      $('volumeStatus').innerHTML='<span class="wait">Nenhum campo de volume reconhecido nas velas. O fornecedor pode não o enviar ou usar outro nome; é necessário inspecionar a resposta original da API.</span>';
    }
    if(d.volume_note)$('volumeStatus').innerHTML+=`<div class="muted">${esc(d.volume_note)}</div>`;
  }catch(e){
    $('candleMeta').textContent=`Erro ao carregar histórico: ${e.message}`;
    $('volumeStatus').innerHTML='<span class="bad">Não foi possível verificar o volume.</span>';
  }
};
$('start').onclick=()=>{
  const ss=selected();
  if(!ss.length){alert('Escolhe pelo menos um ativo.');return;}
  if(source)source.close();
  source=new EventSource('/api/stream?symbols='+encodeURIComponent(ss.join(',')));
  $('feedStatus').textContent='A ligar ao feed...';
  source.addEventListener('connected',e=>{$('feedStatus').innerHTML='<span class="good">Ligado: '+esc(e.data)+'</span>';});
  source.addEventListener('tick', e => {
    try {
      const d = JSON.parse(e.data);
      if (!d.symbol) return;

      const currentPrice = Number(d.price ?? d.close);
      const previous = lastBySymbol[d.symbol];
      const previousPrice = previous
        ? Number(previous.price ?? previous.close)
        : NaN;

      let direction = 'AGUARDANDO PRÓXIMO TICK';
      let directionClass = 'wait';

      if (Number.isFinite(currentPrice)) {
        if (Number.isFinite(previousPrice)) {
          if (currentPrice > previousPrice) {
            direction = 'ALTA';
            directionClass = 'good';
          } else if (currentPrice < previousPrice) {
            direction = 'BAIXA';
            directionClass = 'bad';
          } else {
            direction = 'SEM ALTERAÇÃO';
            directionClass = 'wait';
          }
        }
      } else {
        direction = 'PREÇO INDISPONÍVEL';
        directionClass = 'wait';
      }

      lastBySymbol[d.symbol] = {
        ...d,
        direction,
        directionClass
      };

      tickCount++;
      $('nTicks').textContent = tickCount;
      $('nSymbols').textContent = Object.keys(lastBySymbol).length;
      $('lastTime').textContent =
        formatTime(d.time ?? d.timestamp).slice(11, 19);
      renderTicks();
    } catch (err) {
      console.error('Erro ao processar tick:', err);
    }
  });
  ['dropped','closed','replaced','provider_error','error'].forEach(n=>source.addEventListener(n,e=>{
    $('feedStatus').innerHTML=`<span class="wait">${esc(n)}: ${esc(e.data)}</span>`;
  }));
  source.onerror=()=>{$('feedStatus').innerHTML='<span class="bad">Ligação interrompida ou recusada. Verifica o servidor, o plano e os limites de streams.</span>';};
};
$('stop').onclick=()=>{
  if(source)source.close();
  source=null;
  $('feedStatus').textContent='Feed parado pelo utilizador.';
};
function renderTicks() {
  $('ticks').innerHTML = Object.values(lastBySymbol)
    .sort((a, b) => String(a.symbol).localeCompare(String(b.symbol)))
    .map(t => {
      const directionClass = t.directionClass || 'wait';
      const direction = t.direction || 'AGUARDANDO PRÓXIMO TICK';
      return `
        <tr>
          <td>${esc(t.symbol)}</td>
          <td>${esc(formatNumber(t.price ?? t.close))}</td>
          <td>${esc(formatTime(t.time ?? t.timestamp).slice(11, 19))}</td>
          <td class="${esc(directionClass)}"><strong>${esc(direction)}</strong></td>
        </tr>
      `;
    })
    .join('') ||
    '<tr><td colspan="4" class="muted">Sem dados ainda.</td></tr>';
}
</script>
</body>
</html>
'''

mainpy = r'''import os
import math
import re
import json
from typing import AsyncIterator

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("OTCHARTS_API_KEY", "").strip()
BASE_URL = os.getenv("OTCHARTS_BASE_URL", "https://otcharts.com").rstrip("/")
VENUE = "quotex"
SYMBOL_RE = re.compile(r"^[A-Za-z0-9_#./-]{1,40}$")
TIMEFRAMES = {5, 15, 30, 60, 120, 300, 600, 900, 1800, 3600, 14400, 86400}
VOLUME_FIELDS = ("volume", "tick_volume", "real_volume", "tickVolume", "realVolume", "vol")

app = FastAPI(
    title="Cabo de Força — Data Connector",
    version="0.3.0",
    description="Conector de leitura. Sem login de corretora e sem execução de ordens."
)
app.mount("/static", StaticFiles(directory="static"), name="static")


def require_key():
    if not API_KEY:
        raise HTTPException(
            503,
            "OTCHARTS_API_KEY não configurada. Copia .env.example para .env e adiciona a tua chave."
        )
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
                f"{BASE_URL}{path}",
                params=params,
                headers={
                    "Authorization": f"Bearer {key}",
                    "Accept": "application/json"
                }
            )
        if response.status_code == 401:
            raise HTTPException(502, "OTCharts recusou a chave. Verifica a chave no painel do fornecedor.")
        if response.status_code == 429:
            raise HTTPException(429, "Limite de pedidos OTCharts atingido. Aguarda o reset indicado pelo fornecedor.")
        if response.status_code >= 400:
            raise HTTPException(502, f"OTCharts respondeu HTTP {response.status_code}: {response.text[:250]}")
        try:
            return response.json()
        except ValueError:
            raise HTTPException(502, "OTCharts devolveu uma resposta que não é JSON válido.")
    except httpx.RequestError:
        raise HTTPException(502, "Não foi possível ligar ao OTCharts. Verifica a internet e tenta novamente.")


def numeric_volume(candle: dict):
    """Devolve volume e nome do campo ou None, sem fabricar valores."""
    for field in VOLUME_FIELDS:
        value = candle.get(field)
        if value is None or isinstance(value, bool):
            continue
        try:
            number = float(value)
        except (TypeError, ValueError, OverflowError):
            continue
        if math.isfinite(number) and number >= 0:
            return number, field
    return None, None


def normalize_candles(data, symbol: str, tf: int):
    """Normaliza campos reconhecidos sem inventar volume."""
    if isinstance(data, list):
        bars, metadata = data, {}
    elif isinstance(data, dict):
        bars = data.get("candles")
        metadata = {k: v for k, v in data.items() if k != "candles"}
    else:
        bars, metadata = None, {}

    if not isinstance(bars, list):
        return {
            **metadata,
            "symbol": symbol,
            "interval": tf,
            "candles": [],
            "volume_available": False,
            "diagnostic": (
                "A resposta do fornecedor não contém uma lista reconhecida em 'candles'. "
                "Verifica a estrutura documentada pelo OTCharts."
            ),
        }

    normalized = []
    for original in bars:
        if not isinstance(original, dict):
            continue

        candle = dict(original)
        volume, source_field = numeric_volume(candle)

        try:
            open_price = float(candle["open"])
            close_price = float(candle["close"])
            if not math.isfinite(open_price) or not math.isfinite(close_price):
                raise ValueError
        except (KeyError, TypeError, ValueError, OverflowError):
            direction = "INDETERMINADA"
        else:
            direction = "ALTA" if close_price > open_price else "BAIXA" if close_price < open_price else "NEUTRA"

        candle["direction"] = direction
        candle["volume"] = volume
        candle["volume_source_field"] = source_field
        candle["volume_high"] = volume if direction == "ALTA" else None
        candle["volume_low"] = volume if direction == "BAIXA" else None
        normalized.append(candle)

    volume_count = sum(c["volume"] is not None for c in normalized)
    return {
        **metadata,
        "symbol": symbol,
        "interval": metadata.get("interval", tf),
        "candles": normalized,
        "volume_available": volume_count > 0,
        "volume_candles_count": volume_count,
        "volume_note": (
            "O volume de alta/baixa é o volume reportado da vela classificado "
            "pela direção do fecho. Não representa necessariamente compras e vendas reais."
        ),
    }


@app.get("/")
async def home():
    return FileResponse("static/index.html")


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "provider": "OTCharts",
        "venue": VENUE,
        "api_key_configured": bool(API_KEY),
        "trading_execution": False
    }


@app.get("/api/symbols")
async def symbols():
    return await otc_get("/v1/symbols", {"venue": VENUE})


@app.get("/api/candles")
async def candles(
    symbol: str,
    tf: int = Query(60, ge=5),
    limit: int = Query(100, ge=1, le=500)
):
    symbol = safe_symbol(symbol)
    if tf not in TIMEFRAMES:
        raise HTTPException(400, f"Timeframe não permitido. Opções: {sorted(TIMEFRAMES)}")
    data = await otc_get(
        "/v1/candles",
        {"venue": VENUE, "symbol": symbol, "tf": tf, "limit": limit}
    )
    return normalize_candles(data, symbol, tf)


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
                        yield (
                            "event: provider_error\n"
                            + "data: "
                            + json.dumps({
                                "status": response.status_code,
                                "message": "OTCharts não aceitou o stream; verifica plano, símbolos e limite de ligações."
                            })
                            + "\n\n"
                        )
                        return

                    event_name = "message"
                    data_lines = []
                    async for line in response.aiter_lines():
                        if not line:
                            if data_lines:
                                payload = "\n".join(data_lines)
                                if event_name in {
                                    "connected", "tick", "dropped", "closed",
                                    "replaced", "error", "provider_error"
                                }:
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
            yield (
                "event: provider_error\n"
                + "data: "
                + json.dumps({"message": "A ligação ao feed foi interrompida. Tenta ligar novamente."})
                + "\n\n"
            )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


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
'''

outdir = Path("/mnt/data/cabo_de_forca_corrigido")
(outdir / "static").mkdir(parents=True, exist_ok=True)
(outdir / "main.py").write_text(mainpy, encoding="utf-8")
(outdir / "static" / "index.html").write_text(html, encoding="utf-8")
(outdir / "requirements.txt").write_text("fastapi\nuvicorn[standard]\nhttpx\npython-dotenv\n", encoding="utf-8")
(outdir / ".env.example").write_text(
    "OTCHARTS_API_KEY=COLOCA_A_TUA_CHAVE_AQUI\nOTCHARTS_BASE_URL=https://otcharts.com\n",
    encoding="utf-8"
)

zip_path = Path("/mnt/data/cabo_de_forca_corrigido.zip")
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
    for p in outdir.rglob("*"):
        if p.is_file():
            z.write(p, p.relative_to(outdir.parent))

print("Projeto atualizado com a direção ALTA/BAIXA do preço no feed.")
print(f"HTML: {outdir / 'static' / 'index.html'}")
print(f"Servidor: {outdir / 'main.py'}")
print(f"ZIP: {zip_path}")
