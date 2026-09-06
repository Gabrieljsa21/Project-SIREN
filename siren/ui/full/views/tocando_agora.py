# -*- coding: utf-8 -*-
"""Tocando agora - faixa atual, atalho pro Caos, e letras sincronizadas
(PLANO_SIREN.md, seção 15). Tradução é SEMPRE sob demanda (botão
"Traduzir"), nunca automática - pedido do usuário (2026-09-06): "na maioria
das vezes não vou querer saber da letra"."""
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QButtonGroup, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QStackedWidget, QVBoxLayout, QWidget,
)

from siren.core import config as config_mod
from siren.integrations import lyrics as lyrics_mod
from siren.integrations import traducao as traducao_mod

INTERVALO_SINCRONIA_MS = 400


class ViewTocandoAgora(QWidget):
    def __init__(self, ao_iniciar_caos, player):
        super().__init__()
        self._ao_iniciar_caos = ao_iniciar_caos
        self._player = player
        self._linhas_letra = []
        self._indice_linha_atual = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(14)

        titulo = QLabel("Tocando agora")
        titulo.setObjectName("tituloView")

        self._label_faixa = QLabel("Nenhuma faixa - clique em Caos")
        self._label_faixa.setStyleSheet("font-size: 22px; font-weight: 700;")
        self._label_artista = QLabel("")
        self._label_artista.setObjectName("legendaView")

        botao_caos = QPushButton("🎲 Caos")
        botao_caos.setObjectName("botaoAccent")
        botao_caos.setFixedWidth(140)
        botao_caos.clicked.connect(self._ao_iniciar_caos)

        self._botao_aba_detalhes = QPushButton("Detalhes")
        self._botao_aba_detalhes.setObjectName("botaoSecundario")
        self._botao_aba_detalhes.setCheckable(True)
        self._botao_aba_detalhes.setChecked(True)
        self._botao_aba_letras = QPushButton("Letras")
        self._botao_aba_letras.setObjectName("botaoSecundario")
        self._botao_aba_letras.setCheckable(True)

        grupo_abas = QButtonGroup(self)
        grupo_abas.setExclusive(True)
        grupo_abas.addButton(self._botao_aba_detalhes)
        grupo_abas.addButton(self._botao_aba_letras)
        self._botao_aba_detalhes.clicked.connect(lambda: self._pilha_abas.setCurrentIndex(0))
        self._botao_aba_letras.clicked.connect(lambda: self._pilha_abas.setCurrentIndex(1))

        linha_abas = QHBoxLayout()
        linha_abas.addWidget(self._botao_aba_detalhes)
        linha_abas.addWidget(self._botao_aba_letras)
        linha_abas.addStretch()

        self._pilha_abas = QStackedWidget()

        painel_detalhes = QLabel("Sem detalhe adicional por enquanto.")
        painel_detalhes.setObjectName("legendaView")
        painel_detalhes.setWordWrap(True)

        painel_letras = QWidget()
        layout_letras = QVBoxLayout(painel_letras)
        layout_letras.setContentsMargins(0, 10, 0, 0)
        self._botao_traduzir = QPushButton("Traduzir")
        self._botao_traduzir.setObjectName("botaoSecundario")
        self._botao_traduzir.setFixedWidth(110)
        self._botao_traduzir.clicked.connect(self._traduzir)
        self._lista_letras = QListWidget()
        layout_letras.addWidget(self._botao_traduzir)
        layout_letras.addWidget(self._lista_letras, stretch=1)

        self._pilha_abas.addWidget(painel_detalhes)
        self._pilha_abas.addWidget(painel_letras)

        layout.addWidget(titulo)
        layout.addWidget(self._label_faixa)
        layout.addWidget(self._label_artista)
        layout.addWidget(botao_caos)
        layout.addLayout(linha_abas)
        layout.addWidget(self._pilha_abas, stretch=1)

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
        """Bloqueante de propósito (chamada de rede rara, só quando o
        usuário pede - ver TODO.md pra mover isso pra uma thread própria se
        um dia isso incomodar de verdade na prática)."""
        if not self._linhas_letra:
            return
        resultado = traducao_mod.traduzir_linhas(self._linhas_letra)
        if resultado is None:
            return
        self._linhas_letra = resultado
        for i, linha in enumerate(self._linhas_letra):
            texto = linha["texto"]
            if linha.get("traducao"):
                texto += "\n" + linha["traducao"]
            self._lista_letras.item(i).setText(texto)

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
