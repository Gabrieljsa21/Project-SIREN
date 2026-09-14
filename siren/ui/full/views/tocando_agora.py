# -*- coding: utf-8 -*-
"""Letras sincronizadas abertas sob demanda pelo player persistente.

Tradução é SEMPRE sob demanda (botão
"Traduzir"), nunca automática - pedido do usuário (2026-09-06): "na maioria
das vezes não vou querer saber da letra"."""
from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtWidgets import (
    QLabel, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout, QWidget,
)

from siren.core import config as config_mod
from siren.integrations import lyrics as lyrics_mod
from siren.integrations import traducao as traducao_mod

INTERVALO_SINCRONIA_MS = 400


class _TraduzirWorker(QThread):
    concluido = Signal(object)

    def __init__(self, linhas, parent=None):
        super().__init__(parent)
        self._linhas = [dict(linha) for linha in linhas]

    def run(self):
        self.concluido.emit(traducao_mod.traduzir_linhas(self._linhas))


class ViewTocandoAgora(QWidget):
    def __init__(self, ao_iniciar_caos, player):
        super().__init__()
        self._ao_iniciar_caos = ao_iniciar_caos
        self._player = player
        self._linhas_letra = []
        self._indice_linha_atual = None
        self._worker_traducao = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(14)

        titulo = QLabel("Letras")
        titulo.setObjectName("tituloView")

        self._label_faixa = QLabel("Nenhuma faixa tocando")
        self._label_faixa.setStyleSheet("font-size: 22px; font-weight: 700;")
        self._label_artista = QLabel("")
        self._label_artista.setObjectName("legendaView")

        self._botao_traduzir = QPushButton("Traduzir")
        self._botao_traduzir.setObjectName("botaoSecundario")
        self._botao_traduzir.setFixedWidth(110)
        self._botao_traduzir.clicked.connect(self._traduzir)
        self._lista_letras = QListWidget()

        layout.addWidget(titulo)
        layout.addWidget(self._label_faixa)
        layout.addWidget(self._label_artista)
        layout.addWidget(self._botao_traduzir)
        layout.addWidget(self._lista_letras, stretch=1)

        self._timer_sincronia = QTimer(self)
        self._timer_sincronia.setInterval(INTERVALO_SINCRONIA_MS)
        self._timer_sincronia.timeout.connect(self._sincronizar_linha_atual)
        self._timer_sincronia.start()

    def atualizar(self):
        pass

    def definir_faixa_atual(self, titulo, artista, duracao_segundos=None):
        self._label_faixa.setText(titulo)
        self._label_artista.setText(artista)
        self._carregar_letra(titulo, artista, duracao_segundos)

    def _carregar_letra(self, titulo, artista, duracao_segundos):
        # Uma tradução antiga pode terminar depois que outra faixa começa;
        # ao tirar sua identidade daqui, o resultado atrasado é descartado.
        self._worker_traducao = None
        self._linhas_letra = []
        self._indice_linha_atual = None
        self._lista_letras.clear()
        self._botao_traduzir.setEnabled(traducao_mod.traducao_disponivel())

        if not config_mod.obter("lyrics_ativado"):
            return
        resultado = lyrics_mod.buscar_letra(titulo, artista, duracao_segundos)
        if resultado is None or not resultado["sincronizada"]:
            item = QListWidgetItem("Sem letra sincronizada disponível pra essa faixa.")
            item.setFlags(Qt.NoItemFlags)
            self._lista_letras.addItem(item)
            return

        self._linhas_letra = resultado["linhas"]
        for linha in self._linhas_letra:
            self._lista_letras.addItem(QListWidgetItem(linha["texto"]))

    def _traduzir(self):
        if not self._linhas_letra or (
            self._worker_traducao is not None and self._worker_traducao.isRunning()
        ):
            return
        self._botao_traduzir.setEnabled(False)
        self._botao_traduzir.setText("Traduzindo...")
        worker = _TraduzirWorker(self._linhas_letra, self)
        worker.concluido.connect(lambda resultado, w=worker: self._aplicar_traducao(w, resultado))
        worker.finished.connect(lambda w=worker: self._finalizar_traducao(w))
        self._worker_traducao = worker
        worker.start()

    def _aplicar_traducao(self, worker, resultado):
        if worker is not self._worker_traducao or resultado is None:
            return
        self._linhas_letra = resultado
        for i, linha in enumerate(self._linhas_letra):
            texto = linha["texto"]
            if linha.get("traducao"):
                texto += "\n" + linha["traducao"]
            self._lista_letras.item(i).setText(texto)

    def _finalizar_traducao(self, worker):
        if worker is self._worker_traducao:
            self._worker_traducao = None
            self._botao_traduzir.setText("Traduzir")
            self._botao_traduzir.setEnabled(traducao_mod.traducao_disponivel())
        worker.deleteLater()

    def _sincronizar_linha_atual(self):
        if not self._linhas_letra:
            return
        posicao = self._player.posicao_segundos
        if posicao is None:
            return
        novo_indice = None
        for i, linha in enumerate(self._linhas_letra):
            if linha["tempo_segundos"] <= posicao:
                novo_indice = i
            else:
                break
        if novo_indice is not None and novo_indice != self._indice_linha_atual:
            self._indice_linha_atual = novo_indice
            self._lista_letras.setCurrentRow(novo_indice)
            self._lista_letras.scrollToItem(self._lista_letras.item(novo_indice))
