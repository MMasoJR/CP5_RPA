"""Anonimização local: NER (spaCy) para nomes e regex para identificadores estruturais.

Os spans são offsets [início, fim) no texto original e também servem à auditoria.
"""
import re
from functools import lru_cache


@lru_cache(maxsize=1)
def carregar_modelo():
    import spacy
    try:
        return spacy.load('pt_core_news_sm')
    except OSError as exc:
        raise RuntimeError('Instale o modelo: python -m spacy download pt_core_news_sm') from exc


# Não validamos dígitos verificadores: os dados de teste são fictícios.
_PADROES = [
    ('EMAIL', re.compile(r'(?<![\w.+-])[\w.!#$%&\'*+/=?^`{|}~-]+@[\w-]+(?:\.[\w-]+)+', re.UNICODE), 0),
    ('CPF', re.compile(r'(?<!\d)(?:\d{3}\.\d{3}\.\d{3}-\d{2}|\d{11})(?!\d)'), 0),
    ('RG', re.compile(r'(?<!\w)\d{1,2}\.\d{3}\.\d{3}-[\dXx](?!\w)'), 0),
    ('RG', re.compile(r'\b(?:rg|registro\s+geral)\s*(?:(?:n[º°o.]?|n[uú]mero|[ée])\s*)?[:#-]?\s*(\d[\d. -]{5,16}[\dXx])(?!\w)', re.I), 1),
    ('CONTA', re.compile(r'\b(?:conta(?:\s+(?:corrente|poupan[çc]a|banc[aá]ria))?|c/c)\s*(?:(?:n[º°o.]?|n[uú]mero|[ée])\s*)?[:#-]?\s*(\d{2,16}(?:[. ]\d{2,8})*(?:\s*-\s*[\dXx]{1,2})?)(?!\d)', re.I), 1),
    ('AGENCIA', re.compile(r'\b(?:ag[eê]ncia|ag\b\.?)\s*(?:(?:n[º°o.]?|n[uú]mero|[ée])\s*)?[:#-]?\s*(\d{3,6}(?:\s*-\s*[\dXx])?)(?!\d)', re.I), 1),
]


# Nomes introduzidos por gatilhos genéricos ("meu nome é", "cliente", "gerente"...).
# O NER do modelo pequeno do spaCy falha com nomes sem contexto sintático forte;
# o gatilho cobre esse caso sem listar nenhum nome concreto.
_NOME = r"[A-ZÀ-Ý][a-zà-ÿ'-]+(?:\s+(?:d[aeo]s?\s+)?[A-ZÀ-Ý][a-zà-ÿ'-]+){0,4}"
_GATILHOS_NOME = (
    r"(?i:meu\s+nome(?:\s+completo)?\s+(?:é|e)|me\s+chamo|sou\s+(?:o|a)?\s*(?:cliente)?|"
    r"(?:cliente|atendente|gerente|titular|sr\.?|sra\.?|senhor|senhora|dr\.?|dra\.?)|"
    r"em\s+nome\s+de|assinado(?:\s+por)?|att\.?|atenciosamente)"
)
_PADRAO_NOME_CONTEXTO = re.compile(r"\b" + _GATILHOS_NOME + r"[\s,:-]+(" + _NOME + r")")

# Verbos no imperativo/1ª pessoa iniciando a frase ("Fui", "Envie") não são pessoas.
_POS_NAO_NOME = {'VERB', 'AUX'}


def _parece_verbo_inicial(ent) -> bool:
    """Heurística: palavra única no início da frase tagueada como verbo/auxiliar,
    ou seguida de artigo/pronome ("Envie a confirmação", "Encaminho a reclamação"),
    é quase sempre verbo capitalizado e não um nome (nomes isolados vêm antes de verbo)."""
    tok = ent[0]
    inicio_frase = tok.i == 0 or tok.doc[tok.i - 1].text in {'.', '!', '?', ':', ';'}
    if tok.pos_ in _POS_NAO_NOME:
        return True
    if inicio_frase and tok.i + 1 < len(tok.doc):
        return tok.doc[tok.i + 1].pos_ in {'DET', 'PRON'}
    return False


def detectar_pii(texto: str) -> list[tuple[int, int, str]]:
    """Retorna spans não sobrepostos; padrões estruturais têm prioridade."""
    if not isinstance(texto, str):
        raise TypeError('texto deve ser str')
    if not texto:
        return []
    spans = []
    for tipo, padrao, grupo in _PADROES:
        for match in padrao.finditer(texto):
            inicio, fim = match.span(grupo)
            if not any(inicio < b and fim > a for a, b, _ in spans):
                spans.append((inicio, fim, tipo))
    for match in _PADRAO_NOME_CONTEXTO.finditer(texto):
        inicio, fim = match.span(1)
        if not any(inicio < b and fim > a for a, b, _ in spans):
            spans.append((inicio, fim, 'NOME'))
    # Ocultar identificadores com espaços preserva offsets e evita nome em e-mail.
    base = list(texto)
    for a, b, _ in spans:
        base[a:b] = ' ' * (b - a)
    for ent in carregar_modelo()(''.join(base)).ents:
        if ent.label_ != 'PER':
            continue
        if len(ent) == 1 and _parece_verbo_inicial(ent):
            continue  # verbo confundido com pessoa pelo NER
        if not any(ent.start_char < b and ent.end_char > a for a, b, _ in spans):
            spans.append((ent.start_char, ent.end_char, 'NOME'))
    return sorted(spans)


def anonimizar_texto(texto: str) -> str:
    """Mascarar pessoas, CPF, RG, conta, agência e e-mail sem alterar o original."""
    resultado = texto
    for inicio, fim, tipo in reversed(detectar_pii(texto)):
        resultado = resultado[:inicio] + f'[{tipo}]' + resultado[fim:]
    return resultado
