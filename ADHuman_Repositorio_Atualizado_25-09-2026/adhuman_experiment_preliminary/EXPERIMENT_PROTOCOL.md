# Protocolo — 10 Sites × 10 Páginas × 4 Perfis

## Objetivo
Avaliar a efetividade do ADHuman em identificar e gerenciar a necessidade de participação humana em diferentes páginas de sistemas web auto-adaptativos.

## Fatores principais
- Perfil ∈ {Padrão, Leve, Moderado, Severo}
- Site ∈ {P01, ..., P10}

`Página` é uma unidade aninhada no site (`Página ⊂ Site`), não um fator cruzado independente.

## Unidade de execução
Uma execução corresponde a:

`[site, página, perfil]`

Há uma única execução por combinação.

## Quantidade
- 10 sites
- 10 páginas por site (homepage + 9 internas, quando disponíveis)
- 4 perfis
- 1 repetição

Total = **400 execuções**.

## Descoberta de páginas
As páginas são descobertas antes da avaliação por um crawler BFS controlado:
- mesmo site/domínio e subdomínios pertencentes ao host inicial;
- profundidade máxima 2;
- URLs normalizadas;
- fragmentos e parâmetros de consulta removidos por padrão;
- binários (PDF, ZIP, imagens, Office etc.) excluídos;
- páginas de login/admin/checkout excluídas;
- conjunto final salvo em `pages.csv` e reutilizado por todos os perfis.

Isso evita que diferentes perfis sejam avaliados em conjuntos diferentes de páginas.

## Variável de resposta
`classified_level`, produzido pelo Classifier:
- L0: sem participação humana;
- L1, L2, L3: participação humana.

## Métrica principal
Para cada `[site, perfil]`:

`human_assistance_count = count(páginas classificadas em L1, L2 ou L3)`

Faixa: 0–10.

Também é calculada:

`human_assistance_pct = human_assistance_count / pages_evaluated × 100`

## Classifier
Mantém-se a lógica atual do piloto:
- 0–1 incompatibilidade → L0
- 2–3 → L1
- 4–7 → L2
- 8+ → L3

As incompatibilidades são calculadas em relação ao contraste-alvo de cada perfil.

## Randomização
As 400 combinações são construídas de forma balanceada e a ordem de execução é embaralhada com seed fixa. O conjunto de páginas, os sites e os perfis não são sorteados durante a avaliação.

## Saída gráfica principal
Um gráfico por site:
- eixo X: níveis do fator Perfil;
- eixo Y: número de páginas com participação humana (0–10).
