# Chess Game Analyzer

Backend FastAPI para importar partidas públicas do Chess.com ou PGNs colados pelo usuário, analisar posições com Stockfish 18 via UCI, classificar erros, explicar lances críticos e sugerir estudos personalizados.

## Funcionalidades

- Importa partidas públicas pela Chess.com Published Data API sem login.
- Filtros por mês/ano, controle de tempo, cor, resultado e rating.
- Upload ou colagem de PGN com validação e extração de metadados.
- Integração local com Stockfish por `STOCKFISH_PATH`.
- Análise por lance com melhor lance, avaliação antes/depois, perda em centipawns, mate score e PV.
- Classificação inicial: Best, Excellent, Good, Inaccuracy, Mistake, Blunder, Missed Win, Forced e Book move.
- Explicações baseadas em avaliação, PV, material, segurança do rei e padrões detectáveis.
- Relatório com precisão estimada, contagens de erros, momento crítico, maior erro, fase mais problemática e curva de avaliação.
- Plano de estudos agrupado por abertura, tática, estratégia, finais e gerenciamento de tempo.
- Interface Streamlit mais amigável com busca de partidas públicas do Chess.com, painel de histórico com botão **Analizar** por partida, tabuleiro recriado a partir do PGN, navegação lance a lance, cartões de lances críticos e plano de estudo.

## Requisitos

- Python 3.12+
- Stockfish 18 instalado localmente
- SQLite por padrão; a camada usa SQLAlchemy e aceita `DATABASE_URL` para futura migração a PostgreSQL.

## Instalando Stockfish 18

### Linux

Baixe o binário oficial em <https://stockfishchess.org/download/> ou use o pacote da sua distribuição quando ele já estiver na versão desejada. Exemplo manual:

```bash
mkdir -p ~/bin/stockfish18
# descompacte o pacote baixado do Stockfish 18 nesse diretório
chmod +x ~/bin/stockfish18/stockfish
export STOCKFISH_PATH=~/bin/stockfish18/stockfish
```

### macOS

```bash
brew install stockfish
export STOCKFISH_PATH=$(which stockfish)
```

Se o Homebrew ainda não fornecer Stockfish 18, baixe o binário oficial e aponte `STOCKFISH_PATH` para ele.

### Windows

Baixe o `.zip` oficial, extraia o executável e configure:

```powershell
setx STOCKFISH_PATH "C:\\tools\\stockfish\\stockfish-windows-x86-64-avx2.exe"
```

## Configuração

Copie o arquivo de exemplo:

```bash
cp .env.example .env
```

Variáveis principais:

```env
DATABASE_URL=sqlite:///./data/chess_analyzer.db
STOCKFISH_PATH=/caminho/para/stockfish
STOCKFISH_DEPTH=16
STOCKFISH_MULTIPV=3
# STOCKFISH_MOVE_TIME_MS=500
```

## Rodando localmente

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Acesse:

- API: <http://localhost:8000>
- Swagger: <http://localhost:8000/docs>

## Interface Streamlit

Com a API rodando:

```bash
streamlit run frontend/streamlit_app.py
```

Acesse <http://localhost:8501>. A interface permite colar PGN, buscar partidas públicas do Chess.com por username, escolher no painel qual partida analisar e revisar a análise em um tabuleiro navegável reconstruído diretamente do PGN salvo.


### Revisão visual da partida

No modo Chess.com, informe apenas o username e clique em **Buscar partidas**. O app mostra um painel de histórico com jogadores, resultado, controle de tempo, data e um botão **Analizar** em cada linha; apenas a partida escolhida é enviada para o Stockfish. Depois de analisar um PGN ou uma partida do painel, abra o `game_id` no Streamlit. A aba **Tabuleiro** reconstrói a partida inteira a partir do PGN salvo, permite navegar lance a lance, alternar orientação entre brancas/pretas e mostra ao lado a avaliação, melhor lance, temas e explicação do lance selecionado. A tela de revisão usa um layout inspirado no Chess.com, com tabuleiro grande à esquerda, jogadores/relógios, barra de avaliação, painel lateral de treinador, lista de lances, gráfico de avaliação e controles de navegação. No tabuleiro, a seta vermelha marca o lance jogado e a seta verde mostra a melhor opção do Stockfish. O painel lateral tem botões funcionais para melhor lance, explicação, próximo lance, controles de início/voltar/avançar/fim, atalhos de teclado ←/→/Home/End e uma lista de lances dinâmica com rolagem. O painel lateral de **Lances críticos** e a aba **Plano de estudo** transformam o JSON bruto em cartões e sugestões mais fáceis de entender.

## Docker Compose

O projeto já está configurado para subir API, banco SQLite persistido em volume Docker e frontend Streamlit com um único comando.

```bash
cd chess-game-analyzer
cp .env.docker.example .env
docker compose up --build
```

Serviços:

- API em <http://localhost:8000>
- Swagger em <http://localhost:8000/docs>
- Streamlit em <http://localhost:8501>
- Dados persistidos no volume Docker `chess-game-analyzer_chess_data`

Comandos úteis:

```bash
# Ver status e healthcheck
docker compose ps

# Ver logs da API
docker compose logs -f api

# Verificar health check
curl http://localhost:8000/health

# Parar os containers mantendo o volume de dados
docker compose down

# Remover containers e volume SQLite/PGNs armazenados
docker compose down -v
```

Variáveis que você pode ajustar no `.env` antes de subir:

```env
API_PORT=8000
FRONTEND_PORT=8501
STOCKFISH_DEPTH=16
STOCKFISH_MULTIPV=3
STOCKFISH_PATH=/usr/games/stockfish
```

> Observação: o `Dockerfile` instala o pacote `stockfish` da distribuição Debian. Verifique a versão com `docker compose exec api /usr/games/stockfish` e substitua a imagem/binário se precisar garantir exatamente Stockfish 18.

## Exemplos de uso

### Health check

```bash
curl http://localhost:8000/health
```

### Analisar PGN colado

```bash
curl -X POST http://localhost:8000/analyze/pgn \
  -H 'Content-Type: application/json' \
  -d '{
    "pgn": "[Event \"Casual\"]\n[Site \"Local\"]\n[Date \"2024.01.01\"]\n[White \"Alice\"]\n[Black \"Bob\"]\n[Result \"1-0\"]\n\n1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 1-0",
    "max_moves": 12
  }'
```

### Listar partidas públicas do Chess.com antes de analisar

```bash
curl "http://localhost:8000/players/hikaru/chesscom-public-games?limit=20"
```

A interface Streamlit usa essa lista para mostrar o painel de partidas e só envia ao Stockfish a linha em que você clicar **Analizar**. Se quiser fazer o mesmo por API, pegue o `pgn` de uma partida retornada e envie para:

```bash
curl -X POST http://localhost:8000/analyze/chesscom/game \
  -H 'Content-Type: application/json' \
  -d '{
    "username": "hikaru",
    "url": "https://www.chess.com/game/live/...",
    "pgn": "[Event ...]",
    "max_moves": 20
  }'
```

### Consultar relatório

```bash
curl http://localhost:8000/games/1/report
```

### Listar partidas de um jogador

```bash
curl http://localhost:8000/players/hikaru/games
```

### Consultar plano de estudo agregado

```bash
curl http://localhost:8000/players/hikaru/study-plan
```

## Testes

```bash
pytest
ruff check .
```

Os testes unitários não exigem Stockfish real; a integração real é exercida quando você chama os endpoints com `STOCKFISH_PATH` configurado.

## Limitações conhecidas

- A precisão é uma estimativa simples baseada em perda média de centipawns, não a métrica proprietária de nenhum site.
- A detecção temática é heurística e conservadora; ela evita inventar causas quando só há avaliação/PV.
- A identificação de livro de abertura usa uma heurística curta nos primeiros plies, não uma base ECO completa.
- Dados de gerenciamento de tempo por lance dependem de relógios no PGN e ainda são tratados apenas como recomendação genérica.
- A API Chess.com é pública e pode impor limites/rate limits; o cliente usa `User-Agent` configurável.
