# -*- coding: utf-8 -*-
"""Janela principal do SIREN (v1) - só o caminho crítico do PLANO_SIREN.md,
seção 12: Caos -> resolve -> toca -> feedback volta pro ECHO. Fila,
biblioteca, favoritos (★), busca própria ficam pra v1.1+ (seção 10)."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QMainWindow, QPushButton, QVBoxLayout, QWidget,
)

from siren.integrations import echo_client
from siren.playback import resolver
from siren.playback.player import Player


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SIREN")
        self.resize(360, 160)

        self._player = Player()
        self._faixa_atual = None  # {"artista", "titulo"}
        self._historico_sessao = []  # pilha simples de faixas já tocadas NESTA sessão, sem persistência (histórico local de verdade é v1.4)
        self._excluidos_sessao = []  # "artista::titulo" já sugeridos - evita repetição dentro da mesma sessão

        self._label_faixa = QLabel("Nenhuma faixa - clique em Caos")
        self._label_faixa.setAlignment(Qt.AlignCenter)

        self._botao_caos = QPushButton("🎲 Caos")
        self._botao_dislike = QPushButton("👎")
        self._botao_anterior = QPushButton("⏮")
        self._botao_play_pause = QPushButton("▶")
        self._botao_proximo = QPushButton("⏭")
        self._botao_like = QPushButton("❤️")

        self._botao_caos.clicked.connect(self._iniciar_caos)
        self._botao_dislike.clicked.connect(self._dislike)
        self._botao_anterior.clicked.connect(self._tocar_anterior)
        self._botao_play_pause.clicked.connect(self._alternar_play_pause)
        self._botao_proximo.clicked.connect(self._tocar_proxima)
        self._botao_like.clicked.connect(self._like)

        linha_controles = QHBoxLayout()
        for botao in (self._botao_dislike, self._botao_anterior, self._botao_play_pause, self._botao_proximo, self._botao_like):
            linha_controles.addWidget(botao)

        layout = QVBoxLayout()
        layout.addWidget(self._label_faixa)
        layout.addWidget(self._botao_caos)
        layout.addLayout(linha_controles)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self._definir_controles_habilitados(False)

    def _definir_controles_habilitados(self, habilitado):
        for botao in (self._botao_dislike, self._botao_anterior, self._botao_play_pause, self._botao_proximo, self._botao_like):
            botao.setEnabled(habilitado)

    @staticmethod
    def _id_faixa(faixa):
        return f"{faixa['artista'].strip().lower()}::{faixa['titulo'].strip().lower()}"

    def _iniciar_caos(self):
        faixa = echo_client.sugerir_semente(excluidos=self._excluidos_sessao)
        if faixa is None:
            self._label_faixa.setText("ECHO indisponível ou sem sugestão agora")
            return
        self._tocar_faixa(faixa)

    def _tocar_proxima(self):
        if self._faixa_atual is None:
            self._iniciar_caos()
            return
        faixa = echo_client.sugerir_proxima(self._faixa_atual["artista"], self._faixa_atual["titulo"], excluidos=self._excluidos_sessao)
        if faixa is None:
            self._label_faixa.setText("ECHO não encontrou continuação agora")
            return
        self._tocar_faixa(faixa)

    def _tocar_anterior(self):
        if len(self._historico_sessao) < 2:
            return
        self._historico_sessao.pop()  # remove a faixa atual do topo
        faixa_anterior = self._historico_sessao.pop()
        self._tocar_faixa(faixa_anterior)

    def _tocar_faixa(self, faixa):
        resolved = resolver.resolver_stream(faixa["titulo"], faixa["artista"])
        if resolved is None:
            self._label_faixa.setText(f"Não consegui resolver \"{faixa['artista']} - {faixa['titulo']}\"")
            return
        self._player.tocar(resolved)
        self._faixa_atual = faixa
        self._historico_sessao.append(faixa)
        self._excluidos_sessao.append(self._id_faixa(faixa))
        self._label_faixa.setText(f"{faixa['titulo']} - {faixa['artista']}")
        self._botao_play_pause.setText("⏸")
        self._definir_controles_habilitados(True)

    def _alternar_play_pause(self):
        self._player.alternar_pausa()
        self._botao_play_pause.setText("▶" if self._player.pausado else "⏸")

    def _like(self):
        if self._faixa_atual:
            echo_client.enviar_feedback(self._faixa_atual["artista"], self._faixa_atual["titulo"], "positivo")

    def _dislike(self):
        if self._faixa_atual:
            echo_client.enviar_feedback(self._faixa_atual["artista"], self._faixa_atual["titulo"], "negativo")
            self._tocar_proxima()

    def closeEvent(self, event):
        self._player.encerrar()
        super().closeEvent(event)


def criar_aplicacao():
    app = QApplication.instance() or QApplication([])
    janela = MainWindow()
    return app, janela
