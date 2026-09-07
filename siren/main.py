# -*- coding: utf-8 -*-
"""Entry point do SIREN (`uv run siren` ou `python -m siren.main`).

Duas janelas possíveis - qual abre por padrão é `config.obter("modo_ui")`
("lite" ou "full"), sobrescrível na hora via `--lite`/`--full` sem precisar
mudar a configuração salva:

- Leve: janela simples de sempre (sem Acrylic/vidro fosco) - pra rodar de
  lado com jogo/programa pesado sem competir por CPU/GPU.
- Completo: biblioteca/playlists/fila/favoritos, vidro fosco tipo Argus."""
import argparse
import os
import sys

from dotenv import load_dotenv

load_dotenv(override=True)

from siren.core import config as config_mod  # noqa: E402

_CAMINHO_ICONE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "icone_siren.png")


def _analisar_argumentos():
    parser = argparse.ArgumentParser(description="SIREN - player de música pessoal")
    grupo = parser.add_mutually_exclusive_group()
    grupo.add_argument("--lite", action="store_const", const="lite", dest="modo_ui", help="força o Modo Leve, ignora a configuração salva")
    grupo.add_argument("--full", action="store_const", const="full", dest="modo_ui", help="força o Modo Completo, ignora a configuração salva")
    return parser.parse_args()


def _definir_app_user_model_id():
    """Sem isso, o SIREN e a GAIA (e qualquer satélite rodando pelo mesmo
    Python compartilhado do `uv` - `.venv/Scripts/pythonw.exe` é só um
    trampolim, o processo real sobe de `AppData\\Roaming\\uv\\python\\...\\
    python.exe`, IGUAL pra todo projeto) viram a MESMA identidade pro
    Windows agrupar na barra de tarefas - achado do usuário (2026-09-07):
    "por que siren usa o mesmo espaço de executável que a gaia?... na barra
    de tarefas elas se sobrepõem". `SetCurrentProcessExplicitAppUserModelID`
    dá um ID PRÓPRIO pra este processo, ignorando o caminho do .exe -
    precisa ser chamado ANTES de criar a QApplication/qualquer janela."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Nordware.SIREN")
    except Exception:
        pass


def main():
    _definir_app_user_model_id()
    argumentos = _analisar_argumentos()
    modo_ui = argumentos.modo_ui or config_mod.obter("modo_ui")

    if modo_ui == "full":
        from siren.ui.full.main_window import criar_aplicacao
    else:
        from siren.ui.main_window import criar_aplicacao

    app, janela = criar_aplicacao()
    if os.path.isfile(_CAMINHO_ICONE):
        from PySide6.QtGui import QIcon
        icone = QIcon(_CAMINHO_ICONE)
        app.setWindowIcon(icone)
        janela.setWindowIcon(icone)
    janela.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
