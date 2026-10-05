# CP5 — FIAP Bank: anonimização de manifestações (LGPD)

Pipeline que lê `manifestacoes_clientes_cp5.csv`, extrai campos estruturados com Gemini (fallback Groq) usando schema Pydantic, grava tudo em SQLite e gera `texto_anonimizado` e `resumo_anonimizado` com `anonimizar_texto()` (spaCy + regex), sem sobrescrever os originais.

## Resultado da última execução
- Fallback Gemini → Groq: COMPROVADO
- Estados no banco: [{"status": "concluido", "provedor": "gemini", "quantidade": 37}, {"status": "concluido", "provedor": "groq", "quantidade": 3}]
- Recall de PII: 100.00%
- Preservação de não-PII: 100.00%
- Casos de erro documentados: 3

## Como rodar
Python 3.11 ou 3.12.

```bash
python -m pip install -r requirements.txt
python -m spacy download pt_core_news_sm
```

Abra `CP5_Anonimizacao_LGPD.ipynb` na mesma pasta dos arquivos. No Colab, cadastre `GEMINI_API_KEY` e `GROQ_API_KEY` em Secrets; localmente, use variáveis de ambiente. Os modelos podem ser trocados com `GEMINI_MODEL` e `GROQ_MODEL`. O modelo padrão do Groq é `openai/gpt-oss-120b`.

Os IDs 5, 11 e 22 forçam falha no Gemini para exercitar o fallback. `parsed=None` ou resposta fora do schema vão para revisão humana. A segunda execução não faz chamadas novas.

## Auditoria
```bash
python rotular_dataset.py
python auditoria.py
python -m pytest -q
```
Gera `auditoria_resultado.json`, `auditoria_contagens.json`, `auditoria_detalhes.json` e `RELATORIO_AUDITORIA.md`.

## Uso de IA
Parte do código e a primeira versão dos rótulos de PII foram feitas com apoio de IA; os rótulos e os resultados foram revisados manualmente.

## Publicar
```bash
git clone cp5_historico.bundle cp5-repositorio
cd cp5-repositorio
git remote add origin <URL_DO_REPOSITORIO>
git push -u origin main
```
