# -*- coding: utf-8 -*-
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout, QWidget


class ViewFila(QWidget):
    """Mostra o conteúdo de uma `core.fila.Fila` compartilhada com a janela
    principal - este widget nunca é dono da fila, só a lê/reordena."""

    def __init__(self, fila, ao_tocar):
        super().__init__()
        self._fila = fila
        self._ao_tocar = ao_tocar

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(10)

        titulo = QLabel("Fila")
        titulo.setObjectName("tituloView")
        legenda = QLabel("Autoridade é sempre do SIREN - o ECHO só sugere quem entra, nunca decide a ordem.")
        legenda.setObjectName("legendaView")

        self._lista = QListWidget()
        self._lista.itemActivated.connect(self._tocar_item)

        linha_botoes = QHBoxLayout()
        botao_subir = QPushButton("↑ Subir")
        botao_subir.setObjectName("botaoSecundario")
        botao_subir.clicked.connect(lambda: self._mover(-1))
        botao_descer = QPushButton("↓ Descer")
        botao_descer.setObjectName("botaoSecundario")
        botao_descer.clicked.connect(lambda: self._mover(1))
        botao_remover = QPushButton("Remover")
        botao_remover.setObjectName("botaoSecundario")
        botao_remover.clicked.connect(self._remover)
        linha_botoes.addWidget(botao_subir)
        linha_botoes.addWidget(botao_descer)
        linha_botoes.addWidget(botao_remover)
        linha_botoes.addStretch()

        layout.addWidget(titulo)
        layout.addWidget(legenda)
        layout.addWidget(self._lista, stretch=1)
        layout.addLayout(linha_botoes)

    def _indice_selecionado(self):
        linha = self._lista.currentRow()
        return linha if linha >= 0 else None

    def _mover(self, delta):
        indice = self._indice_selecionado()
        if indice is None:
            return
        novo_indice = indice + delta
        self._fila.mover(indice, delta)
        self.atualizar()
        if 0 <= novo_indice < self._lista.count():
            self._lista.setCurrentRow(novo_indice)

    def _remover(self):
        indice = self._indice_selecionado()
        if indice is not None:
            self._fila.remover(indice)
            self.atualizar()

    def _tocar_item(self, item):
        faixa = item.data(Qt.UserRole)
        self._ao_tocar(faixa["titulo"], faixa["artista"], origem=faixa.get("origem", "fila"))

    def atualizar(self):
        self._lista.clear()
        faixas = self._fila.listar()
        if not faixas:
            item = QListWidgetItem("Fila vazia - toque algo de uma playlist ou peça Caos.")
            item.setFlags(Qt.NoItemFlags)
            self._lista.addItem(item)
            return
        for faixa in faixas:
            texto = f"{faixa['titulo']} - {faixa['artista']} ({faixa.get('origem', 'fila')})"
            item = QListWidgetItem(texto)
            item.setData(Qt.UserRole, faixa)
            self._lista.addItem(item)
