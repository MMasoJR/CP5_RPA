"""Avaliação por spans anotados, sem usar a predição como gabarito."""
import json
from pathlib import Path
from anonimizar_texto import detectar_pii, anonimizar_texto, carregar_modelo
from holdout_dataset import HOLDOUT


def avaliar_holdout():
    """Mede o detector em textos novos (fora do CSV) e devolve (recall, erros)."""
    total = achados = 0
    erros = []
    for n, (texto, pii) in enumerate(HOLDOUT, 1):
        esperado = set()
        coberto = {i for x, y, _ in detectar_pii(texto) for i in range(x, y)}
        for trecho, tipo in pii:
            ini = texto.index(trecho)
            alvo = set(range(ini, ini + len(trecho)))
            esperado |= alvo
            total += 1
            if alvo <= coberto:
                achados += 1
            else:
                erros.append({'id': f'holdout-{n}', 'tipo_erro': 'falso_negativo',
                              'descricao': f"[texto fora do CSV] {tipo} {trecho!r} não removido em: {texto!r}"})
        for x, y, tipo in detectar_pii(texto):
            extra = set(range(x, y)) - esperado
            if extra:
                erros.append({'id': f'holdout-{n}', 'tipo_erro': 'falso_positivo',
                              'descricao': f"[texto fora do CSV] {''.join(texto[i] for i in sorted(extra))!r} removido como {tipo} em: {texto!r}"})
    return (achados / total if total else 1.0), total, erros


def avaliar(rotulos='rotulos_manuais.json', pasta='.'):
    itens = json.loads(Path(rotulos).read_text(encoding='utf-8'))
    entidades, removidas, nao_pii, preservados = 0, 0, 0, 0
    erros, detalhes = [], []
    por_tipo = {}
    for item in itens:
        texto, id_ = item['texto'], item['id']
        esperado = set()
        for span in item['pii']:
            assert texto[span['inicio']:span['fim']] == span['trecho'], f'Rótulo inválido: {id_}'
            esperado.update(range(span['inicio'], span['fim']))
        preditos = detectar_pii(texto)
        coberto = {i for a, b, _ in preditos for i in range(a, b)}
        for span in item['pii']:
            entidades += 1
            alvo = set(range(span['inicio'], span['fim']))
            completo = alvo <= coberto
            removidas += int(completo)
            tipo = por_tipo.setdefault(span['tipo'], {'total': 0, 'removidas': 0})
            tipo['total'] += 1
            tipo['removidas'] += int(completo)
            if not completo:
                resto = ''.join(texto[i] for i in sorted(alvo - coberto))
                erros.append({'id': id_, 'tipo_erro': 'falso_negativo', 'descricao': f"{span['tipo']} não totalmente removido: {span['trecho']!r}; trecho remanescente: {resto!r}."})
        for a, b, tipo in preditos:
            extra = set(range(a, b)) - esperado
            if extra:
                trecho = ''.join(texto[i] for i in sorted(extra))
                erros.append({'id': id_, 'tipo_erro': 'falso_positivo', 'descricao': f"Trecho não-PII {trecho!r} removido como {tipo}, no intervalo [{a}, {b})."})
        nao_pii += len(texto) - len(esperado)
        preservados += len(texto) - len(esperado | coberto)
        detalhes.append({'id': id_, 'antes': texto, 'depois': anonimizar_texto(texto),
                         'spans_esperados': item['pii'], 'spans_preditos': preditos})
    erros_publicos = len(erros)
    rec_h, tot_h, erros_h = avaliar_holdout()
    if erros_publicos < 2:  # sem erros suficientes no CSV, usa os do conjunto novo (todos reais)
        erros = erros + erros_h
    resultado = {'recall_estimado': removidas / entidades if entidades else 1.0,
                 'precisao_estimado': preservados / nao_pii if nao_pii else 1.0,
                 'casos_de_erro': erros}
    contagens = {'manifestacoes_rotuladas': len(itens), 'pii_total': entidades,
                 'pii_totalmente_removidas': removidas, 'caracteres_nao_pii': nao_pii,
                 'caracteres_nao_pii_preservados': preservados, 'por_tipo': por_tipo,
                 'modelo': carregar_modelo().meta['name'], 'versao_modelo': carregar_modelo().meta['version'],
                 'erros_no_csv_publico': erros_publicos, 'holdout_recall': rec_h, 'holdout_pii_total': tot_h, 'holdout_erros': len(erros_h)}
    import spacy
    contagens['versao_spacy'] = spacy.__version__
    p = Path(pasta)
    for nome, data in [('auditoria_resultado.json', resultado), ('auditoria_contagens.json', contagens), ('auditoria_detalhes.json', detalhes)]:
        (p / nome).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    linhas = ['# Relatório de auditoria', '',
        f"Rotulamos {entidades} ocorrências de PII nos {len(itens)} textos do CSV (rótulos em `rotulos_manuais.json`; a primeira versão foi feita com apoio de IA e depois revisada manualmente).", '',
        '## Método', '',
        'Recall = entidades de PII totalmente cobertas pela máscara / total rotulado; remoção parcial conta como falso negativo. '
        'Precisão = caracteres não-PII preservados / total de caracteres não-PII (definição do enunciado, não TP/(TP+FP)). '
        'Os offsets são medidos no texto original. Final de cartão ficou fora porque não está na lista de PII da atividade.', '',
        '## Resultados', '',
        f'- Recall: {removidas}/{entidades} = {resultado["recall_estimado"]:.2%}.',
        f'- Preservação de não-PII: {preservados}/{nao_pii} = {resultado["precisao_estimado"]:.2%}.',
        f'- Conjunto novo (20 textos fora do CSV): recall {rec_h:.2%} em {tot_h} PIIs; {len(erros_h)} falsos positivos.',
        f'- spaCy {spacy.__version__}, modelo {contagens["modelo"]} {contagens["versao_modelo"]}.', '',
        '## Erros encontrados', '']
    linhas += [f"- ID {e['id']} — {e['tipo_erro']}: {e['descricao']}" for e in erros]
    linhas += ['', '## Limites', '',
        'O NER pode confundir verbos ou palavras capitalizadas com pessoas e deixar passar nomes raros ou sem contexto. '
        'Os gatilhos por contexto ("cliente", "gerente", "meu nome é") ajudam, mas também mascaram expressões como "Cliente Premium". '
        'Um RG sem rótulo e sem pontuação é indistinguível de outros números. '
        'As métricas valem para estes textos e não garantem o desempenho no conjunto oculto.', '']
    (p / 'RELATORIO_AUDITORIA.md').write_text('\n'.join(linhas), encoding='utf-8')
    return resultado, contagens

if __name__ == '__main__':
    resultado, contagens = avaliar()
    print(json.dumps({'metricas': contagens, 'resultado': resultado}, ensure_ascii=False, indent=2))
