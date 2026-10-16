ADHuman — AIM Score / correção do sidebar WAVE
=================================================

PROBLEMA IDENTIFICADO
---------------------
O diagnóstico mostrou:

FRAME 1
URL: https://dados.gov.br/sidebar.html

Isso significa que inject.js foi executado, porém o iframe do WAVE usou
"sidebar.html" como URL relativa à página analisada.

CORREÇÃO
--------
Depois de executar inject.js, o novo run:

1. localiza #wave_sidebar_container;
2. obtém chrome.runtime.getURL("sidebar.html");
3. substitui o src relativo pelo URL absoluto da extensão:
   chrome-extension://jbbplnpkjmmeebjpijfedlgcdilocofh/sidebar.html
4. aguarda o sidebar carregar;
5. procura e extrai o AIM Score.

SMOKE TEST
----------
python run_aim_experiment.py --fresh --smoke-test

Antes de executar as 120 runs, confirme que aparecem valores como:
preAIM=...
postAIM=...

Se ainda houver timeout, envie o TXT mais recente de:
results_aim\debug\

O novo erro também mostrará os URLs de todos os frames.
