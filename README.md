# Bot Cabo de Força — Conector de dados v0.3

Protótipo local de navegador + servidor Python, apenas de leitura. Não liga à conta Quotex, não usa sessão/SSID e não executa operações.

## O que já faz
- Serve um painel local no navegador.
- Verifica se o servidor está ativo e se a chave OTCharts está configurada.
- Obtém catálogo de símbolos Quotex no OTCharts.
- Pede histórico de velas sob demanda (não faz polling repetitivo).\n- Inclui seleção de 5 segundos e gráfico de velas OHLC no painel.\n- Tenta normalizar respostas comuns da API (objetos ou arrays); o formato exato depende da resposta real do fornecedor.
- Encaminha ticks em tempo real via Server-Sent Events (SSE).
- Mostra os últimos preços recebidos.
- Não contém mecanismo de ordens.

## Limitações e aviso
OTCharts é um feed independente, não uma API oficial da Quotex. Antes de utilizar, lê os termos vigentes, confirma com o fornecedor se o uso pretendido é permitido e não redistribuas os dados. O site de termos consultado identificava-os como rascunho. Este projeto não prova que as cotações são idênticas ao terminal da Quotex; a comparação manual por ativo/horário é necessária. Sem chave, o servidor inicia, mas os endpoints do fornecedor ficam indisponíveis.

O painel ainda não gera sinais automáticos Cabo de Força. Esta etapa valida a ligação e os dados. A lógica de sinais deve ser adicionada depois de verificar completude, timestamps, gaps e correspondência das cotações.

## Requisitos
- Python 3.11+ recomendado
- Conta/chave OTCharts válida para o livro `quotex`; o plano gratuito pode não incluir stream em tempo real e tem limites de ativos/pedidos. Confirma os limites atuais antes de usar.
- A chave fica no servidor, nunca no navegador.

## Instalação no Windows
1. Extrai o ZIP para uma pasta, por exemplo `C:\CaboForca`.
2. Instala Python 3.11 ou superior.
3. Abre PowerShell nessa pasta.
4. Cria e ativa o ambiente:
   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```
5. Cria o ficheiro de configuração:
   ```powershell
   Copy-Item .env.example .env
   notepad .env
   ```
6. Cola a chave OTCharts depois de `OTCHARTS_API_KEY=` e guarda. Não partilhes o ficheiro `.env`.
7. Inicia:
   ```powershell
   uvicorn main:app --host 127.0.0.1 --port 8000
   ```
8. Abre `http://127.0.0.1:8000` no Chrome ou Edge.
9. Clica em **Testar servidor**, depois **Carregar ativos Quotex**, escolhe um ativo e carrega as velas. Só depois testa **Iniciar feed ao vivo** se o teu plano permitir streams.

## Instalação macOS/Linux
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edita .env e define OTCHARTS_API_KEY
uvicorn main:app --host 127.0.0.1 --port 8000
```
Depois abre `http://127.0.0.1:8000`.

## API local
- `GET /api/health`
- `GET /api/symbols`
- `GET /api/candles?symbol=EURUSD_otc&tf=60&limit=100`
- `GET /api/stream?symbols=EURUSD_otc,GBPUSD_otc`
- `GET /api/strategy-info`

## Verificação de correspondência OTC
1. Escolhe um instrumento que esteja aberto no terminal e no catálogo do feed.
2. Abre o mesmo ativo OTC no terminal Quotex e no painel.
3. Regista lado a lado, com relógio sincronizado, o horário e OHLC de pelo menos 100 velas fechadas M1 (idealmente em várias sessões).
4. Compara timestamps, OHLC, velas em falta e atrasos. Regista cada divergência; não “corrijas” os dados para forçar correspondência.
5. Faz primeiro observação em demo, sem executar ordens pelo bot. Se os preços ou horários não forem suficientemente próximos, não uses esse feed para gerar sinais.

## Próximas fases
1. Persistência de ticks/velas e verificação de gaps/atrasos.
2. Comparador de cotações com exportação CSV.
3. Especificação objetiva das regras Cabo de Força.
4. Backtesting sem look-ahead e validação fora da amostra.
5. Alertas só depois de validar a qualidade dos dados.
