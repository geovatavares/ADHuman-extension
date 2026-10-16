# Integração da extensão — experimento por páginas

O runner envia ao content script:

- `run_id`;
- perfil visual;
- metadados do site;
- metadados da página (`page_id`, `page_url`, `page_title`);
- parâmetros explícitos do Classifier;
- modelo Ollama.

O runner **não envia o Level**. O Level continua sendo uma variável de resposta do ADHuman.

Para cada página, o content script:

1. analisa os elementos de texto visíveis;
2. calcula quantos estão abaixo do contraste-alvo do perfil;
3. executa o ADHuman Classifier e seleciona L0, L1, L2 ou L3;
4. registra os diagnósticos da classificação;
5. em L0, não solicita participação humana;
6. em L1-L3, constrói o Decision Package e envia `/simulation/decide` ao backend;
7. recebe a decisão validada pelo Checker;
8. aplica a adaptação quando autorizada;
9. devolve ao Playwright o nível classificado, decisão, plano, confiança, tempos e métricas.

A descoberta das páginas ocorre **antes** da avaliação, sem depender da extensão. O conjunto fica fixado em `pages.csv`, garantindo que Padrão, Leve, Moderado e Severo sejam avaliados exatamente nas mesmas páginas.

O `background.js` continua responsável pelas chamadas HTTP ao backend local em `127.0.0.1:8000`.
