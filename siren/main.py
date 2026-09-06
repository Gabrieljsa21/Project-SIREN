# -*- coding: utf-8 -*-
"""Entry point do SIREN (`uv run siren` ou `python -m siren.main`)."""
import sys

from dotenv import load_dotenv

load_dotenv(override=True)

from siren.ui.main_window import criar_aplicacao  # noqa: E402


def main():
    app, janela = criar_aplicacao()
    janela.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
