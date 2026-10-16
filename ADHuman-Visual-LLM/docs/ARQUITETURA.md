# Arquitetura — ADHuman Visual 3.0

O projeto mantém o ciclo MAPE-K e utiliza a LLM somente como substituta
experimental da entrada humana.

## Componentes

| Componente | Responsabilidade |
| --- | --- |
| Monitor | Inicia o ciclo e observa a aba ativa |
| Analyzer | Detecta problemas de contraste e produz evidências |
| Classifier | Seleciona Level 0, 1, 2 ou 3; o modo forçado existe para experimentos controlados |
| Decision Supporter | Produz recomendação, alternativas, métricas e limites de capacidade |
| GUI | Apresenta o Decision Package e as ações permitidas no nível |
| Ollama Human Proxy | Simula uma decisão conforme o perfil de acuidade visual |
| Checker | Valida ação, plano e limites antes da execução |
| Executor | Aplica somente adaptações reconhecidas ou configurações dentro dos limites |
| Knowledge | Registra contexto, prompt, resposta, perfil e resultado |

## Estados utilizados pela extensão

| Estado | Responsabilidade |
| --- | --- |
| AH0 | Waiting for Adaptation Request |
| AH1 | Classifying Human Involvement |
| AH2 | Autonomous Decision — Level 0 |
| AH3 | Human Interaction — Levels 1, 2 e 3 |
| AH4 | Validating Selected Action |
| AH5 | Recording Decision |
| AH6 | Executing Adaptation |
| AH7 | Verifying Adaptation Outcome |
| SF | Safe Interruption |

## Fluxo

1. O Analyzer produz violações de contraste.
2. O Classifier determina o nível.
3. No Level 0, o sistema seleciona a correção mínima sem consultar a LLM.
4. Nos Levels 1–3, o Decision Supporter monta o pacote e a GUI o apresenta.
5. O Ollama simula a ação humana conforme o perfil selecionado.
6. O backend e o Checker validam a ação conforme o nível.
7. A decisão é registrada antes da execução.
8. O Executor aplica uma configuração determinística.
9. O Analyzer verifica o resultado.

## Decision Package

O pacote contém:

- contexto e violações;
- nível de envolvimento;
- plano recomendado;
- três planos candidatos;
- configurações resultantes de cada plano;
- benefício previsto, risco, incerteza e custo da mudança visual;
- limites para uma configuração personalizada;
- histórico do ciclo.

## Limite arquitetural da LLM

A LLM não atua como Analyzer, Classifier, Decision Supporter, Checker ou
Executor. Ela não escreve CSS e não acessa diretamente a página. Sua resposta
estruturada passa por duas validações antes da execução: o backend verifica a
semântica do nível e o popup confirma novamente o identificador ou configuração.

## Modo automático demonstrativo

As regras abaixo servem somente para percorrer a implementação:

- zero falhas: nenhuma adaptação;
- uma falha: Level 0;
- duas ou três falhas: Level 1;
- quatro a sete falhas: Level 2;
- oito ou mais falhas: Level 3.

Esses limites não são apresentados como resultado científico. No experimento de
perfis, deve-se selecionar explicitamente o nível para manter o cenário
controlado.
