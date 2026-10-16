# ADHuman — 30 sites × homepage × 4 perfis

## Desenho
- 30 sites (P01–P30)
- 1 pagina por site: homepage
- 4 perfis: Padrao, Leve, Moderado e Severo
- 1 execucao por combinacao site-perfil
- Total: 30 × 1 × 4 = 120 execucoes
- O Level (L0/L1/L2/L3) continua sendo produzido pelo Classifier.

## Smoke test
```powershell
.\.venv\Scripts\python.exe run_experiment.py --smoke-test --mode extension --fresh
```
Esperado: 8 execucoes (2 sites × 4 perfis).

## Experimento completo
```powershell
.\.venv\Scripts\python.exe run_experiment.py --mode extension --fresh
```
Esperado: 120 execucoes.

## Analise
```powershell
.\.venv\Scripts\python.exe analyze_results.py
```
O grafico de cada site usa X = perfil e Y = participacao humana na homepage (0 ou 1).
