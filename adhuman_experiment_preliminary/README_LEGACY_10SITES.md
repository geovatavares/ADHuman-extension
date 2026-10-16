# ADHuman — 10 Sites × 10 Páginas × 4 Perfis

## Objetivo
Avaliar em quantas páginas de cada website o ADHuman identifica necessidade de participação humana, considerando quatro perfis de acuidade visual.

## Desenho
- 10 sites (P01 a P10 em `sites.csv`);
- 10 páginas por site;
- 4 perfis: Padrão, Leve, Moderado e Severo;
- 1 execução por combinação página × perfil.

**Total planejado: 10 × 10 × 4 = 400 execuções.**

A homepage conta como uma das 10 páginas. As outras páginas são descobertas automaticamente por um crawler BFS controlado, limitado ao próprio site e a profundidade 2.

## Por que existe `pages.csv`?
Antes do experimento, as páginas são descobertas uma única vez e salvas em `pages.csv`. O experimento usa esse conjunto fixo nas 400 execuções, evitando que cada perfil seja avaliado em páginas diferentes.

Para redescobrir as páginas deliberadamente:

```powershell
.\.venv\Scripts\python.exe discover_pages.py --force
```

ou:

```powershell
.\.venv\Scripts\python.exe run_experiment.py --refresh-pages --discover-only
```

## Descobrir páginas sem rodar a avaliação

```powershell
.\.venv\Scripts\python.exe run_experiment.py --discover-only
```

O crawler gera:
- `pages.csv`: as 100 páginas fixadas para o experimento;
- `results/crawl_report.csv`: quantidade encontrada e erros por site.

Por padrão, o experimento exige exatamente 10 páginas elegíveis por site. Se algum site não atingir a cota, ele para antes da avaliação para não produzir um desenho desbalanceado.

## Smoke test
O smoke test usa somente a homepage dos dois primeiros sites e os quatro perfis:

```powershell
.\.venv\Scripts\python.exe run_experiment.py --smoke-test --mode extension --fresh
```

Total esperado: **8 execuções**.

## Experimento completo

```powershell
.\.venv\Scripts\python.exe run_experiment.py --mode extension --fresh
```

Total esperado: **400 execuções**.

## Métrica principal
Para cada combinação `[site, perfil]`:

```text
human_assistance_count = quantidade de páginas com Level 1, 2 ou 3
```

Como são 10 páginas por site, a métrica varia de **0 a 10**.

- 0 = nenhuma página exigiu participação humana;
- 10 = todas as páginas exigiram participação humana.

O Level 0 permanece registrado como ausência de participação humana.

## Gráficos

```powershell
.\.venv\Scripts\python.exe analyze_results.py
```

Para cada site será gerado um gráfico:
- eixo X = Padrão, Leve, Moderado, Severo;
- eixo Y = número de páginas (0–10) em que houve participação humana.

Arquivos principais em `results/analysis/`:
- `page_profile_results.csv`
- `assistance_summary.csv`
- `level_frequency_by_site_profile.csv`
- `participation_rate_matrix.csv`
- `decision_distribution.csv`
- `P01_human_participation_by_profile.png` ... `P10_human_participation_by_profile.png`
- `experiment_report.md`
