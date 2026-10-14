# -*- coding: utf-8 -*-
"""Log do que o player está fazendo (2026-10-06, pedido do usuário: "um log
das músicas passando e tudo que tá acontecendo"). Uma linha por evento em
`logs/AAAA-MM-DD.log`, com horário: faixa que começou e de onde veio, fila
do Caos pedida/recebida, voto. O SIREN roda escondido via `pythonw.exe`,
então `print` não chegaria em lugar nenhum. As sugestões do lado do ECHO
(de qual camada veio cada faixa) ficam no log do próprio ECHO."""
import datetime
import os

PASTA_LOGS = "logs"


def registrar(texto):
    agora = datetime.datetime.now()
    try:
        os.makedirs(PASTA_LOGS, exist_ok=True)
        caminho = os.path.join(PASTA_LOGS, f"{agora.date().isoformat()}.log")
        with open(caminho, "a", encoding="utf-8") as arquivo:
            arquivo.write(f"[{agora.strftime('%H:%M:%S')}] {texto}\n")
    except OSError:
        pass  # log nunca pode derrubar o player
