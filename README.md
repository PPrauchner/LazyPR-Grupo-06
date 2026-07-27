<h1 align="center">LazyPR</h1>

<p align="center">
  <strong>Análise semântica do histórico de contribuições em projetos open source</strong><br>
  Programação funcional em Python + classificação por LLM sobre datasets de milhões de registros.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.12-3776AB?logo=python&logoColor=white" alt="Python 3.12">
  <img src="https://img.shields.io/badge/streamlit-1.57-FF4B4B?logo=streamlit&logoColor=white" alt="Streamlit">
  <img src="https://img.shields.io/badge/uv-managed-DE5FE9?logo=uv&logoColor=white" alt="uv">
  <img src="https://img.shields.io/badge/groq-llama--3.1--8b-F55036?logo=groq&logoColor=white" alt="Groq">
  <img src="https://img.shields.io/badge/paradigma-funcional-4B8BBE" alt="Programação Funcional">
</p>

---

<!-- TODO: substituir pela captura real do dashboard (página Overview com dados carregados) -->
<p align="center"><em>— captura do dashboard a incluir —</em></p>

## O problema

Projetos no GitHub acumulam históricos de pull requests com informação valiosa sobre
qualidade de contribuição e dinâmica de revisão. Datasets públicos como o
[GitHub Public Pull Request Comments](https://www.kaggle.com/datasets/pelmers/github-public-pull-request-comments)
têm milhões de registros heterogêneos — de correções triviais a reestruturações
complexas. Análise manual é inviável.

O LazyPR resolve isso com três decisões:

**Ingestão preguiçosa.** O dataset é percorrido linha a linha por geradores; o hash
SHA-256 do arquivo é calculado na mesma passagem de I/O. Nada é carregado inteiro em
memória.

**Núcleo funcional puro.** Limpeza, normalização, filtragem e agregação são funções
puras compostas por `map`, `filter` e `reduce`. Todo efeito colateral — arquivo, rede,
LLM, interface — vive numa camada separada.

**LLM apenas para semântica.** O modelo classifica; ele não processa dados. Toda
limpeza, métrica, agrupamento e agregação é código próprio. Classificações são
memoizadas em disco por hash, então um dataset já analisado nunca volta ao LLM.

## Quickstart

Requer [uv](https://github.com/astral-sh/uv) e uma chave gratuita do
[Groq](https://console.groq.com/keys).

```bash
git clone https://github.com/PPrauchner/LazyPR-Grupo-06.git
cd LazyPR-Grupo-06

uv sync

cp .env.example .env        # preencha GROQ_API_KEY
streamlit run main.py       # abre em http://localhost:8501
```

| Variável | Padrão | Obrigatória |
|---|---|:-:|
| `GROQ_API_KEY` | — | ✅ |
| `LAZYPR_MAX_BODY_CHARS` | `1500` | — |
| `CACHE_DIR` | `.cache` | — |

## Como funciona

```
 CSV/JSON ──► services/ingestion.py ──► PRRecord (stream lazy)
                                              │
                    ╭─────────────────────────┴─────────────────────────╮
                    │            core/  ·  funções puras                │
                    │   limpeza → normalização → filtragem              │
                    ╰─────────────────────────┬─────────────────────────╯
                                              │
                    ╭─────────────────────────┴─────────────────────────╮
                    │      services/  ·  efeitos colaterais isolados    │
                    │   Groq: tipo de projeto · natureza · clareza      │
                    │   cache SHA-256 em disco, escrita atômica         │
                    ╰─────────────────────────┬─────────────────────────╯
                                              │
                              AnalysisResult ──► core/aggregations/
                                                        │
                                              ui/ + views/ ──► dashboards
```

O pipeline é configurável por etapa: cada uma pode ser ligada ou desligada sem tocar
no código das transformações.

**Rate limiting.** O plano gratuito do Groq permite 30 requisições por minuto. O
LazyPR agrupa os registros de um mesmo repositório numa única chamada, unifica
natureza e clareza num só JSON, e aplica throttle de 2,1 s — 50 registros são
analisados em cerca de 2 minutos. Em erro 429, o tempo de espera sugerido pela API é
extraído da mensagem e respeitado, com até 6 tentativas em backoff exponencial.

## Histórias de Usuário

| # | Como analista, quero… | Implementação |
|:-:|---|---|
| 01 | fazer upload de datasets para análise | `views/upload.py` · `services/ingestion.py` |
| 02 | categorizar cada repositório por tipo de projeto | `services/classifiers.py::classify_project_type` |
| 03 | categorizar cada PR por natureza da contribuição | `services/classifiers.py::classify_pr_nature` |
| 04 | avaliar a clareza da descrição | `services/classifiers.py::classify_clarity` |
| 05 | ver volume estratificado por linguagem, tipo e natureza | `views/overview.py` · `core/aggregations/counters.py` |
| 06 | ver a distribuição de tamanho da descrição | `core/aggregations/metrics.py` · `ui/charts.py` |
| 07 | ver a relação entre clareza, tipo, natureza e linguagem | `views/correlations_dashboard.py` · `core/aggregations/correlations.py` |
| 08 | filtrar todas as visualizações por qualquer critério | `ui/sidebar_filters.py` · `core/transforms/filtering.py` |
| 09 | exportar os resultados em CSV e JSON | `views/export.py` · `services/exporters.py` |

## Onde cada regra do enunciado vive

| Regra | Onde |
|---|---|
| **RG 02** — ingestão lazy por geradores | `services/ingestion.py::stream_csv` — `yield from map(...)` com hash na mesma passagem |
| **RG 03** — classificação por LLM | `services/llm_client.py` · `services/classifiers.py` |
| **RG 04** — análises persistidas | `services/storage.py` — JSON atômico indexado por SHA-256 |
| **RG 05** — pipeline configurável de ordem superior | `core/pipeline/runner.py` · `core/pipeline/composer.py` |
| **RG 06** — LLM isolado, sem processar dados | `services/` — `language` vem da extensão do arquivo, não do LLM |
| **RG 07** — funções puras e estruturas imutáveis | `core/` — `NamedTuple`, `tuple`, `frozenset`, `MappingProxyType` |
| **RG 08** — interface gráfica | `main.py` · `views/` · `ui/` |
| **RF 04** — avaliação preguiçosa | geradores de ponta a ponta; a exceção está em [ADR 0001](docs/adr/0001-materializacao-do-stream-no-agrupamento-por-repositorio.md) |
| **RF 05** — memoização | `utils/memoization.py` · `@lru_cache` em `core/transforms/normalizing.py` |
| **RF 06** — composição de funções | `core/pipeline/composer.py` — `compose()` e `pipe()` |

## Estrutura

```
core/          Functional Core — funções puras, sem I/O
  models/        PRRecord, AnalysisResult (NamedTuple imutáveis)
  pipeline/      composição e execução configurável de etapas
  transforms/    limpeza · filtragem · normalização
  aggregations/  contagens · agrupamentos · métricas · correlações
  validators/    validação do schema do dataset
services/      Imperative Shell — ingestão, LLM, cache, exportação
ui/            componentes, gráficos, tema, filtros da sidebar
views/         páginas do Streamlit
utils/         hashing e memoização
tests/         pytest — foco nas funções puras
```

## Desenvolvimento

```bash
uv run pytest tests/                                    # testes
uv run pytest tests/ --cov=core --cov-report=term-missing
uv run black .                                          # formatação (line-length 88)
```

## Documentação

| Documento | Conteúdo |
|---|---|
| [`CONTEXT.md`](CONTEXT.md) | glossário de domínio — o vocabulário do projeto |
| [`CLAUDE.md`](CLAUDE.md) | arquitetura detalhada, contratos entre camadas, estado de conformidade |
| [`docs/adr/`](docs/adr/) | decisões arquiteturais e seus porquês |
| [`.claude/rules/`](.claude/rules/) | convenções de código e restrições do projeto |

## Equipe

**Grupo 06** — Residência em Programação III · Escola Politécnica de Pernambuco

| Membro | GitHub |
|---|---|
| Pietro Mendes Prauchner | [@PPrauchner](https://github.com/PPrauchner) |
| Inaurrara Flores Rozado | [@Inaurrara](https://github.com/Inaurrara) |
| Lorenzo Ficher | [@lorenzoficher](https://github.com/lorenzoficher) |
| Luiz Hermano | [@LuizHerm](https://github.com/LuizHerm) |
| Rafael Lopes | [@rjnlopes03](https://github.com/rjnlopes03) |

Orientação: [@paulosevero](https://github.com/paulosevero) · [@sequincozes](https://github.com/sequincozes)
