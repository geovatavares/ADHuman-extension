# Alterações — Versão 10 Sites × 10 Páginas × 4 Perfis

1. A avaliação deixou de usar somente a homepage.
2. Foram selecionados 10 sites (P01–P10).
3. Um crawler controlado descobre e fixa 10 páginas por site em `pages.csv`.
4. O plano experimental é agora página × perfil, com uma execução por combinação.
5. Total esperado: 400 execuções.
6. O CSV passou a registrar `page_id`, `page_order`, `page_depth`, `page_title`, `page_url` e `site_url`.
7. A análise agrega as 10 páginas por `[site, perfil]`.
8. O gráfico principal usa perfil no eixo X e quantidade de páginas com participação humana no eixo Y (0–10).
9. O Level continua sendo resultado do Classifier, não um fator presetado.
