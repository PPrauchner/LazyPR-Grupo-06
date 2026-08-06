# Clareza avaliada sobre o Comentário de Revisão

A HU 04 pede avaliar "a clareza da descrição de cada PR", mas o dataset fixado
pela Regra Geral 01 não traz descrições de PR: cada registro é um Comentário de
Revisão. Os prompts rotulavam o campo enviado como `PR Description` e cobravam do
modelo "context, problem statement, solution explanation, examples" — uma rubrica
de descrição de PR aplicada a uma observação sobre uma linha. Decidimos que **o
prompt descreve o dado real** — um comentário de revisão, julgado ao lado do
`diff_hunk` a que se refere — e que **a interface continua dizendo "PR"**,
conforme a ponte já registrada no `CONTEXT.md`.

## Considered Options

- **Manter a rubrica de descrição de PR** — custo zero e cache preservado, mas um
  comentário de revisão competente é curto e certeiro por natureza, e nunca
  apresenta "problem statement" nem "examples". A rubrica antiga o classifica como
  `insufficient` por exibir exatamente a virtude que se espera dele. O viés é
  sistemático, não ruído: empurra `clarity_level` para baixo em todo o dataset e
  contamina a correlação da HU 07.
- **Renomear a métrica para "Clareza do Comentário" na interface** — honesto de
  ponta a ponta, mas afasta a tela do vocabulário da HU 04 que a banca lê, e
  contradiz a ponte "PR" que o `CONTEXT.md` fixa para rótulos e relatórios.
- **Prompt descreve o comentário, interface diz "PR"** (escolhida) — alinha a
  classificação ao dado real sem mexer no vocabulário avaliado.

## Consequences

O `diff_hunk` passa a integrar o prompt de clareza. Sem ele o modelo julga um
texto arrancado do contexto — "isso aqui devia ser const" só é avaliável ao lado
da linha comentada. O hunk é truncado em 500 caracteres
(`_MAX_DIFF_HUNK_CHARS`) para segurar o custo de token a 30 RPM. A rubrica entra
no prompt unificado de natureza + clareza, então uma chamada só continua servindo
às duas classificações.

**As classificações já persistidas foram produzidas pela rubrica antiga.** Para
que corrigir o prompt não conviva silenciosamente com resultados velhos, o nome
do arquivo de cache passa a carregar uma **versão de prompt** (`PROMPT_VERSION`,
em `services/prompt_version.py`) ao lado da versão de esquema já existente:

```
.cache/analysis/v2-p1-<hash>.json
.cache/repo-classification/v1-p1-<hash>.json
```

São **duas dimensões independentes** — versão de esquema (formato de
armazenamento) × versão de prompt (rubrica) — e a de prompt compõe a chave dos
**dois** espaços de nomes, porque o `clarity_level` que ela produz mora nos dois.
Bumpar uma não mexe no que a outra invalida. Isso invalida sozinho o cache agora
e em toda edição futura de prompt, sem depender de alguém lembrar de apagar
`.cache/`. O cache antigo permanece no disco, inerte.

Dois prompts mortos foram removidos junto: `classify_pr_nature_single` e
`classify_clarity_single`, alcançáveis apenas por wrappers sem nenhum chamador —
e que nem sequer importavam as funções que invocavam. Manter uma segunda rubrica
de clareza que ninguém executa é convidar a divergência.

Os números da HU 04 e da HU 07 mudam de significado entre o antes e o depois desta
decisão. Comparações com resultados gerados antes dela não são válidas.
