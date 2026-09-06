# -*- coding: utf-8 -*-
"""Wrapper fino sobre o MPV (`python-mpv`, requer `libmpv` instalado no
sistema - ver README.md) - único mecanismo de áudio do SIREN na v1. Sem
vídeo, sem interface própria do MPV; quem decide o que tocar é sempre quem
chama (`ui/main_window.py`), nunca este módulo."""
import mpv


class Player:
    def __init__(self):
        self._mpv = mpv.MPV(video=False, ytdl=False)

    def tocar(self, resolved_stream):
        """Recebe um `ResolvedStream` já resolvido (ver `playback/resolver.py`)
        - este módulo nunca resolve URL sozinho, só reproduz."""
        self._mpv.play(resolved_stream.url)

    def alternar_pausa(self):
        self._mpv.pause = not self._mpv.pause

    def parar(self):
        self._mpv.stop()

    def definir_volume(self, volume_0_a_100):
        self._mpv.volume = max(0, min(100, volume_0_a_100))

    @property
    def pausado(self):
        return bool(self._mpv.pause)

    @property
    def posicao_segundos(self):
        return self._mpv.time_pos

    def encerrar(self):
        self._mpv.terminate()
