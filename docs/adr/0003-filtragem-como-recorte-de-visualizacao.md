# Filtragem é recorte de visualização, não etapa do Pipeline

O `CONTEXT.md` listava filtragem como Etapa, e `run_pipeline` a executava antes da
classificação lendo os predicados de `st.session_state` — o que fazia `core/`
importar `ui/` e violar a Regra Específica 02. A consequência de dados era pior
que a violação de camada: com `enable_filtering` ligado por padrão, os filtros
marcados na sidebar no momento do upload recortavam o stream **antes** da
persistência, e a Análise era gravada sob o hash do dataset **inteiro**. Decidimos
que filtragem é **Filtro de Visualização**: aplicada sobre a Análise já carregada,
nunca sobre o stream que será persistido.

## Considered Options

- **Manter como Etapa, incluindo os filtros na chave do cache** — preserva a
  economia de chamadas ao LLM (filtrar antes de classificar reduz o volume), e
  corrige a colisão. Mas o analista passa a acumular N análises parciais do mesmo
  dataset, e a Regra Geral 04 fica ambígua sobre o que significa "a análise de um
  dataset".
- **Dois conceitos distintos** — um Filtro de Ingestão explícito, que entra na
  chave do cache, e um Filtro de Visualização na sidebar. Mais poderoso e mais
  honesto, mas dobra a superfície de interface e de vocabulário para algo que a
  HU 08 não pede.
- **Apenas Filtro de Visualização** (escolhida) — a HU 08 fala em "filtrar todas
  as visualizações", que é exatamente isto.

## Consequences

Perde-se a economia de LLM que filtrar antes de classificar proporcionava: o
dataset inteiro é sempre classificado. A 30 RPM isso é tempo real de espera no
primeiro upload de um dataset grande — mas é pago uma vez, porque a Análise
completa fica em cache e todo recorte posterior é servido dela.

Em troca, a Regra Geral 04 volta a ter significado único: um dataset tem uma
Análise, e ela cobre o dataset inteiro. Limpar os filtros sempre recupera tudo.

A filtragem continua existindo como função componível em `core/transforms/`, e o
Pipeline pode recebê-la como etapa — mas os predicados chegam **por argumento**,
nunca lidos de estado global. `core/` deixa de importar `ui/`.

O `CONTEXT.md` foi ajustado: **Etapa** não lista mais filtragem, **Análise** passa
a dizer que cobre sempre o dataset inteiro, e **Filtro de Visualização** entrou
como termo próprio.

## Reprocessamento das Análises truncadas

As Análises gravadas antes desta correção podem estar recortadas, e nada no
arquivo distingue uma truncada de uma completa. Em vez de pedir que alguém apague
`.cache` à mão, `services/storage.py` passa a versionar a chave de cache
(`CACHE_SCHEMA_VERSION = "v2"`, prefixo do nome do arquivo): toda Análise antiga
dá **miss** e é reanalisada na primeira vez que o dataset for submetido de novo.
Nenhuma ação humana é necessária, e os arquivos antigos ficam inertes em disco —
podem ser apagados a qualquer momento. Correções futuras que invalidem o formato
seguem o mesmo caminho: incrementar a versão.

### Escopo do versionamento: só a Análise (issue #101)

O `CACHE_SCHEMA_VERSION` invalida **apenas a Análise do dataset**. As
classificações de LLM por repositório, gravadas por
`utils/memoization.py::cached_classify()`, nunca estiveram truncadas — o Filtro
de Visualização recortava o stream depois delas — e descartá-las junto custaria
cota do Groq à toa, contra a Regra Geral 04.

Os dois caches passam a ocupar **subdiretórios distintos** de `CACHE_DIR`
(`analysis/` e `repo-classification/`), cada um com a própria versão de esquema
(`CACHE_SCHEMA_VERSION` e `REPO_CLASSIFICATION_SCHEMA_VERSION`). Escolhemos
subdiretório em vez de sufixo na chave porque separa também fisicamente: dá para
apagar um cache inteiro à mão sem tocar no outro. Um bump futuro atinge só o
espaço afetado.

A escrita permanece atômica (`.tmp` + `os.replace`) nos dois espaços, agora com
o `mkdir` do subdiretório do namespace. A mudança de layout invalida uma vez os
arquivos que estavam na raiz de `CACHE_DIR`; daí em diante, cada espaço evolui
sozinho.
