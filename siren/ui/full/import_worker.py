# -*- coding: utf-8 -*-
"""Threads de importação - nunca travam a janela, todas fazem chamada de
rede de verdade (YouTube ou ECHO)."""
from PySide6.QtCore import QThread, Signal

from siren.integrations import echo_client
from siren.integrations import importador_youtube


class ImportYoutubeWorker(QThread):
    concluido = Signal(list)  # lista de {"titulo", "artista"} (vazia se falhou)

    def __init__(self, url, parent=None):
        super().__init__(parent)
        self._url = url

    def run(self):
        faixas = importador_youtube.importar_playlist(self._url)
        self.concluido.emit(faixas)


class ImportEchoAprovadasWorker(QThread):
    """Busca as faixas com 👍 do ECHO (mesmo discord_user_id que o Modo
    Música do ERIS usa) - só busca, quem aplica (favoritar + playlist
    Descobertas) é `core/importar_votos_echo.py`, chamado por quem conecta
    esse sinal."""
    concluido = Signal(list)  # lista de entradas do ECHO (vazia se o ECHO estiver fora do ar)

    def run(self):
        self.concluido.emit(echo_client.obter_aprovados())
