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
