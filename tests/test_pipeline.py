"""Dublês em bancos temporários; não são evidência de chamadas reais."""
import csv
import json
from pathlib import Path
import pytest
from pydantic import ValidationError
from pipeline import Pipeline, Config, ManifestacaoEstruturada, ProvedoresReais
from anonimizar_texto import anonimizar_texto


def valido(resumo='Cliente pede informação.'):
    return ManifestacaoEstruturada(urgencia='normal', sentimento='neutro', categoria_produto='conta', valor_citado=None, resumo=resumo)


class Duble:
    def __init__(self, falhar=False, invalido=False):
        self.calls = []
        self.falhar, self.invalido = falhar, invalido
    def chamar(self, provedor, texto):
        self.calls.append(provedor)
        if self.falhar:
            raise TimeoutError()
        if self.invalido:
            return None
        return valido('Cliente com CPF 456.789.123-00 pede informação.')


def csv_file(tmp, rows):
    path = tmp / 'entrada.csv'
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['id', 'texto'])
        w.writerows(rows)
    return path


def novo(tmp, d):
    return Pipeline(tmp/'teste.db', provedores=d, config=Config(intervalo_gemini=0, intervalo_groq=0, backoff=0), sleep=lambda _: None)


def test_fallback_forcado_retomada_e_resumo(tmp_path):
    d = Duble()
    path = csv_file(tmp_path, [('1', 'Informação sobre conta.'), ('5', 'Suspeito de fraude. CPF 456.789.123-00')])
    p = novo(tmp_path, d)
    p.executar(path)
    assert d.calls == ['gemini', 'groq']
    assert p.verificar_fallback_real() == {'mistura_gemini_groq': True, 'fallbacks_forcados_concluidos': 1}
    row = p.conn.execute("SELECT * FROM manifestacoes WHERE id='5'").fetchone()
    assert row['urgencia'] == 'urgente'
    assert '456.789.123-00' in row['resumo']
    assert '456.789.123-00' not in row['resumo_anonimizado']
    assert p.conn.execute("SELECT COUNT(*) FROM tentativas WHERE resultado='FalhaForcada'").fetchone()[0] == 3
    p.fechar()
    p = novo(tmp_path, d)
    p.executar(path)
    assert d.calls == ['gemini', 'groq']
    assert p.conn.execute('SELECT COUNT(*) FROM manifestacoes').fetchone()[0] == 2
    p.fechar()


def test_cache_persistido_entre_ids(tmp_path):
    d = Duble()
    p = novo(tmp_path, d)
    p.executar(csv_file(tmp_path, [('1', 'Mesmo texto.')]))
    p.fechar()
    p = novo(tmp_path, d)
    p.executar(csv_file(tmp_path, [('2', 'Mesmo texto.')]))
    assert len(d.calls) == 1
    assert p.metricas['cache'] == 1
    p.fechar()


def test_parsed_none_revisao_sem_retentativa_automatica(tmp_path):
    d = Duble(invalido=True)
    p = novo(tmp_path, d)
    path = csv_file(tmp_path, [('1', 'Informação.')])
    p.executar(path)
    p.executar(path)
    assert len(d.calls) == 1
    r = p.conn.execute('SELECT * FROM manifestacoes').fetchone()
    assert r['status'] == 'revisao_humana' and r['resumo'] is None and r['provedor'] is None
    p.fechar()


def test_sdk_parsed_none():
    from types import SimpleNamespace
    p = ProvedoresReais.__new__(ProvedoresReais)
    p.config = Config()
    p.gemini = SimpleNamespace(models=SimpleNamespace(generate_content=lambda **kw: SimpleNamespace(parsed=None)))
    from pipeline import RevisaoHumana
    with pytest.raises(RevisaoHumana, match='parsed_none'):
        p.chamar('gemini', 'Texto.')


def test_backoff_e_falha_total(tmp_path):
    esperas = []
    d = Duble(falhar=True)
    p = Pipeline(tmp_path/'falha.db', provedores=d, config=Config(intervalo_gemini=0, intervalo_groq=0, backoff=2), sleep=esperas.append)
    p.executar(csv_file(tmp_path, [('1', 'Dúvida.')]))
    assert d.calls == ['gemini'] * 3 + ['groq'] * 3
    assert [e for e in esperas if e > 0] == [2, 4, 2, 4]
    assert p.conn.execute('SELECT status FROM manifestacoes').fetchone()[0] == 'revisao_humana'
    p.fechar()


def test_throttling_proativo(tmp_path):
    agora, esperas = [0.0], []
    def dormir(n):
        esperas.append(n)
        agora[0] += n
    p = Pipeline(tmp_path/'tempo.db', provedores=Duble(), config=Config(intervalo_gemini=15), sleep=dormir, clock=lambda: agora[0])
    p.executar(csv_file(tmp_path, [('1', 'Primeiro.'), ('2', 'Segundo.')]))
    assert esperas == [0, 15]
    p.fechar()


def test_offline_nao_fabrica_dados(tmp_path):
    p = novo(tmp_path, Duble())
    path = csv_file(tmp_path, [('1', 'CPF 45678912300.')])
    p.executar(path, offline=True)
    row = p.conn.execute('SELECT * FROM manifestacoes').fetchone()
    assert row['status'] == 'pendente_api' and row['provedor'] is None and row['resumo'] is None
    assert row['texto'] == 'CPF 45678912300.'
    assert '45678912300' not in row['texto_anonimizado']
    p.executar(path, offline=False)
    assert p.conn.execute('SELECT status FROM manifestacoes').fetchone()[0] == 'concluido'
    p.fechar()


def test_mudanca_texto_invalida_idempotencia(tmp_path):
    d = Duble()
    p = novo(tmp_path, d)
    p.executar(csv_file(tmp_path, [('1', 'Texto A.')]))
    p.executar(csv_file(tmp_path, [('1', 'Texto B.')]))
    assert len(d.calls) == 2
    assert p.conn.execute('SELECT COUNT(*) FROM manifestacoes').fetchone()[0] == 1
    p.fechar()


def test_exportacao_tem_lista_fechada(tmp_path):
    p = novo(tmp_path, Duble())
    p.executar(csv_file(tmp_path, [('1', 'CPF 456.789.123-00.')]))
    with pytest.raises(RuntimeError):
        p.exportar(tmp_path/'externo.csv')
    p.exportar(tmp_path/'externo.csv', revisao_aprovada=True)
    with (tmp_path/'externo.csv').open(encoding='utf-8', newline='') as f:
        data = list(csv.DictReader(f))
    assert 'texto' not in data[0] and 'resumo' not in data[0]
    assert '456.789.123-00' not in (tmp_path/'externo.csv').read_text(encoding='utf-8')
    p.fechar()


def test_regex_identificadores_fora_do_dataset():
    texto = 'CPF 456.789.123-00; RG 98.765.432-X; conta corrente 123456-7; agência 4321; email nome.sobrenome+teste@dominio.org.br.'
    saida = anonimizar_texto(texto)
    for original in ['456.789.123-00', '98.765.432-X', '123456-7', '4321', 'nome.sobrenome+teste@dominio.org.br']:
        assert original not in saida
    for marcador in ['[CPF]', '[RG]', '[CONTA]', '[AGENCIA]', '[EMAIL]']:
        assert marcador in saida
    assert anonimizar_texto('') == ''
    with pytest.raises(TypeError):
        anonimizar_texto(None)


def test_schema_rejeita_categorias_inventadas():
    data = valido().model_dump()
    data['urgencia'] = 'alta'
    with pytest.raises(ValidationError):
        ManifestacaoEstruturada(**data)


def test_auditoria_reproduzivel(tmp_path):
    from auditoria import avaliar
    resultado, contagens = avaliar(pasta=tmp_path)
    salvo = json.loads(Path('auditoria_resultado.json').read_text(encoding='utf-8'))
    assert resultado == salvo
    assert contagens['manifestacoes_rotuladas'] == 40
    assert len(resultado['casos_de_erro']) >= 2


def test_modelo_groq_padrao_nao_esta_descontinuado():
    assert Config().groq_model not in {'llama-3.3-70b-versatile', 'llama-3.1-8b-instant'}


def test_anonimizacao_nomes_por_contexto_e_agencia_abreviada():
    saida = anonimizar_texto('Meu nome e Ana Clara Souza, ag 1234, conta 55555-1. Falei com o gerente Paulo Reis.')
    for original in ['Ana Clara Souza', '1234', '55555-1', 'Paulo Reis']:
        assert original not in saida


def test_verbo_inicial_nao_vira_nome():
    assert anonimizar_texto('Fui cobrado duas vezes na fatura.').startswith('Fui cobrado')
    assert anonimizar_texto('Envie a confirmacao hoje.').startswith('Envie a')


def test_reanonimizar_atualiza_sem_tocar_originais(tmp_path):
    d = Duble()
    p = novo(tmp_path, d)
    p.executar(csv_file(tmp_path, [('1', 'CPF 456.789.123-00.')]))
    p.conn.execute("UPDATE manifestacoes SET texto_anonimizado='velho', resumo_anonimizado='velho'")
    p.conn.commit()
    p.executar(csv_file(tmp_path, [('1', 'CPF 456.789.123-00.')]))
    r = p.conn.execute('SELECT * FROM manifestacoes').fetchone()
    assert r['texto'] == 'CPF 456.789.123-00.' and r['texto_anonimizado'] == 'CPF [CPF].'
    assert '456.789.123-00' not in r['resumo_anonimizado']
    assert len(d.calls) == 1
    p.fechar()
