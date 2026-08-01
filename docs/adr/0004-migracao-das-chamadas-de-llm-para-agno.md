# Migração das chamadas de LLM para Agno

A Dica 05 do enunciado recomenda Agno para as chamadas a LLMs; o código usa o SDK
do Groq direto, e `agno>=2.6.5` está declarado no `pyproject.toml` sem ser
importado por módulo nenhum — uma dependência fantasma. Como
`.claude/rules/code-conventions.md` exige ADR para mudança de stack, decidimos
**migrar para Agno, e migrar cedo** — antes da correção dos prompts
([ADR-0002](./0002-clareza-avaliada-sobre-o-comentario-de-revisao.md)) — para que
os prompts sejam reescritos uma única vez, já sobre a biblioteca definitiva.

## Considered Options

- **Não migrar, e remover `agno` do `pyproject.toml`** — a Dica 05 é *Dica*, não
  Regra: usar o SDK direto não é não-conformidade. Zero risco, e o SDK direto dá
  controle fino sobre o rate limit. Descartada porque o grupo prefere atender à
  Dica, que a banca pode valorizar.
- **Migrar depois das correções de prompt** — mais seguro por ordem, mas obrigaria
  a reescrever os prompts duas vezes.
- **Migrar cedo** (escolhida) — os prompts nascem sobre o Agno.

## Consequences

O throttle de 2,1 s entre requisições e o backoff exponencial de até 6 tentativas
são o que segura o teto de **30 RPM** do plano gratuito do Groq. A migração precisa
preservá-los ou reimplementá-los sobre o Agno. Essa é a parte perigosa: um throttle
quebrado não falha em teste — falha com erro 429 no meio de uma análise longa, em
produção.

Por isso a migração é sequenciada **depois** do conserto da suíte de testes, que
hoje não coleta. Migrar sem suíte que rode significa trocar a camada inteira de LLM
sem nenhuma forma de verificar que a proteção sobreviveu.

## Caminho de erro: recusa de schema degrada para o sentinela

A migração criou um caminho de falha que não existia antes. Com o SDK direto, uma
resposta fora do vocabulário controlado (`"monorepo"`, chave errada, texto solto)
chegava como string a `services/classifiers.py` e degradava para o sentinela
`unknown` via `normalize_label()`. Com o Agno, a validação contra o `Literal` do
`output_schema` acontece antes: o `parse_response_model_str` engole o
`ValidationError`, registra um *warning* e devolve **a string crua** em `content`
— `normalize_label()` nunca é alcançada.

Três decisões seguem daí.

**Orçamentos de tentativa separados.** Antes, o desvio de schema era tratado como
falha de rede: 6 tentativas com backoff exponencial, ~12 s de espera, para o
modelo repetir uma recusa largamente determinística. Agora
`_invoke_with_retry` conta rede e schema em separado — rede mantém as 6
tentativas e o backoff (inclusive o tempo sugerido no 429), schema tem **2
tentativas**. A tentativa extra existe porque o JSON mode é probabilístico e
flutua de verdade; a partir daí só se queima cota. O throttle de 2,1 s continua
precedendo **toda** requisição, nos dois caminhos — é ele que segura os 30 RPM.

**Os dois caminhos da recusa usam o orçamento de schema.** O desvio se manifesta
de duas formas: o Agno devolvendo `content` cru (acima), e o Groq rejeitando a
própria geração com **HTTP 400 `json_validate_failed`**, que sobe como *exceção*
de `agent.run()`. O segundo caminho caía no `except Exception` genérico e
consumia as 6 tentativas de rede com backoff (~62 s) por uma recusa
determinística. `_is_schema_refusal_exception()` o reclassifica inspecionando a
mensagem da exceção. A detecção por texto é frágil e é assim de propósito:
capturar pelo tipo exigiria importar `groq.BadRequestError` — proibido neste
projeto — ou uma exceção interna do Agno. Um falso negativo apenas devolve o
caminho ao orçamento de rede, que é o comportamento anterior. O `except
Exception` segue largo para o resto: estreitá-lo exigiria o mesmo acoplamento.

**Degradar para o sentinela, não falhar alto.** Esgotado o orçamento de schema,
`_invoke_with_retry` devolve `None` e o chamador substitui a classificação por
`UNKNOWN_PROJECT_TYPE` / `UNKNOWN_PR_NATURE` / `UNKNOWN_CLARITY_LEVEL`. A recusa
fica registrada em log de nível `error`, com o repositório de origem e o conteúdo
recusado truncado. `services/classifiers.py` reconhece o sentinela antes de
chamar `normalize_label()`, que não o tem no vocabulário e o rebaixaria para
`"other"`.

A alternativa considerada — e implementada antes desta decisão — era propagar uma
`SchemaRefusalError` que `views/upload.py` transformava em mensagem de erro e
`st.stop()`. Foi revertida porque `save_results()` só é chamado depois de
materializar o gerador: **um único registro recusado descartava a Análise
inteira**, incluindo toda a classificação já paga em cota do Groq. Num dataset
grande isso não é falha ruidosa, é inviabilização — a probabilidade de pelo menos
uma recusa cresce com o número de registros.

**O trade-off é real e foi aceito com os olhos abertos.** Degradar torna um
`unknown` de recusa indistinguível de um `unknown` legítimo (campo ausente do
JSON, label fora do vocabulário). Isso pode enviesar a correlação da HU 07, e o
log é o único rastro que sobra — quem lê o dashboard não o vê. Distinguir as duas
procedências exigiria um campo novo de procedência no `AnalysisResult`, ou seja,
mudança no modelo de domínio; ficou explicitamente fora desta correção.
Persistência incremental, que tornaria o "falhar alto" barato, mudaria o contrato
da Regra Geral 04 e fica para issue própria.

Por ser Dica e não Regra, este ADR é reversível a custo baixo: se o Agno não
permitir o controle de rate limit necessário, voltar ao SDK direto **não** é
não-conformidade — mas exige superseder este ADR, e não apenas reverter o código.
