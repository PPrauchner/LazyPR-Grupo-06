# Gemini Instructions — LazyPR (Lite)

---

## 🧠 Contexto do Projeto

Ferramenta de análise semântica de Pull Requests do GitHub usando programação funcional e LLMs.

**Stack:**

* Python 3.12+
* Streamlit
* LLM (Agno + Groq/OpenRouter)

---

## 🏗️ Arquitetura

* `core/` → funções puras (sem I/O)
* `services/` → I/O, LLM, rede
* `ui/` → interface Streamlit

Nunca misturar responsabilidades entre camadas.

---

## ⚙️ Regras Essenciais

### Programação Funcional

* Proibido `for` e `while` em transformações no `core/`
* Usar `map`, `filter`, `reduce`, generators
* Preferir composição de funções (`compose`, `pipe`)

### Imutabilidade

* Nunca modificar dados in-place
* Usar `tuple`, `NamedTuple`, `dataclass(frozen=True)`
* Sempre retornar novas estruturas

### Lazy Evaluation

* Usar `yield` e generators
* Nunca usar `list()` em datasets completos

### Pureza

* `core/` → funções puras (sem estado, sem efeitos colaterais)
* I/O apenas em `services/` e `ui/`

---

## 📌 Regras por Camada

### core/

* Apenas funções puras
* Sem imports de I/O ou libs externas

### services/

* I/O, LLM, cache, rede
* Pode usar `try/except`

### ui/

* Apenas Streamlit e renderização
* Sem lógica de negócio

---

## 🚫 Proibições

* Mutação de dados (`append`, `update`, etc.)
* Loops imperativos no `core/`
* Misturar lógica com I/O
* Materializar streams (`list()`)

---

## ✅ Exemplos

### Correto

```python
tuple(map(lambda x: x * 2, data))
```

### Errado

```python
result = []
for x in data:
    result.append(x * 2)
```

---

## 📐 Formato de Resposta

Sempre responder com:

1. Explicação breve (até 5 linhas)
2. Código completo
3. Justificativa baseada nas regras

---

## 🎯 Missão

Gerar código seguindo estritamente:

* programação funcional
* imutabilidade
* separação de camadas
* lazy evaluation

Se a solicitação violar essas regras:
→ corrigir e explicar

---

## ⚠️ Regra Final

Este documento é a fonte de verdade.

Nunca gerar código que viole essas regras.
