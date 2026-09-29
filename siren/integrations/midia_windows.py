# -*- coding: utf-8 -*-
"""Teclas multimídia do teclado e painel de mídia do Windows (2026-09-26,
pedido do usuário: "quero controlar o SIREN pelas teclas multimídia do
teclado").

Usa os Controles de Transporte de Mídia do Sistema (SMTC) - o mesmo
mecanismo do Spotify e dos navegadores - em vez de registrar as teclas como
atalho global: o Windows entrega play/pausa/próxima/anterior pra sessão de
mídia ativa, então o SIREN não "rouba" as teclas de outro player que esteja
tocando, e ainda aparece no painel de volume/mídia do Windows com título,
artista e capa.

O SMTC é pego de um `MediaPlayer` do WinRT sem mídia própria (o áudio
continua sendo do MPV), com o `CommandManager` desligado pra liberar os
controles. Os avisos de botão chegam numa thread do Windows: o sinal
`botao` leva pra thread do Qt. Sem os pacotes `winrt-*` (ou fora do
Windows), `disponivel` fica False e nada acontece."""
from PySide6.QtCore import QObject, Signal

try:
    from winrt.windows.foundation import Uri
    from winrt.windows.media import MediaPlaybackStatus, MediaPlaybackType, SystemMediaTransportControlsButton
    from winrt.windows.media.playback import MediaPlayer
    from winrt.windows.storage.streams import RandomAccessStreamReference
    _WINRT_OK = True
except Exception:  # pacote ausente, Windows antigo, outro sistema
    _WINRT_OK = False


def _nomes_dos_botoes():
    if not _WINRT_OK:
        return {}
    return {
        SystemMediaTransportControlsButton.PLAY: "play",
        SystemMediaTransportControlsButton.PAUSE: "pause",
        SystemMediaTransportControlsButton.STOP: "parar",
        SystemMediaTransportControlsButton.NEXT: "proxima",
        SystemMediaTransportControlsButton.PREVIOUS: "anterior",
    }


class ControlesMidiaWindows(QObject):
    """`botao` emite "play", "pause", "parar", "proxima" ou "anterior"."""

    botao = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.disponivel = False
        self._token = None
        if not _WINRT_OK:
            return
        try:
            self._player = MediaPlayer()
            self._player.command_manager.is_enabled = False
            smtc = self._player.system_media_transport_controls
            smtc.is_enabled = True
            smtc.is_play_enabled = True
            smtc.is_pause_enabled = True
            smtc.is_stop_enabled = True
            smtc.is_next_enabled = True
            smtc.is_previous_enabled = True
            smtc.playback_status = MediaPlaybackStatus.CLOSED
            self._nomes = _nomes_dos_botoes()
            self._token = smtc.add_button_pressed(self._ao_apertar)
            self._smtc = smtc
            self.disponivel = True
        except Exception:
            self.disponivel = False

    def _ao_apertar(self, _remetente, argumentos):
        # Thread do Windows: só emite; o Qt entrega na thread da interface.
        nome = self._nomes.get(argumentos.button)
        if nome:
            self.botao.emit(nome)

    def definir_faixa(self, titulo, artista, url_capa=None):
        if not self.disponivel:
            return
        try:
            atualizador = self._smtc.display_updater
            atualizador.type = MediaPlaybackType.MUSIC
            atualizador.music_properties.title = titulo or ""
            atualizador.music_properties.artist = artista or ""
            if url_capa and url_capa.startswith(("http://", "https://")):
                atualizador.thumbnail = RandomAccessStreamReference.create_from_uri(Uri(url_capa))
            else:
                atualizador.thumbnail = None
            atualizador.update()
        except Exception:
            pass

    def definir_tocando(self, tocando):
        if not self.disponivel:
            return
        try:
            self._smtc.playback_status = MediaPlaybackStatus.PLAYING if tocando else MediaPlaybackStatus.PAUSED
        except Exception:
            pass

    def encerrar(self):
        if not self.disponivel:
            return
        try:
            if self._token is not None:
                self._smtc.remove_button_pressed(self._token)
            self._smtc.display_updater.clear_all()
            self._smtc.playback_status = MediaPlaybackStatus.CLOSED
            self._smtc.is_enabled = False
        except Exception:
            pass
        self.disponivel = False
