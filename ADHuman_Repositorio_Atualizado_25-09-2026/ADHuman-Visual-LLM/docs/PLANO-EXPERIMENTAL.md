# Plano experimental preliminar — 17/09/2026

## Objetivo

Avaliar a efetividade do ADHuman no auxílio da participação humana em sistemas autoadaptativos.

## Fatores

- **Perfil:** Padrão, Leve, Moderado, Severo.
- **Site:** Site 1 e Site 2.

O Level não é fator. Ele é uma saída do ADHuman Classifier.

## Condições

O desenho contém 8 células:

- [Padrão, Site1]
- [Padrão, Site2]
- [Leve, Site1]
- [Leve, Site2]
- [Moderado, Site1]
- [Moderado, Site2]
- [Severo, Site1]
- [Severo, Site2]

Cada célula é repetida 30 vezes: **240 execuções**.

## Métrica principal

Quantidade de vezes em que o Classifier seleciona:

- Level 1;
- Level 2;
- Level 3.

Level 0 é registrado como ausência de participação humana.

`human_assistance = 1` quando `classified_level ∈ {1,2,3}`.

## Gráficos

Um gráfico por site:

- eixo X: Levels 1, 2 e 3;
- eixo Y: quantidade de execuções;
- quatro séries de barras: Padrão, Leve, Moderado e Severo.

## Classifier do piloto

O Classifier usa a quantidade de elementos de texto visíveis que não atingem o contraste-alvo do perfil. São preservados os limiares já existentes no modo automático do ADHuman:

- até 1 incompatibilidade → L0;
- 2–3 → L1;
- 4–7 → L2;
- 8+ → L3.

Os alvos sintéticos de contraste são 4.5, 7, 10 e 15 para os quatro perfis. Esses valores e limiares são parâmetros experimentais explícitos e não prescrições clínicas.

## Execução humana simulada

Após o Classifier selecionar L1-L3, o Ollama simula o participante:

- L1: aprova ou rejeita a recomendação;
- L2: seleciona um plano candidato, rejeita ou adia;
- L3: seleciona um plano ou customiza uma adaptação dentro dos limites.

Essas decisões são métricas secundárias neste experimento; a resposta principal é o Level selecionado pelo ADHuman.
