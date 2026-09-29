# -*- coding: utf-8 -*-
"""Controlador de reprodução compartilhado pelas duas janelas (2026-09-26).

Antes toda a lógica de "o que toca agora e o que vem depois" morava dentro
da janela do Modo Completo (`ui/full/main_window.py`), e o Modo Leve tinha
uma cópia mais pobre (só Caos, sem fila). Com o miniplayer (Modo Leve no
estilo do Spotify) precisando de fila, aleatório, repetir e retomar sessão,
isso virou um `QObject` sem interface: as janelas só chamam os métodos e
reagem aos sinais.

Reúne:
- fila (`core/fila.py`) e Caos com fila (pedidos ao ECHO em segundo plano,
  reabastecidos quando sobram poucas faixas do Caos);
- aleatório e repetir (fila ou esta música);
- votos (ECHO + playlists Curtidas/Não Curtidas);
- capa real (thumbnail do YouTube, baixada em segundo plano);
- retomar a última faixa ao reabrir (`core/sessao.py`), carregada pausada;
- eventos de reprodução pro LOKI (`integrations/loki_events.py`);
- teclas multimídia do teclado e painel de mídia do Windows
  (`integrations/midia_windows.py`)."""
import os
import re
import time
from collections import Counter

import requests
from PySide6.QtCore import QObject, QThread, QTimer, Signal
from PySide6.QtGui import QPixmap

from siren.core import cache_faixas as cache_faixas_mod
from siren.core import config as config_mod
from siren.core import downloads as downloads_mod
from siren.core import playlists as playlists_mod
from siren.core import sessao as sessao_mod
from siren.core.fila import Fila
from siren.integrations import echo_client
from siren.integrations.loki_events import PublicadorPlayback
from siren.playback import orquestrador
from siren.playback import resolver as resolver_mod
from siren.playback.resolver import ResolvedStream

TAMANHO_FILA_CAOS = 5
MINIMO_FILA_CAOS = 2
JANELA_DIVERSIDADE = 10  # últimas faixas (tocadas + na fila) que contam pra penalidade de artista repetido
MODOS_REPETIR = ["desligado", "fila", "faixa"]
INTERVALO_PROGRESSO_MS = 500
INTERVALO_SALVAR_SESSAO = 10  # s - um encerramento forçado não passa pelo closeEvent
LIMITE_TROCA_DE_MODO = 30  # s esperando a outra janela assumir antes de desistir e seguir tocando aqui


def id_faixa(titulo, artista):
    return f"{artista.strip().lower()}::{titulo.strip().lower()}"


def chave_repeticao(titulo, artista):
    """Chave frouxa pra detectar a MESMA música escrita de jeitos
    diferentes - achado real (2026-09-26): "Ass Back Home (feat. Neon
    Hitch)" e "Ass Back Home - feat. Neon Hitch" entravam os dois. Tira
    parênteses/colchetes, trecho depois de " - " ou "feat." e pontuação."""
    titulo = re.sub(r"[\(\[].*?[\)\]]", " ", titulo.lower())
    titulo = re.split(r"\s-\s|\bfeat\.?\b|\bft\.?\b", titulo)[0]
    artista_limpo = re.sub(r"[^\w]+", "", artista.lower())
    titulo_limpo = re.sub(r"[^\w]+", "", titulo)
    return f"{artista_limpo}::{titulo_limpo}"


def formatar_tempo(segundos):
    segundos = max(0, int(segundos or 0))
    return f"{segundos // 60}:{segundos % 60:02d}"


class _CarregarCapaWorker(QThread):
    """Baixa a thumbnail fora da GUI thread - `QPixmap` só pode ser criado
    na thread principal, então aqui só trafegam os bytes."""

    concluido = Signal(str, bytes)

    def __init__(self, url, parent=None):
        super().__init__(parent)
        self._url = url

    def run(self):
        try:
            resposta = requests.get(self._url, timeout=8)
            resposta.raise_for_status()
            self.concluido.emit(self._url, resposta.content)
        except Exception:
            self.concluido.emit(self._url, b"")


class _CaosWorker(QThread):
    """Pede faixas ao ECHO fora da GUI thread. Sem `semente`, a 1ª vem de
    `/radar/semente` (início do Caos); as demais encadeiam `/radar/proxima`,
    cada uma a partir da anterior. Emite cada faixa assim que chega (a 1ª de
    um Caos novo já pode começar a tocar enquanto o resto ainda vem)."""

    faixa_pronta = Signal(int, dict)
    sem_resultado = Signal(int)

    def __init__(self, geracao, semente, excluidos, quantidade, artistas_recentes, parent=None):
        super().__init__(parent)
        self._geracao = geracao
        self._semente = semente
        self._excluidos = list(excluidos)
        self._quantidade = quantidade
        self._artistas_recentes = list(artistas_recentes)

    def _penalidades(self):
        contagem = Counter(a.strip().lower() for a in self._artistas_recentes[-JANELA_DIVERSIDADE:])
        return {f"artista::{nome}": vezes for nome, vezes in contagem.items()}

    def run(self):
        atual = self._semente
        obtidas = 0
        for _ in range(self._quantidade):
            if atual is None:
                faixa = echo_client.sugerir_semente(excluidos=self._excluidos, penalidades_sessao=self._penalidades())
            else:
                faixa = echo_client.sugerir_proxima(
                    atual["artista"], atual["titulo"], excluidos=self._excluidos, penalidades_sessao=self._penalidades(),
                )
            if not faixa:
                break
            self._excluidos.append(id_faixa(faixa["titulo"], faixa["artista"]))
            self._artistas_recentes.append(faixa["artista"])
            self.faixa_pronta.emit(self._geracao, {"titulo": faixa["titulo"], "artista": faixa["artista"]})
            obtidas += 1
            atual = faixa
        if not obtidas:
            self.sem_resultado.emit(self._geracao)


class _ResolverRetomadaWorker(QThread):
    """Resolve o áudio da faixa retomada fora da GUI thread (arquivo baixado
    primeiro, senão yt-dlp)."""

    concluido = Signal(object)

    def __init__(self, titulo, artista, parent=None):
        super().__init__(parent)
        self._titulo = titulo
        self._artista = artista

    def run(self):
        caminho_local = downloads_mod.obter_caminho_local(self._titulo, self._artista)
        if caminho_local:
            self.concluido.emit(ResolvedStream(
                url=caminho_local, title=self._titulo, artist=self._artista,
                duration=None, thumbnail=None, source="local", expires_at=float("inf"),
            ))
            return
        self.concluido.emit(resolver_mod.resolver_stream(self._titulo, self._artista))


class ControladorReproducao(QObject):
    """Sem nenhum widget. `player`: injetável nos testes (padrão: `Player`
    de verdade, sobre o MPV)."""

    # Callback do MPV chega na thread dele: Signal devolve pra GUI thread.
    _sinal_fim_de_faixa = Signal()

    faixa_mudou = Signal(object)  # dict da faixa atual (ou None)
    progresso = Signal(float, float)  # posição, duração (segundos)
    tocando_mudou = Signal(bool)
    voto_mudou = Signal(object)  # "positivo", "negativo" ou None, da faixa atual
    capa_mudou = Signal(object)  # QPixmap da capa real, ou None (sem capa: a janela usa a procedural)
    mensagem = Signal(str)  # aviso curto pro usuário (falha ao resolver, ECHO fora do ar...)
    fila_mudou = Signal()
    modos_mudaram = Signal(bool, str)  # aleatório, repetir
    votos_mudaram = Signal()  # playlists Curtidas/Não Curtidas mudaram
    troca_concluida = Signal()  # a outra janela (outro modo) assumiu a reprodução: esta pode fechar

    def __init__(self, parent=None, player=None, midia=None):
        """`midia`: controles de mídia do Windows - `None` usa os de verdade
        (se `teclas_multimidia` estiver ligado), `False` desliga (testes)."""
        super().__init__(parent)
        if player is None:
            from siren.playback.player import Player
            player = Player()
        self.player = player
        self.fila = Fila()
        self._eventos_loki = PublicadorPlayback()
        self.player.definir_volume(config_mod.obter("volume_inicial"))
        self.player.observar_fim_de_faixa(self._sinal_fim_de_faixa.emit)
        self._sinal_fim_de_faixa.connect(self._ao_fim_de_faixa)

        self.faixa_atual = None
        self.duracao = 0
        self.voto_atual = None
        self.tocando = False
        self.url_capa = None
        self._historico_sessao = []  # pilha pro "anterior", só desta sessão
        self._excluidos_sessao = []
        self._duracao_registrada = True
        self._encerrado = False

        self._retomada = None  # {"faixa", "posicao"} enquanto o áudio da faixa retomada não está carregado
        self._tocar_ao_retomar = False
        self._retomada_carregada_pausada = False
        self._ultimo_salvamento_sessao = 0.0
        self._troca_iniciada_em = None  # troca de modo em andamento (esta janela ainda tocando)

        self._geracao_caos = 0  # muda a cada Caos novo/playlist: descarta respostas atrasadas do ECHO
        self._worker_caos = None
        self.aguardando_caos = False  # usuário esperando a 1ª faixa do Caos

        self.aleatorio = bool(config_mod.obter("aleatorio"))
        repetir = config_mod.obter("repetir")
        self.repetir = repetir if repetir in MODOS_REPETIR else "desligado"
        self.player.definir_repetir_faixa(self.repetir == "faixa")

        self._timer = QTimer(self)
        self._timer.setInterval(INTERVALO_PROGRESSO_MS)
        self._timer.timeout.connect(self._atualizar_progresso)
        self._timer.start()

        if midia is None and config_mod.obter("teclas_multimidia"):
            from siren.integrations.midia_windows import ControlesMidiaWindows
            midia = ControlesMidiaWindows(self)
        self._midia = midia or None
        if self._midia is not None:
            self._midia.botao.connect(self._ao_tecla_midia)
            self.faixa_mudou.connect(lambda faixa: self._atualizar_midia())
            self.tocando_mudou.connect(self._midia.definir_tocando)

    # ---------------- utilitários ----------------

    def _ids_na_fila(self):
        return [id_faixa(f["titulo"], f["artista"]) for f in self.fila.listar()]

    @staticmethod
    def voto_local(titulo, artista):
        """Voto pelas playlists locais: instantâneo, sem esperar o ECHO."""
        chave = id_faixa(titulo, artista)
        if any(id_faixa(f["titulo"], f["artista"]) == chave for f in playlists_mod.obter_faixas(playlists_mod.NOME_PLAYLIST_CURTIDAS)):
            return "positivo"
        if any(id_faixa(f["titulo"], f["artista"]) == chave for f in playlists_mod.obter_faixas(playlists_mod.NOME_PLAYLIST_NAO_CURTIDAS)):
            return "negativo"
        return None

    def _definir_tocando(self, tocando):
        if tocando != self.tocando:
            self.tocando = tocando
            self.tocando_mudou.emit(tocando)

    def _atualizar_midia(self):
        if self._midia is not None and self.faixa_atual:
            self._midia.definir_faixa(self.faixa_atual["titulo"], self.faixa_atual["artista"], self.url_capa)
            self._midia.definir_tocando(self.tocando)

    def _ao_tecla_midia(self, nome):
        """Tecla multimídia (ou botão do painel de mídia do Windows). Play e
        pausa são separados no SMTC: só alterna se o estado for o oposto."""
        if nome == "play" and not self.tocando:
            self.alternar_play_pause()
        elif nome in ("pause", "parar") and self.tocando:
            self.alternar_play_pause()
        elif nome == "proxima":
            self.proxima()
        elif nome == "anterior":
            self.anterior()

    def _definir_voto(self, voto):
        self.voto_atual = voto
        self.voto_mudou.emit(voto)

    # ---------------- capa ----------------

    def _carregar_capa(self, url):
        self.url_capa = url
        self.capa_mudou.emit(None)
        self._atualizar_midia()
        if not url:
            return
        worker = _CarregarCapaWorker(url, self)
        worker.concluido.connect(self._aplicar_capa)
        worker.finished.connect(worker.deleteLater)
        worker.start()

    def _aplicar_capa(self, url, conteudo):
        if url != self.url_capa or not conteudo:
            return  # faixa mudou enquanto a imagem baixava
        imagem = QPixmap()
        if imagem.loadFromData(conteudo):
            self.capa_mudou.emit(imagem)

    # ---------------- tocar ----------------

    def tocar_faixa(self, titulo, artista, origem="fila"):
        self._retomada = None
        self._tocar_ao_retomar = False
        self._retomada_carregada_pausada = False
        resolvido = orquestrador.tocar_faixa(self.player, titulo, artista, origem=origem)
        if resolvido is None:
            self.mensagem.emit(f"Não consegui resolver \"{artista} - {titulo}\"")
            return False
        self.faixa_atual = {"titulo": titulo, "artista": artista, "origem": origem}
        self._historico_sessao.append(self.faixa_atual)
        self._excluidos_sessao.append(id_faixa(titulo, artista))
        self.duracao = max(0, int(resolvido.duration or 0))
        self._duracao_registrada = bool(resolvido.duration)
        if resolvido.duration:
            cache_faixas_mod.registrar(titulo, artista, duracao=resolvido.duration)
        self.faixa_mudou.emit(self.faixa_atual)
        self._carregar_capa(getattr(resolvido, "thumbnail", None))
        self._definir_voto(self.voto_local(titulo, artista))
        self._definir_tocando(True)
        self.progresso.emit(0.0, float(self.duracao))
        if origem == "caos":
            self._garantir_fila_caos()
        self._eventos_loki.faixa_iniciada(titulo, artista, origem=origem, duracao=resolvido.duration)
        return True

    def tocar_lista(self, faixas, origem):
        """Toca a 1ª faixa e põe o resto na fila, substituindo o que já
        estava enfileirado (playlists, populares do artista)."""
        if not faixas:
            return
        self._geracao_caos += 1
        self.aguardando_caos = False
        self.fila.limpar()
        for faixa in faixas[1:]:
            self.fila.adicionar(faixa["titulo"], faixa["artista"], origem=origem)
        self.fila_mudou.emit()
        self.tocar_faixa(faixas[0]["titulo"], faixas[0]["artista"], origem=origem)

    def enfileirar(self, faixa, origem):
        self.fila.adicionar(faixa["titulo"], faixa["artista"], origem=origem)
        self.fila_mudou.emit()

    def proxima(self, reciclar=True):
        """A fila local tem prioridade (docs/PLANO_SIREN.md: o SIREN manda na
        fila, o ECHO só sugere). Com a fila vazia, continua pelo ECHO a
        partir da faixa atual (ou começa um Caos, se nada tocou ainda).

        Repetir "fila": a faixa que sai volta pro fim da fila antes de a
        próxima ser escolhida - menos quando ela acabou de levar 👎
        (`reciclar=False`). Aleatório: a próxima é sorteada entre as da fila."""
        if reciclar and self.repetir == "fila" and self.faixa_atual:
            atual = self.faixa_atual
            self.fila.adicionar(atual["titulo"], atual["artista"], origem=atual.get("origem", "fila"))
        proxima = self.fila.proxima(aleatorio=self.aleatorio)
        if proxima:
            self.fila_mudou.emit()
            self.tocar_faixa(proxima["titulo"], proxima["artista"], origem=proxima.get("origem", "fila"))
            return
        self.iniciar_caos(semente=self.faixa_atual)

    def anterior(self):
        if len(self._historico_sessao) < 2:
            return
        self._historico_sessao.pop()
        anterior = self._historico_sessao.pop()
        self.tocar_faixa(anterior["titulo"], anterior["artista"], origem=anterior.get("origem", "fila"))

    def _ao_fim_de_faixa(self):
        self._eventos_loki.faixa_encerrada("fim")
        self.proxima()

    def alternar_play_pause(self):
        """Sem faixa nenhuma: começa um Caos (atalho do miniplayer)."""
        if self.faixa_atual is None:
            self.iniciar_caos()
            return
        if self._retomada is not None:
            # Áudio da faixa retomada ainda resolvendo: toca assim que chegar.
            self._tocar_ao_retomar = not self._tocar_ao_retomar
            self._definir_tocando(self._tocar_ao_retomar)
            return
        if self._retomada_carregada_pausada:
            self._retomada_carregada_pausada = False
            self.player.alternar_pausa()
            self._iniciar_reproducao_retomada()
            return
        self.player.alternar_pausa()
        self._definir_tocando(not self.player.pausado)
        self._eventos_loki.pausa_alterada(self.player.pausado)

    def buscar_posicao(self, segundos):
        if self._retomada is not None:
            self._retomada["posicao"] = float(segundos)
            self.progresso.emit(float(segundos), float(self.duracao))
            return
        if self.faixa_atual:
            self.player.buscar_posicao(segundos)

    def definir_volume(self, volume):
        self.player.definir_volume(volume)

    def _atualizar_progresso(self):
        if self._troca_iniciada_em is not None and not self._encerrado:
            self._acompanhar_troca_de_modo()
        if not self.faixa_atual or self._retomada is not None or self._encerrado:
            return  # sem faixa, ou a retomada ainda não carregou (o MPV ainda não sabe a posição)
        duracao_player = self.player.duracao_segundos
        if duracao_player:
            self.duracao = max(0, int(duracao_player))
            if not self._duracao_registrada:
                # Faixa local (sem duração no resolvedor): o MPV descobre tocando.
                cache_faixas_mod.registrar(self.faixa_atual["titulo"], self.faixa_atual["artista"], duracao=duracao_player)
                self._duracao_registrada = True
        posicao = self.player.posicao_segundos or 0
        self._eventos_loki.progresso(posicao, self.duracao)
        self.progresso.emit(float(posicao), float(self.duracao))
        agora = time.monotonic()
        if agora - self._ultimo_salvamento_sessao >= INTERVALO_SALVAR_SESSAO:
            self._ultimo_salvamento_sessao = agora
            self.salvar_sessao()

    # ---------------- votos ----------------

    def votar_faixa(self, faixa, positivo):
        """Voto numa faixa qualquer (fila, tela do artista): ECHO + playlists
        locais, sem pular nada."""
        echo_client.enviar_feedback(faixa["artista"], faixa["titulo"], "positivo" if positivo else "negativo")
        playlists_mod.registrar_voto(faixa["titulo"], faixa["artista"], positivo=positivo)
        if self.faixa_atual and id_faixa(faixa["titulo"], faixa["artista"]) == id_faixa(self.faixa_atual["titulo"], self.faixa_atual["artista"]):
            self._definir_voto("positivo" if positivo else "negativo")
        self.votos_mudaram.emit()

    def curtir(self):
        if self.faixa_atual:
            self.votar_faixa(self.faixa_atual, True)

    def nao_curtir(self):
        """👎 na faixa atual pula pra próxima (sem reciclar no Repetir fila)."""
        if not self.faixa_atual:
            return
        self.votar_faixa(self.faixa_atual, False)
        self.proxima(reciclar=False)

    # ---------------- aleatório e repetir ----------------

    def alternar_aleatorio(self):
        self.aleatorio = not self.aleatorio
        config_mod.definir("aleatorio", self.aleatorio)
        self.modos_mudaram.emit(self.aleatorio, self.repetir)

    def alternar_repetir(self):
        """Desligado -> fila -> esta música -> desligado, como no Spotify."""
        self.repetir = MODOS_REPETIR[(MODOS_REPETIR.index(self.repetir) + 1) % len(MODOS_REPETIR)]
        config_mod.definir("repetir", self.repetir)
        self.player.definir_repetir_faixa(self.repetir == "faixa")
        self.modos_mudaram.emit(self.aleatorio, self.repetir)

    # ---------------- Caos com fila ----------------

    def _iniciar_worker_caos(self, semente, quantidade):
        artistas_recentes = [f["artista"] for f in self._historico_sessao + self.fila.listar()]
        worker = _CaosWorker(
            self._geracao_caos, semente, self._excluidos_sessao + self._ids_na_fila(), quantidade, artistas_recentes, self,
        )
        worker.faixa_pronta.connect(self._ao_receber_faixa_caos)
        worker.sem_resultado.connect(self._ao_caos_sem_resultado)
        worker.finished.connect(lambda w=worker: self._finalizar_worker_caos(w))
        self._worker_caos = worker
        worker.start()

    def iniciar_caos(self, semente=None):
        """Caos novo: substitui a fila (como tocar uma playlist), toca a 1ª
        faixa assim que o ECHO responder e enfileira as próximas. Com
        `semente`, continua a partir dela (fila acabou no meio da sessão)."""
        self._geracao_caos += 1
        self.fila.limpar()
        self.fila_mudou.emit()
        self.aguardando_caos = True
        self._iniciar_worker_caos(semente, 1 + TAMANHO_FILA_CAOS)

    def _garantir_fila_caos(self):
        """Chamado toda vez que uma faixa do Caos começa: com menos de
        `MINIMO_FILA_CAOS` faixas do Caos na fila, pede mais em segundo
        plano, continuando da última enfileirada.

        Checa `_worker_caos is not None` (e não `isRunning()`): tocar uma
        faixa bloqueia a GUI alguns segundos, e o worker pode ter terminado
        com as faixas ainda na fila de eventos - achado real (2026-09-26):
        disparava um 2º pedido e a fila chegava a 10 faixas, com repetidas."""
        if self._worker_caos is not None:
            return
        faixas_caos = [f for f in self.fila.listar() if f.get("origem") == "caos" and f.get("voto") != "negativo"]
        if len(faixas_caos) >= MINIMO_FILA_CAOS:
            return
        semente = faixas_caos[-1] if faixas_caos else self.faixa_atual
        if semente is None:
            return
        self._iniciar_worker_caos(semente, TAMANHO_FILA_CAOS - len(faixas_caos))

    def _ao_receber_faixa_caos(self, geracao, faixa):
        if geracao != self._geracao_caos:
            return  # Caos antigo (trocou de playlist ou pediu outro Caos no meio)
        chave = chave_repeticao(faixa["titulo"], faixa["artista"])
        ja_vistas = {chave_repeticao(f["titulo"], f["artista"]) for f in self._historico_sessao + self.fila.listar()}
        if chave in ja_vistas:
            return
        if self.aguardando_caos:
            self.aguardando_caos = False
            self.tocar_faixa(faixa["titulo"], faixa["artista"], origem="caos")
            return
        self.fila.adicionar(faixa["titulo"], faixa["artista"], origem="caos")
        self.fila_mudou.emit()

    def _ao_caos_sem_resultado(self, geracao):
        if geracao == self._geracao_caos and self.aguardando_caos:
            self.aguardando_caos = False
            self.mensagem.emit("ECHO indisponível ou sem sugestão agora")

    def _finalizar_worker_caos(self, worker):
        if worker is self._worker_caos:
            self._worker_caos = None
        worker.deleteLater()

    # ---------------- sessão (retomar ao reabrir) ----------------

    def salvar_sessao(self, continuar=False):
        """`continuar`: a próxima abertura já retoma tocando (troca entre
        Modo Leve e Completo, que reabre o SIREN noutro processo)."""
        if not self.faixa_atual:
            return
        posicao = self._retomada["posicao"] if self._retomada is not None else (self.player.posicao_segundos or 0)
        sessao_mod.salvar(
            self.faixa_atual["titulo"], self.faixa_atual["artista"], self.faixa_atual.get("origem", "fila"),
            posicao, self.duracao, self.url_capa, continuar=continuar,
        )

    def retomar_sessao(self):
        """Mostra a última faixa na hora (sinais `faixa_mudou`/`progresso`,
        pausada) e resolve o áudio em segundo plano; quando fica pronto, o
        MPV carrega a faixa pausada na posição salva. Play antes disso toca
        assim que o áudio chegar. Se a sessão veio de uma troca de modo com
        a música tocando, já retoma tocando."""
        dados = sessao_mod.carregar()
        if not dados:
            return False
        titulo, artista, origem = dados["titulo"], dados["artista"], dados.get("origem") or "fila"
        posicao = float(dados.get("posicao") or 0)
        self.faixa_atual = {"titulo": titulo, "artista": artista, "origem": origem}
        self._historico_sessao.append(self.faixa_atual)
        self._excluidos_sessao.append(id_faixa(titulo, artista))
        self._retomada = {
            "faixa": self.faixa_atual, "posicao": posicao,
            "pid_troca": dados.get("pid") if dados.get("continuar") and dados.get("pid") != os.getpid() else None,
        }
        self._tocar_ao_retomar = bool(dados.get("continuar"))
        self.duracao = int(dados.get("duracao") or 0)
        self.faixa_mudou.emit(self.faixa_atual)
        self._carregar_capa(dados.get("thumbnail"))
        self._definir_voto(self.voto_local(titulo, artista))
        self._definir_tocando(self._tocar_ao_retomar)
        self.progresso.emit(posicao, float(self.duracao))

        worker = _ResolverRetomadaWorker(titulo, artista, self)
        worker.concluido.connect(self._ao_resolver_retomada)
        worker.finished.connect(worker.deleteLater)
        self._worker_retomada = worker
        worker.start()
        return True

    def _ao_resolver_retomada(self, resolvido):
        retomada = self._retomada
        if retomada is None or retomada["faixa"] is not self.faixa_atual:
            return  # outra faixa começou a tocar enquanto esta resolvia
        self._retomada = None
        if resolvido is None:
            self.mensagem.emit("Não consegui carregar a última faixa")
            return
        tocar_agora = self._tocar_ao_retomar
        self._tocar_ao_retomar = False
        posicao = retomada["posicao"]
        if retomada.get("pid_troca"):
            # Troca de modo: a outra janela seguiu tocando enquanto esta
            # carregava - pega a posição mais recente dela.
            atual = sessao_mod.carregar()
            if atual and atual.get("titulo") == self.faixa_atual["titulo"] and atual.get("artista") == self.faixa_atual["artista"]:
                posicao = sessao_mod.posicao_atualizada(atual)
        self.player.tocar(resolvido, pausado=not tocar_agora, inicio=posicao)
        if retomada.get("pid_troca"):
            sessao_mod.sinalizar_troca_concluida(retomada["pid_troca"])
        self._retomada_carregada_pausada = not tocar_agora
        if resolvido.duration and not self.duracao:
            self.duracao = int(resolvido.duration)
            self.progresso.emit(retomada["posicao"], float(self.duracao))
        if not self.url_capa and resolvido.thumbnail:
            self._carregar_capa(resolvido.thumbnail)
        if tocar_agora:
            self._iniciar_reproducao_retomada()

    def _iniciar_reproducao_retomada(self):
        faixa = self.faixa_atual
        self._definir_tocando(True)
        self._eventos_loki.faixa_iniciada(faixa["titulo"], faixa["artista"], origem=faixa.get("origem", "fila"), duracao=self.duracao or None)
        if faixa.get("origem") == "caos":
            self._garantir_fila_caos()

    # ---------------- troca de modo sem parar a música ----------------

    def iniciar_troca_de_modo(self):
        """Chamado antes de abrir a janela do outro modo. Tocando: continua
        tocando aqui e grava a sessão várias vezes por segundo (com
        `continuar`) até a outra janela avisar que assumiu
        (`troca_concluida`). Parado: só grava e devolve False - quem chama
        pode fechar na hora."""
        if not self.tocando or self._retomada is not None:
            self.salvar_sessao()
            return False
        self._troca_iniciada_em = time.monotonic()
        self.salvar_sessao(continuar=True)
        # Mais rápido durante a troca: posição gravada mais fresca, e esta
        # janela para até ~0,1 s depois de a outra começar a tocar.
        self._timer.setInterval(100)
        return True

    def _acompanhar_troca_de_modo(self):
        if sessao_mod.troca_concluida_para(os.getpid()):
            self._troca_iniciada_em = None
            self._assumida_por_outra_janela = True
            self.troca_concluida.emit()
            return
        if time.monotonic() - self._troca_iniciada_em > LIMITE_TROCA_DE_MODO:
            self._troca_iniciada_em = None
            self._timer.setInterval(INTERVALO_PROGRESSO_MS)
            self.salvar_sessao()
            self.mensagem.emit("O outro modo não abriu - a música continua aqui")
            return
        self.salvar_sessao(continuar=True)

    # ---------------- encerrar ----------------

    def encerrar(self, continuar=False):
        """Salva a sessão, avisa o LOKI e desliga o MPV. Idempotente (o
        closeEvent pode chegar 2x). Depois de uma troca de modo concluída
        não grava nada: a sessão agora é da outra janela."""
        if self._encerrado:
            return
        if not getattr(self, "_assumida_por_outra_janela", False):
            self.salvar_sessao(continuar=continuar and self.tocando)
        self._encerrado = True
        self._timer.stop()
        if self._midia is not None:
            self._midia.encerrar()
        self._eventos_loki.faixa_encerrada("player_fechado")
        self.player.encerrar()
