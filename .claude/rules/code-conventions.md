# Convenções de Código

> Lido pelo agente ao escrever ou revisar código. Para o modelo de domínio, ver
> `CONTEXT.md`; para as decisões de arquitetura e seus porquês, `docs/adr/`.
>
> As restrições específicas deste projeto devem ser definidas na sessão de *grill
> with docs* (skill `grill-with-docs`, log em `docs/grills_logs/`) e registradas na
> seção [Restrições deste projeto](#restrições-deste-projeto) abaixo.

---

## Idioma

- **Código** (módulos, identificadores, docstrings) em **inglês**.
- **Documentação** (ADRs, `CONTEXT.md`, README, log) em **português**.
- O glossário em `CONTEXT.md` faz a ponte entre o termo de domínio (pt-BR) e o
  identificador no código (inglês).

---

## Convenções por linguagem

As regras específicas de cada linguagem vivem em arquivos separados, para não
assumir uma stack que o projeto não usa:

- **Python** → [`python-conventions.md`](./python-conventions.md)
- Outras linguagens: adicionar `rules/<linguagem>-conventions.md` conforme o
  projeto precisar (ex.: `typescript-conventions.md`).

---

## Clean Code

- Funções com responsabilidade única — se o nome precisar de "e"/"ou", dividir.
- Nomes descritivos: sem abreviações opacas (`nd` → `node`, `sz` → `size`).
- Constantes em `UPPER_SNAKE_CASE`; variáveis e funções em `snake_case`; classes em
  `PascalCase`.
- Comentários explicam *por quê*, não *o quê*.
- Ver também `.claude/rules/karpathy-principles.md` (simplicidade primeiro,
  mudanças cirúrgicas, execução orientada a metas).

---

## Restrições deste projeto

> Preencher na sessão de *grill with docs* deste projeto. Modelo de domínio em
> [`CONTEXT.md`](../../CONTEXT.md); decisões e porquês em [`docs/adr/`](../../docs/adr/).
>
> Modelo de domínio em [`CONTEXT.md`](../../CONTEXT.md); decisões e porquês em
> [`docs/adr/`](../../docs/adr/); estado de conformidade na §15 do
> [`CLAUDE.md`](../../CLAUDE.md).

### Regra zero — o enunciado é a fonte da verdade

LazyPR é trabalho avaliado da Residência em Programação III. O **enunciado da
disciplina** define as Regras Gerais, as Regras Específicas de Programação
Funcional e as Histórias de Usuário, e prevalece sobre qualquer preferência de
estilo — inclusive sobre as regras deste arquivo.

**Código que diverge do enunciado é não-conformidade a corrigir, não dívida a
aceitar.** Ao encontrar uma, nomeie a regra numerada violada.

Distinga os dois níveis: **Regras** são obrigatórias; **Dicas de Implementação**
são opcionais. Usar o SDK do Groq direto em vez de Agno descumpriria a Dica 05 —
não uma regra.

### Pipeline (Regra Geral 05) — inegociável

As etapas de análise devem ser **funções passadas como argumento** para uma função
que centralize o pipeline, e o chamador deve poder **ativar ou desativar** etapas
sem alterar código. As duas metades juntas, na mesma função.

Passar flags booleanas para uma função com as etapas fixas no corpo **não** cumpre
a regra.

### Papel do LLM (Regra Geral 06) — inegociável

O LLM **só** enriquece com classificação semântica: Tipo de Projeto, Natureza da
Contribuição, Clareza da Descrição. É proibido delegar a ele limpeza,
normalização, cálculo de métricas, agrupamento ou agregação — essa lógica é o que
está sendo avaliado.

Corolário: `language` é inferida da extensão do arquivo em `path`, **nunca** por
LLM. Chamadas ao LLM ficam isoladas em `services/`, recebem dados já
pré-processados e devolvem JSON que o pipeline pós-processa.

### Paradigma funcional — inegociável

Vale integralmente o que está na [§3 do `CLAUDE.md`](../../CLAUDE.md): pureza em
`core/`, imutabilidade, lazy evaluation, composição. Pontos que só o enunciado
esclarece:

- **Comprehensions são permitidas** (Regra Específica 01) — um `for` dentro de uma
  list/dict/generator comprehension não viola nada. O proibido é o laço
  acumulador com `append()`.
- **Laços imperativos exigem justificativa em comentário**, não são banidos em
  absoluto. Um gerador que precisa de `yield` dentro do laço é caso legítimo —
  mas escreva o porquê.
- **Materialização exige justificativa.** `group_by` sobre o stream completo é
  inerentemente não-lazy; se for inevitável, documente o trade-off no código
  (exemplo em `services/classifiers.py:177`).
- **Recursão é incentivada** como alternativa a laço.

### Stack — não trocar sem ADR

| Item | Valor | Porquê |
|---|---|---|
| Python | 3.12 | fixado em `.python-version` |
| Dependências | **uv** (`uv.lock`) | nunca pip, poetry ou conda |
| Interface | Streamlit | Regra Geral 08 exige interface gráfica; Dica 04 sugere Streamlit |
| LLM | Agno + backend Groq | Dica 05 (Agno) e Dica 07 — acesso gratuito; 30 RPM no plano free |
| Dataset | `pelmers/github-public-pull-request-comments` | fixado pela Regra Geral 01 |

As chamadas passam por um `Agent` do Agno com `output_schema` Pydantic
([ADR-0004](../../docs/adr/0004-migracao-das-chamadas-de-llm-para-agno.md)). O
schema vive em `services/` — `core/` não importa pydantic nem agno. `groq` segue
declarado no `pyproject.toml` porque o Agno o usa internamente; nenhum módulo
nosso o importa direto.

### Persistência (Regra Geral 04) — inegociável

Toda análise de um dataset é persistida para nunca ser recomputada. Escrita
**atômica** (`.tmp` + `os.replace`), indexada por SHA-256. A chave de cache inclui
os IDs do batch — datasets distintos que compartilham repositórios não podem
colidir.

### Limites de ambiente

- **30 RPM** no plano gratuito do Groq. Throttle de 2,1 s entre chamadas é
  obrigatório; remover quebra a análise com erro 429.
- **`GROQ_API_KEY`** é a única variável sem a qual o sistema não roda.
- Sem CI: nada valida conformidade automaticamente. A revisão é humana.
