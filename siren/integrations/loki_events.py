"""Eventos locais de reprodução para consumidores visuais como o LOKI."""

from __future__ import annotations

import json
import os
import socket
import time
import uuid

PORTA_PADRAO = 8771
TIPOS = {"track_started", "playback_paused", "playback_resumed", "progress", "track_ended"}


class PublicadorPlayback:
    def __init__(self, host="127.0.0.1", porta=None, socket_factory=socket.socket):
        self.host = host
        self.porta = int(porta or os.getenv("LOKI_PLAYBACK_EVENT_PORT", PORTA_PADRAO))
        self._socket_factory = socket_factory
        self.session_id = uuid.uuid4().hex
        self.track_id = None
        self._sequencia = 0
        self._faixa = None
        self._ultimo_progresso_inteiro = -1

    def _publicar(self, tipo, **dados):
        if tipo not in TIPOS:
            raise ValueError(f"Evento de playback desconhecido: {tipo}")
        self._sequencia += 1
        evento = {
            "schema": "siren.playback.v1",
            "type": tipo,
            "session_id": self.session_id,
            "track_id": self.track_id,
            "sequence": self._sequencia,
            "created_at": time.time(),
            **dados,
        }
        pacote = json.dumps(evento, ensure_ascii=False).encode("utf-8")
        try:
            with self._socket_factory(socket.AF_INET, socket.SOCK_DGRAM) as canal:
                canal.sendto(pacote, (self.host, self.porta))
        except OSError:
            pass
        return evento

    def faixa_iniciada(self, titulo, artista, origem="desconhecida", duracao=None):
        if self.track_id is not None:
            self.faixa_encerrada("substituida")
        self.track_id = uuid.uuid4().hex
        self._faixa = {"titulo": titulo, "artista": artista, "origem": origem}
        self._ultimo_progresso_inteiro = -1
        return self._publicar(
            "track_started",
            track=dict(self._faixa),
            duration_seconds=float(duracao or 0),
        )

    def pausa_alterada(self, pausado):
        if self.track_id is None:
            return None
        return self._publicar("playback_paused" if pausado else "playback_resumed")

    def progresso(self, posicao, duracao=None):
        if self.track_id is None:
            return None
        inteiro = max(0, int(posicao or 0))
        if inteiro == self._ultimo_progresso_inteiro:
            return None
        self._ultimo_progresso_inteiro = inteiro
        return self._publicar(
            "progress",
            position_seconds=float(posicao or 0),
            duration_seconds=float(duracao or 0),
        )

    def faixa_encerrada(self, motivo="fim"):
        if self.track_id is None:
            return None
        evento = self._publicar("track_ended", reason=motivo, track=dict(self._faixa or {}))
        self.track_id = None
        self._faixa = None
        return evento
