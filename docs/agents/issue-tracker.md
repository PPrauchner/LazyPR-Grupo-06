# Issue tracker

Issues do LazyPR vivem no **GitHub Issues** de `PPrauchner/LazyPR-Grupo-06`,
espelhadas no board **GitHub Projects nº 2 ("LazyPR")**.

O enunciado da disciplina exige esse arranjo: issues como tarefas do projeto,
board Kanban populado e responsáveis atribuídos. Não migrar para outro tracker.

## Comandos

```bash
gh issue create --title "..." --body-file <arquivo> --label <label>
gh issue list --state open --limit 30
gh issue list --label ready-for-agent --state open      # fila do /afk-queue
gh issue view <numero>
gh issue edit <numero> --add-label <label> --remove-label <label>
gh issue close <numero>
```

Corpos longos vão por `--body-file`, nunca por `--body` com string multilinha —
a sintaxe de here-string do PowerShell e a de heredoc do Bash são incompatíveis
entre si, e o erro grava o texto errado silenciosamente.

## Board

O movimento de coluna é feito por `.claude/scripts/board-move.sh`, que resolve os
IDs do Projects v2 sozinho e os cacheia em `.claude/board.env`:

```bash
bash .claude/scripts/board-move.sh <numero-da-issue> <in-progress|in-review>
```

O script **nunca falha**: qualquer problema vira aviso em stderr e `exit 0`, para
que uma fila do `/afk-queue` não aborte por causa do board. Desativar com
`BOARD_SYNC=off` no bloco `env` de `.claude/settings.json`.

### Colunas

O campo `Status` do board tem estas opções:

`Backlog` · `Ready` · `In progress` · `In review` · `Done`

> ⚠️ O enunciado descreve o fluxo como *Backlog → Sprint Backlog → Em Progresso →
> Feito*. As colunas reais são as do template padrão do GitHub, em inglês, e
> `Ready` ocupa o lugar de `Sprint Backlog`. Divergência conhecida — ver a
> "Regra zero" em `.claude/rules/code-conventions.md`.

## Labels de domínio

Além do vocabulário de triagem (`triage-labels.md`), o repo usa labels por área:

| Label | Área |
|---|---|
| `data-ingestion` | entrada de dados, validadores, geradores lazy |
| `logic-core` | pipeline funcional, ordem superior, estado imutável |
| `ai-classification` | classificação semântica por LLM |
| `ai-metrics` | métricas qualitativas geradas por IA |
| `data-science` | análises estatísticas e cruzamento de dimensões |
| `frontend` | Streamlit, componentes, layout, dashboards |
| `data-output` | exportação e persistência em CSV/JSON |

Ao criar uma issue, aplique **um** label de área junto do label de triagem.
