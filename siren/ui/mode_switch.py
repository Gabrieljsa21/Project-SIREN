# -*- coding: utf-8 -*-
"""Alternar entre Modo Leve e Completo sem precisar editar `data/config.json`
na mão nem usar terminal - pedido do usuário (2026-09-06): "pode manter o
completo padrão, mas tem que ser possível trocar entre eles". Salva o novo
modo como padrão (próximas aberturas - IRIS, atalho, etc. - já abrem no modo
escolhido) e sobe a OUTRA janela num processo novo antes de fechar esta."""
import subprocess
import sys

from siren.core import config as config_mod


def trocar_modo(app, janela, novo_modo):
    """`novo_modo`: "lite" ou "full". `janela.close()` já dispara o
    `closeEvent` de cada janela (que encerra o player) - não repete essa
    limpeza aqui, pra nunca chamar `player.encerrar()` duas vezes."""
    config_mod.definir("modo_ui", novo_modo)
    subprocess.Popen([sys.executable, "-m", "siren.main", f"--{novo_modo}"])
    janela.close()
    app.quit()
