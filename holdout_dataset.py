"""Conjunto extra de textos escritos fora do CSV público, rotulados à mão.
Serve para medir generalização (o CSV público foi usado para ajustar o detector)."""
HOLDOUT = [
 ("Meu CPF 321.654.987-10 foi usado em uma compra que não reconheço.", [("321.654.987-10", "CPF")]),
 ("Olá, sou Roberto Almeida e quero cancelar o cartão.", [("Roberto Almeida", "NOME")]),
 ("O atendente Lucas foi muito educado, parabéns.", [("Lucas", "NOME")]),
 ("Enviei os documentos para marina.souza@outlook.com ontem.", [("marina.souza@outlook.com", "EMAIL")]),
 ("Minha agência é 0345 e a conta 56789-0, favor revisar.", [("0345", "AGENCIA"), ("56789-0", "CONTA")]),
 ("Meu RG 12.345.678-9 não foi aceito no aplicativo.", [("12.345.678-9", "RG")]),
 ("Falei com a gerente Ana Beatriz Duarte e nada foi resolvido.", [("Ana Beatriz Duarte", "NOME")]),
 ("Solicito segunda via. Atenciosamente, Joao Pedro Ramos.", [("Joao Pedro Ramos", "NOME")]),
 ("CPF 45678912345 e conta 11223-4 estão corretos?", [("45678912345", "CPF"), ("11223-4", "CONTA")]),
 ("A fatura veio com valor errado e ninguém me atende.", []),
 ("Quero saber sobre investimentos em renda fixa.", []),
 ("Segundo o Pedro, o app travou depois da atualização.", [("Pedro", "NOME")]),
 ("A ag. 2210 não abre aos sábados.", [("2210", "AGENCIA")]),
 ("O cliente Mario relatou cobrança indevida.", [("Mario", "NOME")]),
 ("Preciso falar com Fernanda sobre o meu contrato.", [("Fernanda", "NOME")]),
 ("Pix de R$ 500,00 não chegou. Conta 998-1.", [("998-1", "CONTA")]),
 ("Entre em contato pelo telefone ou escreva para suporte@fiapbank.com.br.", [("suporte@fiapbank.com.br", "EMAIL")]),
 ("Cliente Premium reclama da taxa de anuidade.", []),
 ("Ligar para Joana Dark no número cadastrado.", [("Joana Dark", "NOME")]),
 ("Documento: RG 9876543, titular José Carlos.", [("9876543", "RG"), ("José Carlos", "NOME")]),
]
