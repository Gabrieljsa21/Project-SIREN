# -*- coding: utf-8 -*-
import unicodedata

from PySide6.QtCore import QEvent, QSize, Qt, QTimer
from PySide6.QtWidgets import (
    QHBoxLayout, QInputDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QPushButton, QStackedWidget, QVBoxLayout, QWidget,
)

from siren.core import importador_texto
from siren.core import playlists as playlists_mod
from siren.ui.full.import_worker import ImportYoutubeWorker
from siren.ui.full import faixas as faixas_ui
from siren.ui.full import icones, styles
from siren.ui.full.widgets import PainelAcoesFaixa


ALTURA_LINHA = 40


def _normalizar(texto):
    """Sem acento e em minúsculas: "é" acha "e", "BEYONCÉ" acha "beyonce"."""
    sem_acento = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in sem_acento if not unicodedata.combining(c)).lower()


def faixa_combina(faixa, busca):
    """Busca da tela de playlist (2026-09-26): todas as palavras digitadas
    precisam aparecer no título ou no artista, em qualquer ordem."""
    alvo = _normalizar(f"{faixa['titulo']} {faixa['artista']}")
    return all(palavra in alvo for palavra in _normalizar(busca).split())


class LinhaFaixa(QWidget):
    """Linha da lista de uma playlist (2026-10-14, pedido do usuário: "podia
    mostrar quais estao curtidas, e permitir trocar entre os 3 status"):
    texto + o mesmo par curtir/não curtir da Fila. O texto deixa o mouse
    passar pra lista (selecionar, duplo clique pra tocar)."""

    def __init__(self, faixa, voto, ao_votar):
        super().__init__()
        self._faixa = faixa
        self._ao_votar = ao_votar
        texto = faixas_ui.RotuloElidido(f"{faixa['titulo']} - {faixa['artista']}")
        texto.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 8, 0)
        layout.setSpacing(2)
        layout.addWidget(texto, stretch=1)
        self._curtir, self._nao_curtir = faixas_ui.botoes_voto(voto, self._votar)
        layout.addWidget(self._curtir)
        layout.addWidget(self._nao_curtir)
        self.definir_voto(voto)

    def definir_voto(self, voto):
        self._voto = voto
        self._curtir.setChecked(voto == "positivo")
        self._nao_curtir.setChecked(voto == "negativo")

    def _votar(self, voto):
        # Reclicar no botão já marcado tira o voto (mesma regra da Fila).
        novo = None if self._voto == voto else voto
        self.definir_voto(novo)
        self._ao_votar(self._faixa, None if novo is None else novo == "positivo")


class ViewPlaylists(QWidget):
    def __init__(self, ao_tocar, fila=None, ao_votar=None, ao_tocar_lista=None):
        """`ao_votar(faixa, positivo)`: mesmo caminho dos votos da Fila
        (ECHO + playlists locais); `positivo=None` tira o voto.
        `ao_tocar_lista(faixas, origem)`: toca a 1ª e põe o resto na fila."""
        super().__init__()
        self._ao_tocar = ao_tocar
        self._ao_tocar_lista = ao_tocar_lista
        self._ao_votar = ao_votar
        self._playlist_atual = None
        self._worker_importacao = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(10)

        titulo = QLabel("Playlists")
        titulo.setObjectName("tituloView")
        legenda = QLabel("Criadas por você, ou pelo SIREN a partir do que você aprova. Salvas localmente.")
        legenda.setObjectName("legendaView")

        linha_topo = QHBoxLayout()
        botao_nova = QPushButton("+ Nova playlist")
        botao_nova.setObjectName("botaoSecundario")
        botao_nova.clicked.connect(self._criar_playlist)
        self._botao_importar_youtube = QPushButton("Importar do YouTube")
        self._botao_importar_youtube.setObjectName("botaoSecundario")
        self._botao_importar_youtube.clicked.connect(self._importar_do_youtube)
        botao_importar_texto = QPushButton("Colar playlist (texto)")
        botao_importar_texto.setObjectName("botaoSecundario")
        botao_importar_texto.clicked.connect(self._importar_de_texto)
        linha_topo.addWidget(botao_nova)
        linha_topo.addWidget(self._botao_importar_youtube)
        linha_topo.addWidget(botao_importar_texto)
        linha_topo.addStretch()
        self._label_status_importacao = QLabel("")
        self._label_status_importacao.setObjectName("legendaView")

        self._pilha = QStackedWidget()

        self._lista_playlists = QListWidget()
        self._lista_playlists.itemActivated.connect(self._abrir_playlist)

        painel_detalhe = QWidget()
        layout_detalhe = QVBoxLayout(painel_detalhe)
        layout_detalhe.setContentsMargins(0, 0, 0, 0)
        botao_voltar = QPushButton("← todas as playlists")
        botao_voltar.setObjectName("botaoSecundario")
        botao_voltar.clicked.connect(lambda: self._pilha.setCurrentIndex(0))
        self._rotulo_playlist_atual = QLabel("")
        self._rotulo_playlist_atual.setStyleSheet("font-weight: 700; font-size: 16px; margin-top: 8px;")
        # Filtro das faixas (pedido do usuário, 2026-09-26) - vale pra
        # qualquer playlist, inclusive Músicas Curtidas e Não Curtidas.
        self._busca = QLineEdit()
        self._busca.setObjectName("buscaGlobal")
        self._busca.setPlaceholderText("Buscar nesta playlist (título ou artista)")
        self._busca.setClearButtonEnabled(True)
        self._busca.setFixedHeight(38)
        self._busca.setMaximumWidth(420)
        self._busca.addAction(icones.icone("busca", styles.COR_TEXTO, 16), QLineEdit.LeadingPosition)
        self._busca.textChanged.connect(self._filtrar_faixas)
        self._rotulo_resultado = QLabel("")
        self._rotulo_resultado.setObjectName("legendaView")
        self._lista_faixas = QListWidget()
        self._lista_faixas.itemActivated.connect(self._tocar_faixa_selecionada)
        self._lista_faixas.verticalScrollBar().valueChanged.connect(self._criar_linhas_visiveis)
        self._lista_faixas.installEventFilter(self)
        layout_detalhe.addWidget(botao_voltar)
        layout_detalhe.addWidget(self._rotulo_playlist_atual)
        linha_busca = QHBoxLayout()
        linha_busca.addWidget(self._busca)
        linha_busca.addWidget(self._rotulo_resultado)
        linha_busca.addStretch()
        layout_detalhe.addLayout(linha_busca)
        layout_detalhe.addWidget(self._lista_faixas, stretch=1)
        self._painel_acoes = PainelAcoesFaixa(self._lista_faixas, fila=fila, origem_padrao="playlist")
        layout_detalhe.addWidget(self._painel_acoes)

        self._pilha.addWidget(self._lista_playlists)
        self._pilha.addWidget(painel_detalhe)

        layout.addWidget(titulo)
        layout.addWidget(legenda)
        layout.addLayout(linha_topo)
        layout.addWidget(self._label_status_importacao)
        layout.addWidget(self._pilha, stretch=1)

    def _criar_playlist(self):
        nome, ok = QInputDialog.getText(self, "Nova playlist", "Nome:")
        if ok and nome.strip():
            playlists_mod.criar(nome.strip())
            self.atualizar()

    def _importar_do_youtube(self):
        if self._worker_importacao is not None and self._worker_importacao.isRunning():
            self._label_status_importacao.setText("Uma playlist do YouTube já está sendo importada.")
            return
        nome, ok = QInputDialog.getText(self, "Importar do YouTube", "Nome da nova playlist:")
        if not (ok and nome.strip()):
            return
        url, ok = QInputDialog.getText(self, "Importar do YouTube", "URL da playlist do YouTube:")
        if not (ok and url.strip()):
            return

        nome = nome.strip()
        self._label_status_importacao.setText(f"Importando \"{url.strip()}\"...")
        self._botao_importar_youtube.setEnabled(False)
        self._worker_importacao = ImportYoutubeWorker(url.strip(), parent=self)
        self._worker_importacao.concluido.connect(lambda faixas: self._ao_concluir_importacao(nome, faixas))
        self._worker_importacao.finished.connect(self._finalizar_importacao_youtube)
        self._worker_importacao.start()

    def _finalizar_importacao_youtube(self):
        worker = self._worker_importacao
        self._worker_importacao = None
        self._botao_importar_youtube.setEnabled(True)
        if worker is not None:
            worker.deleteLater()

    def _importar_de_texto(self):
        nome, ok = QInputDialog.getText(self, "Colar playlist", "Nome da nova playlist:")
        if not (ok and nome.strip()):
            return
        texto, ok = QInputDialog.getMultiLineText(
            self, "Colar playlist",
            "Uma faixa por linha, no formato \"Artista - Título\" (ex.: copiado do Spotify):",
        )
        if not (ok and texto.strip()):
            return

        faixas = importador_texto.parsear_texto(texto)
        self._ao_concluir_importacao(nome.strip(), faixas)

    def _ao_concluir_importacao(self, nome, faixas):
        if not faixas:
            self._label_status_importacao.setText("Não consegui importar nenhuma faixa - confira a URL/o texto.")
            return
        playlists_mod.criar(nome)
        for faixa in faixas:
            playlists_mod.adicionar_faixa(nome, faixa["titulo"], faixa["artista"])
        self._label_status_importacao.setText(f"\"{nome}\" criada com {len(faixas)} faixa(s).")
        self.atualizar()

    def _abrir_playlist(self, item):
        self.abrir(item.data(Qt.UserRole))

    def abrir(self, nome):
        """Abre diretamente uma playlist escolhida na biblioteca lateral."""
        self._playlist_atual = nome
        self._painel_acoes.definir_origem_padrao(f"playlist:{nome}")
        self._rotulo_playlist_atual.setText(nome)
        self._lista_faixas.clear()
        for faixa in playlists_mod.obter_faixas(nome):
            if self._ao_votar is None:
                entrada = QListWidgetItem(f"{faixa['titulo']} - {faixa['artista']}")
            else:
                entrada = QListWidgetItem()  # o texto fica na LinhaFaixa
                entrada.setSizeHint(QSize(0, ALTURA_LINHA))
            entrada.setData(Qt.UserRole, faixa)
            self._lista_faixas.addItem(entrada)
        self._busca.clear()
        self._filtrar_faixas("")
        self._pilha.setCurrentIndex(1)
        QTimer.singleShot(0, self._criar_linhas_visiveis)

    def _criar_linhas_visiveis(self):
        """Cria a `LinhaFaixa` só das linhas que aparecem na tela: montar as
        998 de Não Curtidas de uma vez travava a janela por ~1,3 s. As já
        criadas ficam (rolar de volta não recria nada)."""
        if self._ao_votar is None or self._pilha.currentIndex() != 1:
            return
        lista = self._lista_faixas
        area = lista.viewport().rect()
        primeira = lista.indexAt(area.topLeft())
        if not primeira.isValid():
            return
        votos = None
        for indice in range(primeira.row(), lista.count()):
            item = lista.item(indice)
            if item.isHidden():
                continue
            if lista.visualItemRect(item).top() > area.bottom():
                break
            if lista.itemWidget(item) is None:
                if votos is None:
                    votos = playlists_mod.votos_locais()
                faixa = item.data(Qt.UserRole)
                voto = playlists_mod.voto_local(faixa["titulo"], faixa["artista"], votos)
                lista.setItemWidget(item, LinhaFaixa(faixa, voto, self._ao_votar))

    def eventFilter(self, objeto, evento):
        if objeto is self._lista_faixas and evento.type() in (QEvent.Resize, QEvent.Show):
            QTimer.singleShot(0, self._criar_linhas_visiveis)
        return super().eventFilter(objeto, evento)

    def atualizar_votos(self):
        """Voto dado em outro lugar (player, Fila, miniplayer) aparece na
        lista aberta sem recarregá-la."""
        if self._pilha.currentIndex() != 1 or self._ao_votar is None:
            return
        votos = playlists_mod.votos_locais()
        for indice in range(self._lista_faixas.count()):
            item = self._lista_faixas.item(indice)
            linha = self._lista_faixas.itemWidget(item)
            if linha is not None:
                faixa = item.data(Qt.UserRole)
                linha.definir_voto(playlists_mod.voto_local(faixa["titulo"], faixa["artista"], votos))

    def _filtrar_faixas(self, texto):
        total = self._lista_faixas.count()
        visiveis = 0
        for indice in range(total):
            item = self._lista_faixas.item(indice)
            mostrar = faixa_combina(item.data(Qt.UserRole), texto)
            item.setHidden(not mostrar)
            visiveis += mostrar
        self._rotulo_resultado.setText(f"{visiveis} de {total}" if texto.strip() else f"{total} faixas")
        QTimer.singleShot(0, self._criar_linhas_visiveis)

    def _tocar_faixa_selecionada(self, item):
        """Duplo clique toca a playlist a partir daquela faixa, com o resto
        dela na fila (2026-10-14: tocava só a faixa e o Caos assumia em
        seguida - "n ta seguindo a playlist")."""
        origem = f"playlist:{self._playlist_atual}"
        if self._ao_tocar_lista is not None:
            faixas = [self._lista_faixas.item(i).data(Qt.UserRole) for i in range(self._lista_faixas.count())]
            self._ao_tocar_lista(faixas[self._lista_faixas.row(item):], origem)
            return
        faixa = item.data(Qt.UserRole)
        self._ao_tocar(faixa["titulo"], faixa["artista"], origem=origem)

    def atualizar(self):
        self._pilha.setCurrentIndex(0)
        self._lista_playlists.clear()
        playlists = playlists_mod.listar()
        if not playlists:
            item = QListWidgetItem("Nenhuma playlist ainda - crie uma acima.")
            item.setFlags(Qt.NoItemFlags)
            self._lista_playlists.addItem(item)
            return
        for pl in playlists:
            item = QListWidgetItem(f"{pl['nome']} ({pl['quantidade']} faixas)")
            item.setData(Qt.UserRole, pl["nome"])
            self._lista_playlists.addItem(item)
