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
DIAS_DE_LOG = 60  # logs mais velhos que isso são apagados
_limpeza_feita_em = None


def _apagar_logs_antigos(hoje):
    """Uma vez por dia. Só mexe em arquivos `AAAA-MM-DD.log`."""
    global _limpeza_feita_em
    if _limpeza_feita_em == hoje:
        return
    _limpeza_feita_em = hoje
    limite = hoje - datetime.timedelta(days=DIAS_DE_LOG)
    for nome in os.listdir(PASTA_LOGS):
        try:
            dia = datetime.date.fromisoformat(nome.removesuffix(".log"))
        except ValueError:
            continue
        if nome.endswith(".log") and dia < limite:
            os.remove(os.path.join(PASTA_LOGS, nome))


def registrar(texto):
    agora = datetime.datetime.now()
    try:
        os.makedirs(PASTA_LOGS, exist_ok=True)
        _apagar_logs_antigos(agora.date())
        caminho = os.path.join(PASTA_LOGS, f"{agora.date().isoformat()}.log")
        with open(caminho, "a", encoding="utf-8") as arquivo:
            arquivo.write(f"[{agora.strftime('%H:%M:%S')}] {texto}\n")
    except OSError:
        pass  # log nunca pode derrubar o player
