# -*- coding: utf-8 -*-
"""Entry point do SIREN (`uv run siren` ou `python -m siren.main`).

Duas janelas possíveis - qual abre por padrão é `config.obter("modo_ui")`
("lite" ou "full"), sobrescrível na hora via `--lite`/`--full` sem precisar
mudar a configuração salva:

- Leve: janela simples de sempre (sem Acrylic/vidro fosco) - pra rodar de
  lado com jogo/programa pesado sem competir por CPU/GPU.
- Completo: biblioteca/playlists/fila/favoritos, vidro fosco tipo Argus."""
import argparse
import sys

from dotenv import load_dotenv

load_dotenv(override=True)

from siren.core import config as config_mod  # noqa: E402


def _analisar_argumentos():
    parser = argparse.ArgumentParser(description="SIREN - player de música pessoal")
    grupo = parser.add_mutually_exclusive_group()
    grupo.add_argument("--lite", action="store_const", const="lite", dest="modo_ui", help="força o Modo Leve, ignora a configuração salva")
    grupo.add_argument("--full", action="store_const", const="full", dest="modo_ui", help="força o Modo Completo, ignora a configuração salva")
    return parser.parse_args()


def main():
    argumentos = _analisar_argumentos()
    modo_ui = argumentos.modo_ui or config_mod.obter("modo_ui")

    if modo_ui == "full":
        from siren.ui.full.main_window import criar_aplicacao
    else:
        from siren.ui.main_window import criar_aplicacao

    app, janela = criar_aplicacao()
    janela.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
