# Backend ADHuman Visual

O backend recebe o `Decision Package` da extensão e solicita ao Ollama uma única
decisão coerente com um perfil sintético de acuidade visual funcional. A LLM
não detecta violações, não seleciona o nível e não executa adaptações.

## Instalação no Windows

1. Instale o Ollama: <https://ollama.com/download/windows>.
2. Execute `ollama pull llama3.1:8b` ou `ollama pull qwen3:8b`.
3. Na pasta principal, execute `1-Instalar-Backend.bat` uma vez.
4. Execute `2-Iniciar-ADHuman-LLM.bat` ao utilizar a extensão.

O instalador aceita o Python padrão 3.10 ou mais recente selecionado pelo
`py.exe` ou pelo comando `python`.

## Endpoints

- `GET /health`: saúde do backend.
- `GET /health/ollama?model=llama3.1:8b`: conexão com o Ollama e disponibilidade do modelo.
- `GET /profiles`: perfis visuais experimentais.
- `POST /simulation/decide`: decisão do participante sintético.
- `GET /docs`: documentação interativa do FastAPI.

## Validação por nível

- Level 1: `approve`, `reject` ou `defer`; uma aprovação só pode apontar para o plano recomendado.
- Level 2: `select`, `reject` ou `defer`; a seleção deve pertencer aos planos candidatos.
- Level 3: `select`, `customize`, `reject` ou `defer`; uma configuração deve respeitar `capability_bounds`.

Identificadores são normalizados antes da validação. Uma resposta fora das
regras é convertida em `defer` e não alcança o Executor.

## Testes

Na pasta `backend`:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

As execuções ficam em `logs/simulation-runs.jsonl`.
