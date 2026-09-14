# -*- coding: utf-8 -*-
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QPushButton, QVBoxLayout, QWidget,
)

from siren.playback import resolver


class _BuscarWorker(QThread):
    concluido = Signal(list)

    def __init__(self, texto, parent=None):
        super().__init__(parent)
        self._texto = texto

    def run(self):
        self.concluido.emit(resolver.buscar_faixas(self._texto, limite=5))


class ViewBusca(QWidget):
    """Busca direta no YouTube; o ECHO não participa deste fluxo."""

    def __init__(self, ao_tocar):
        super().__init__()
        self._ao_tocar = ao_tocar
        self._worker = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(10)

        titulo = QLabel("Busca")
        titulo.setObjectName("tituloView")
        legenda = QLabel("Pesquise diretamente no YouTube, mesmo quando o ECHO estiver offline.")
        legenda.setObjectName("legendaView")

        self._campo = QLineEdit()
        self._campo.setPlaceholderText("Música, artista ou os dois")
        self._campo.returnPressed.connect(self._buscar)
        self._botao = QPushButton("Buscar")
        self._botao.setObjectName("botaoAccent")
        self._botao.clicked.connect(self._buscar)

        linha = QHBoxLayout()
        linha.addWidget(self._campo, stretch=1)
        linha.addWidget(self._botao)

        self._lista = QListWidget()
        self._lista.itemActivated.connect(self._tocar_item)

        layout.addWidget(titulo)
        layout.addWidget(legenda)
        layout.addLayout(linha)
        layout.addWidget(self._lista, stretch=1)

    def atualizar(self):
        self._campo.setFocus()

    def _buscar(self):
        self.buscar()

    def buscar(self, texto=None):
        """Executa a busca também a partir do campo global da janela."""
        if texto is not None:
            self._campo.setText(texto)
        texto = self._campo.text().strip()
        if not texto or (self._worker is not None and self._worker.isRunning()):
            return
        self._lista.clear()
        carregando = QListWidgetItem("Buscando...")
        carregando.setFlags(Qt.NoItemFlags)
        self._lista.addItem(carregando)
        self._botao.setEnabled(False)
        worker = _BuscarWorker(texto, self)
        worker.concluido.connect(lambda resultados, w=worker: self._mostrar_resultados(w, resultados))
        worker.finished.connect(lambda w=worker: self._finalizar_worker(w))
        self._worker = worker
        worker.start()

    def _mostrar_resultados(self, worker, resultados):
        if worker is not self._worker:
            return
        self._lista.clear()
        if not resultados:
            vazio = QListWidgetItem("Nenhum resultado encontrado.")
            vazio.setFlags(Qt.NoItemFlags)
            self._lista.addItem(vazio)
            return
        for faixa in resultados:
            item = QListWidgetItem(f"{faixa['titulo']} - {faixa['artista']}")
            item.setData(Qt.UserRole, faixa)
            self._lista.addItem(item)

    def _finalizar_worker(self, worker):
        if worker is self._worker:
            self._worker = None
            self._botao.setEnabled(True)
        worker.deleteLater()

    def _tocar_item(self, item):
        faixa = item.data(Qt.UserRole)
        if faixa:
            self._ao_tocar(faixa["titulo"], faixa["artista"], origem="busca")
