# ADHuman — Relatório do Experimento

## Desenho experimental

- Fatores: **perfil visual** e **site**.
- Perfis: **Padrão, Leve, Moderado e Severo**.
- Execuções por combinação [perfil, site]: **1**.
- O nível de participação é uma **variável de resposta do Classifier**.
- Métrica principal: **quantidade de vezes em que houve participação humana**.
- Uma execução conta como participação humana quando o nível classificado é **L1, L2 ou L3**.
- Level 0 representa ausência de participação humana.

## Execução observada

- Linhas válidas consideradas na análise: **76**.
- Participações humanas observadas no total: **65**.
- Taxa global de participação humana: **85.53%**.

## Resumo global por perfil

| Perfil | Sites | Execuções | L0 | L1 | L2 | L3 | Participação humana | % |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Padrão | 18 | 18 | 6 | 1 | 2 | 9 | 12 | 66.67% |
| Leve | 23 | 23 | 4 | 0 | 1 | 18 | 19 | 82.61% |
| Moderado | 18 | 18 | 0 | 2 | 1 | 15 | 18 | 100.00% |
| Severo | 17 | 17 | 1 | 0 | 0 | 16 | 16 | 94.12% |

## Interpretação da métrica

`human_assistance_count = level_1_count + level_2_count + level_3_count`

O gráfico principal agrega a ocorrência de participação humana em **todos os sites**. Assim, existe apenas um gráfico: no eixo X estão os níveis do fator Perfil (Padrão, Leve, Moderado e Severo), e no eixo Y está a quantidade total de vezes em que houve participação humana somando todos os sites.
