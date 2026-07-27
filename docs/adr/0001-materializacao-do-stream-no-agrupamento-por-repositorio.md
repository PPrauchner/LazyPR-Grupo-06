# Materialização do stream no agrupamento por repositório

O enunciado pede duas coisas que tensionam entre si: a Regra Específica 04 exige
avaliação preguiçosa sem carregar todos os registros em memória, e a Dica 06
recomenda agrupar os registros de um mesmo repositório numa única chamada ao LLM
para classificar o Tipo de Projeto. Agrupar por repositório é inerentemente
não-lazy — não se sabe quais registros pertencem a `golang/go` sem ter visto o
stream inteiro. Decidimos **materializar o stream nesse ponto específico**
(`services/classifiers.py`, via `group_by`), aceitando custo O(n) de memória na
etapa de classificação, e manter lazy todo o resto do pipeline.

## Considered Options

- **`itertools.groupby` sobre o stream** — é lazy, mas exige entrada pré-ordenada
  por repositório, e ordenar via `sorted()` materializa igual. Ganho nenhum.
- **Uma chamada de LLM por registro, sem agrupar** — preserva a laziness de ponta
  a ponta, mas contraria a Dica 06 e multiplica as requisições. Com o teto de 30
  RPM do plano gratuito do Groq, a análise deixaria de terminar em tempo viável.
- **Materializar no ponto de agrupamento** (escolhida) — concentra a perda de
  laziness numa etapa identificável e documentada, em vez de espalhá-la.

## Consequences

A ingestão (`stream_csv`), a limpeza, a normalização e a filtragem continuam
preguiçosas; o teto de memória é atingido apenas quando a etapa de classificação
está habilitada.

A chave de cache persistente depende dessa decisão: ela é o SHA-256 de
`repo:ids_ordenados_do_batch`, o que só faz sentido porque o batch é conhecido por
inteiro antes da chamada. Voltar atrás no agrupamento obriga a redesenhar o
esquema de cache — e invalida todo o cache já gravado em `.cache/`.

Quem ler `services/classifiers.py` esperando laziness vai encontrar `group_by`
sobre o stream completo e pode tomar isso por descuido. O trade-off está
justificado em comentário no código, como a Regra Específica 01 exige.
