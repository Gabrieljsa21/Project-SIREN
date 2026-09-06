# -*- coding: utf-8 -*-
"""Thread pra importar playlist do YouTube sem travar a janela - listar os
vídeos de uma playlist pode levar alguns segundos (é rede de verdade)."""
from PySide6.QtCore import QThread, Signal

from siren.integrations import importador_youtube


class ImportYoutubeWorker(QThread):
    concluido = Signal(list)  # lista de {"titulo", "artista"} (vazia se falhou)

    def __init__(self, url, parent=None):
        super().__init__(parent)
        self._url = url

    def run(self):
        faixas = importador_youtube.importar_playlist(self._url)
        self.concluido.emit(faixas)
