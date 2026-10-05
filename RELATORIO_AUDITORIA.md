# Relatório de auditoria

Rotulamos 28 ocorrências de PII nos 40 textos do CSV (rótulos em `rotulos_manuais.json`; a primeira versão foi feita com apoio de IA e depois revisada manualmente).

## Método

Recall = entidades de PII totalmente cobertas pela máscara / total rotulado; remoção parcial conta como falso negativo. Precisão = caracteres não-PII preservados / total de caracteres não-PII (definição do enunciado, não TP/(TP+FP)). Os offsets são medidos no texto original. Final de cartão ficou fora porque não está na lista de PII da atividade.

## Resultados

- Recall: 28/28 = 100.00%.
- Preservação de não-PII: 2868/2868 = 100.00%.
- Conjunto novo (20 textos fora do CSV): recall 100.00% em 20 PIIs; 3 falsos positivos.
- spaCy 3.8.16, modelo core_news_sm 3.8.0.

## Erros encontrados

- ID holdout-2 — falso_positivo: [texto fora do CSV] 'Olá' removido como NOME em: 'Olá, sou Roberto Almeida e quero cancelar o cartão.'
- ID holdout-18 — falso_positivo: [texto fora do CSV] 'Premium' removido como NOME em: 'Cliente Premium reclama da taxa de anuidade.'
- ID holdout-19 — falso_positivo: [texto fora do CSV] 'Ligar' removido como NOME em: 'Ligar para Joana Dark no número cadastrado.'

## Limites

O NER pode confundir verbos ou palavras capitalizadas com pessoas e deixar passar nomes raros ou sem contexto. Os gatilhos por contexto ("cliente", "gerente", "meu nome é") ajudam, mas também mascaram expressões como "Cliente Premium". Um RG sem rótulo e sem pontuação é indistinguível de outros números. As métricas valem para estes textos e não garantem o desempenho no conjunto oculto.
