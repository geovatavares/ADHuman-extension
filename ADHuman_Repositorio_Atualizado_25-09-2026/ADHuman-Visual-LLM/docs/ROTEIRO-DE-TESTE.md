# Roteiro de teste — perfis visuais com Ollama

## Preparação

1. Instale o Ollama e execute `ollama pull llama3.1:8b`.
2. Execute `1-Instalar-Backend.bat` uma vez.
3. Execute `2-Iniciar-ADHuman-LLM.bat`.
4. Instale a pasta `plugin` pelo modo de desenvolvedor do Chrome.
5. Habilite acesso a URLs de arquivo.
6. Abra `Teste-Integracao-1-Erro.html`.

## Verificação da conexão

1. Abra o popup.
2. Selecione **Humano simulado por Ollama**.
3. Escolha um modelo instalado.
4. Clique em **Testar backend e Ollama**.
5. Confirme **Ollama pronto**.

## Level 0

1. Selecione **Forçar Level 0**.
2. Execute o ciclo.
3. Confirme AH0 → AH1 → AH2 → AH6 → AH7.
4. Confirme que a LLM não foi consultada.

## Level 1 — validação

1. Restaure a página.
2. Selecione **Forçar Level 1**.
3. Escolha um perfil visual.
4. Execute o ciclo.
5. Confirme que o Ollama só pode aprovar ou rejeitar a recomendação
   `plan_enhanced` — além do `defer` de segurança por dados insuficientes.

## Level 2 — seleção

1. Restaure a página.
2. Selecione **Forçar Level 2**.
3. Repita o ciclo para os quatro perfis.
4. Compare a seleção entre `plan_minimum`, `plan_enhanced` e
   `plan_low_vision`.

## Level 3 — controle humano

1. Restaure a página.
2. Selecione **Forçar Level 3**.
3. Execute com cada perfil.
4. Confirme que o Ollama pode selecionar um plano ou retornar
   `customized_settings` dentro dos limites.
5. Confirme que configurações inválidas são bloqueadas antes do Executor.

## Fallback

1. Feche o backend.
2. Execute um nível humano no modo Ollama.
3. Confirme SF e a disponibilidade dos controles manuais.

## Evidências

Registre perfil, faixa, cenário, nível, modelo, versão do prompt, falhas antes e
depois, compatibilidade dos planos, ação, plano/configuração, confiança,
justificativa, tempo de inferência, estado final e fallback.

O registro completo fica em `backend/logs/simulation-runs.jsonl`.
