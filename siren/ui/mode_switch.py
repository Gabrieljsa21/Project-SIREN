# -*- coding: utf-8 -*-
"""Alternar entre Modo Leve e Completo sem precisar editar `data/config.json`
na mão nem usar terminal - pedido do usuário (2026-09-06): "pode manter o
completo padrão, mas tem que ser possível trocar entre eles". Salva o novo
modo como padrão (próximas aberturas - IRIS, atalho, etc. - já abrem no modo
escolhido) e sobe a OUTRA janela num processo novo.

Sem parar a música (2026-09-26, pedido do usuário: "deveria abrir o modo
leve, continuar tocando apenas lá, e só então fechar o modo completo"): se
algo está tocando, esta janela continua tocando até a nova carregar e
começar do mesmo ponto - aí o controlador dela avisa (`troca_concluida`) e
esta fecha sozinha. Parada, fecha na hora (a nova retoma pausada)."""
import subprocess
import sys

from siren.core import config as config_mod


def trocar_modo(app, janela, novo_modo):
    """`novo_modo`: "lite" ou "full". A sessão é gravada ANTES de abrir o
    processo novo, pra ele já ler a faixa e o `continuar` certos."""
    config_mod.definir("modo_ui", novo_modo)
    continuar = janela.preparar_troca_de_modo() if hasattr(janela, "preparar_troca_de_modo") else False
    subprocess.Popen([sys.executable, "-m", "siren.main", f"--{novo_modo}"])
    if not continuar:
        janela.close()
        app.quit()
