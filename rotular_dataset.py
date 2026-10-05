"""Rotulagem manual de PII: trechos escolhidos lendo cada manifestação.

Os rótulos não vêm do detector; a auditoria compara o detector contra eles.
"""
import csv
import json
from pathlib import Path

# Só o valor é PII (o prefixo "CPF", "conta" etc. fica fora do span).
# Nomes de atendentes e terceiros entram. Final de cartão não está na lista de PII da atividade.
ANOTACOES = {
    '3': [('Carlos Eduardo Ferreira', 'NOME')],
    '4': [('Bruno Salviano', 'NOME')],
    '5': [('123.456.789-00', 'CPF')],
    '7': [('Fernanda Albuquerque', 'NOME'), ('98765432100', 'CPF')],
    '8': [('Julia Prado', 'NOME')],
    '11': [('45231-9', 'CONTA'), ('0021', 'AGENCIA')],
    '13': [('Maria da Silva Nogueira', 'NOME')],
    '14': [('joao.pereira@gmail.com', 'EMAIL')],
    '17': [('34.567.890-1', 'RG')],
    '18': [('rafael tavares moreira', 'NOME')],
    '21': [('ana_costa99@hotmail.com', 'EMAIL')],
    '22': [('778821-4', 'CONTA')],
    '25': [('Patricia Yumi Sakamoto', 'NOME')],
    '27': [('111.222.333-44', 'CPF')],
    '29': [('501987654', 'RG')],
    '31': [('pedro henrique de castro', 'NOME')],
    '32': [('1123', 'AGENCIA'), ('998877-2', 'CONTA')],
    '34': [('Thiago Bezerra Lins', 'NOME'), ('thiago.lins@empresa.com.br', 'EMAIL')],
    '36': [('Camila', 'NOME')],
    '37': [('gustavo lima araujo', 'NOME'), ('22233344455', 'CPF')],
    '39': [('Beatriz Cristina Monteiro', 'NOME'), ('12345678', 'RG'), ('33445-5', 'CONTA')],
}


def gerar(csv_path='manifestacoes_clientes_cp5.csv', destino='rotulos_manuais.json'):
    itens = []
    with open(csv_path, encoding='utf-8-sig', newline='') as f:
        for row in csv.DictReader(f):
            spans = []
            for trecho, tipo in ANOTACOES.get(row['id'], []):
                assert row['texto'].count(trecho) == 1
                inicio = row['texto'].index(trecho)
                spans.append({'inicio': inicio, 'fim': inicio + len(trecho), 'tipo': tipo, 'trecho': trecho})
            itens.append({'id': row['id'], 'texto': row['texto'], 'pii': spans})
    Path(destino).write_text(json.dumps(itens, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return itens

if __name__ == '__main__':
    gerar()
