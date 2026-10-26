# -*- coding: utf-8 -*-
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from PySide6.QtCore import QSize, Qt, QThread, Signal
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QPushButton, QVBoxLayout, QWidget,
)

from siren.core.cache_faixas import formatar_duracao
from siren.playback import resolver
from siren.ui.full import styles
from siren.ui.full.faixas import RotuloElidido

ALTURA_RESULTADO = 74

_UNIDADES_TEMPO = (
    (365 * 86400, "ano", "anos"),
    (30 * 86400, "mês", "meses"),
    (7 * 86400, "semana", "semanas"),
    (86400, "dia", "dias"),
    (3600, "hora", "horas"),
    (60, "minuto", "minutos"),
)


def formatar_contagem(numero):
    """Contagem curta como o YouTube em português: 950, 1,8 mil, 7,4 mi."""
    if numero is None:
        return None
    for base, sufixo in ((1_000_000_000, "bi"), (1_000_000, "mi"), (1_000, "mil")):
        if numero >= base:
            valor = numero / base
            # trunca como o YouTube: 7.492.948 vira "7,4 mi", nunca "7,5 mi"
            texto = f"{int(valor * 10) / 10:.1f}" if valor < 10 else f"{int(valor)}"
            return f"{texto.removesuffix('.0').replace('.', ',')} {sufixo}"
    return str(int(numero))


def formatar_data_relativa(timestamp, agora=None):
    """"há 4 anos", "há 1 mês" - mesma escala do YouTube."""
    if not timestamp:
        return None
    segundos = max(0, (agora or time.time()) - timestamp)
    for tamanho, singular, plural in _UNIDADES_TEMPO:
        if segundos >= tamanho:
            quantidade = int(segundos // tamanho)
            return f"há {quantidade} {singular if quantidade == 1 else plural}"
    return "agora há pouco"


class _BuscarWorker(QThread):
    concluido = Signal(list)

    def __init__(self, texto, parent=None):
        super().__init__(parent)
        self._texto = texto

    def run(self):
        self.concluido.emit(resolver.buscar_faixas(self._texto, limite=5))


class _DetalhesWorker(QThread):
    """Curtidas e data exata não vêm na busca: abre os vídeos em paralelo e
    entrega cada um assim que chega, sem segurar a lista."""

    detalhe = Signal(int, dict)

    def __init__(self, urls, parent=None):
        super().__init__(parent)
        self._urls = urls

    def run(self):
        with ThreadPoolExecutor(max_workers=len(self._urls)) as executor:
            futuros = {executor.submit(resolver.detalhes_video, url): i for i, url in enumerate(self._urls)}
            for futuro in as_completed(futuros):
                self.detalhe.emit(futuros[futuro], futuro.result())


class _LinhaResultado(QWidget):
    """Título, "visualizações · data · curtidas", canal e duração à direita."""

    def __init__(self, faixa):
        super().__init__()
        self._faixa = dict(faixa)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        titulo = RotuloElidido(faixa["titulo"], f"font-size: 14px; color: {styles.COR_TEXTO};")
        self._info = QLabel()
        self._info.setStyleSheet(f"font-size: 12px; color: {styles.COR_TEXTO_FRACO};")
        canal = RotuloElidido(faixa.get("canal") or faixa["artista"], f"font-size: 12px; color: {styles.COR_TEXTO_FRACO};")
        duracao = QLabel(formatar_duracao(faixa.get("duracao")))
        duracao.setStyleSheet(f"font-size: 12px; color: {styles.COR_TEXTO_FRACO};")

        textos = QVBoxLayout()
        textos.setContentsMargins(0, 0, 0, 0)
        textos.setSpacing(2)
        textos.addWidget(titulo)
        textos.addWidget(self._info)
        textos.addWidget(canal)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(16)
        layout.addLayout(textos, stretch=1)
        layout.addWidget(duracao, alignment=Qt.AlignVCenter)
        self._atualizar_info()

    def aplicar_detalhes(self, detalhes):
        for chave in ("curtidas", "data"):
            if detalhes.get(chave) is not None:
                self._faixa[chave] = detalhes[chave]
        self._atualizar_info()

    def _atualizar_info(self):
        partes = []
        visualizacoes = formatar_contagem(self._faixa.get("visualizacoes"))
        if visualizacoes:
            partes.append(f"{visualizacoes} visualizações")
        data = formatar_data_relativa(self._faixa.get("data"))
        if data:
            partes.append(data)
        curtidas = formatar_contagem(self._faixa.get("curtidas"))
        if curtidas:
            partes.append(f"{curtidas} curtidas")
        self._info.setText(" · ".join(partes))


class ViewBusca(QWidget):
    """Busca direta no YouTube; o ECHO não participa deste fluxo."""

    def __init__(self, ao_tocar):
        super().__init__()
        self._ao_tocar = ao_tocar
        self._worker = None
        self._worker_detalhes = None
        self._linhas = []

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
        self._limpar_lista()
        carregando = QListWidgetItem("Buscando...")
        carregando.setFlags(Qt.NoItemFlags)
        self._lista.addItem(carregando)
        self._botao.setEnabled(False)
        worker = _BuscarWorker(texto, self)
        worker.concluido.connect(lambda resultados, w=worker: self._mostrar_resultados(w, resultados))
        worker.finished.connect(lambda w=worker: self._finalizar_worker(w))
        self._worker = worker
        worker.start()

    def _limpar_lista(self):
        self._lista.clear()
        self._linhas = []
        self._worker_detalhes = None  # respostas de uma busca anterior são descartadas

    def _mostrar_resultados(self, worker, resultados):
        if worker is not self._worker:
            return
        self._limpar_lista()
        if not resultados:
            vazio = QListWidgetItem("Nenhum resultado encontrado.")
            vazio.setFlags(Qt.NoItemFlags)
            self._lista.addItem(vazio)
            return
        for faixa in resultados:
            item = QListWidgetItem()
            item.setData(Qt.UserRole, faixa)
            item.setSizeHint(QSize(0, ALTURA_RESULTADO))
            linha = _LinhaResultado(faixa)
            self._lista.addItem(item)
            self._lista.setItemWidget(item, linha)
            self._linhas.append(linha)
        urls = [faixa.get("url") for faixa in resultados]
        if all(urls):
            detalhes = _DetalhesWorker(urls, self)
            detalhes.detalhe.connect(lambda i, dados, w=detalhes: self._aplicar_detalhes(w, i, dados))
            detalhes.finished.connect(detalhes.deleteLater)
            self._worker_detalhes = detalhes
            detalhes.start()

    def _aplicar_detalhes(self, worker, indice, detalhes):
        if worker is self._worker_detalhes and indice < len(self._linhas):
            self._linhas[indice].aplicar_detalhes(detalhes)

    def _finalizar_worker(self, worker):
        if worker is self._worker:
            self._worker = None
            self._botao.setEnabled(True)
        worker.deleteLater()

    def _tocar_item(self, item):
        faixa = item.data(Qt.UserRole)
        if faixa:
            self._ao_tocar(faixa["titulo"], faixa["artista"], origem="busca")
