# Modelo experimental de perfis de acuidade visual

## Decisão metodológica

Esta primeira versão varia somente a **acuidade visual funcional**. Perfis de
personalidade ou estilo de decisão, como cauteloso, flexível, impulsivo e
sobrecarregado, não são combinados nesta etapa. Isso evita confundir condição
visual com comportamento, atenção ou confiança na automação.

## Perfis

| Perfil | Faixa funcional | Escala | Contraste-alvo | Linha | Letras | Alvo interativo |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Visão de referência | 6/12 ou melhor | 100% | 4,5:1 | 1,5 | 0 em | 24 px |
| Redução leve | pior que 6/12 até 6/18 | 125% | 7:1 | 1,5 | 0,02 em | 28 px |
| Redução moderada | pior que 6/18 até 6/60 | 150% | 10:1 | 1,6 | 0,04 em | 36 px |
| Redução severa | pior que 6/60 até 3/60 | 200% | 15:1 | 1,8 | 0,08 em | 44 px |

As faixas de acuidade são baseadas na classificação de deficiência visual de
distância divulgada pela Organização Mundial da Saúde. Os demais valores são
**parâmetros experimentais propostos**: não foram derivados diretamente da OMS
e não constituem orientação clínica.

## Planos com compensações

| Plano | Benefício | Risco | Incerteza | Custo visual | Resultado principal |
| --- | ---: | ---: | ---: | ---: | --- |
| Correção mínima | 0,66 | 0,08 | 0,08 | 0,08 | Mínima mudança, escala 100%, contraste mínimo |
| Legibilidade reforçada | 0,84 | 0,22 | 0,12 | 0,35 | Escala 125%, contraste 7:1 |
| Pacote de baixa visão | 0,97 | 0,44 | 0,18 | 0,78 | Escala 175%, contraste elevado, controles 44 px |

Os valores são normalizados em `[0,1]`. Eles foram escolhidos para criar
compensações observáveis; devem ser tratados como configuração do experimento e
submetidos posteriormente a análise de sensibilidade e validação com pessoas.

## Compatibilidade perfil–plano

O backend calcula, para cada plano, a cobertura das preferências de contraste,
escala, altura da linha, espaçamento entre letras, tamanho dos controles e alto
contraste. Cada componente é limitado a 1 e a compatibilidade final é a média
dos seis componentes.

Esse valor não decide automaticamente. Ele é uma evidência apresentada ao
participante sintético junto com benefício, risco, incerteza e custo visual.

## Referências normativas e funcionais

- WHO, *WHOeyes information sheet*: categorias de deficiência visual de distância. <https://cdn.who.int/media/docs/default-source/blindness-and-visual-impairment/whoeyes-info-sheet-en.pdf>
- W3C, WCAG 2.2, SC 1.4.3: contraste mínimo de 4,5:1 para texto comum. <https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html>
- W3C, WCAG 2.2, SC 1.4.4: texto ampliável até 200% sem perda. <https://www.w3.org/WAI/WCAG22/Understanding/resize-text.html>
- W3C, WCAG 2.2, SC 1.4.12: parâmetros de espaçamento de texto. <https://www.w3.org/WAI/WCAG22/Understanding/text-spacing.html>
- W3C, WCAG 2.2, SC 2.5.8: tamanho mínimo de alvos de ponteiro. <https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum>

## Limitações

- Acuidade não captura campo visual, sensibilidade ao contraste, fotofobia,
  percepção de cores, uso de tecnologia assistiva ou experiência prévia.
- Uma LLM não possui experiência visual incorporada equivalente à de uma pessoa.
- O estudo deve ser apresentado como simulação controlada e não como substituto
  definitivo de avaliação com usuários.
