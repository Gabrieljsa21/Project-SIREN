# -*- coding: utf-8 -*-
"""Ponto ÚNICO de "tocar uma faixa" - compartilhado entre o Modo Leve e o
Modo Completo, pra nunca duplicar a mesma lógica em 2 janelas (a v1 tinha
isso direto dentro de `ui/main_window.py::_tocar_faixa`; virou módulo
próprio quando o Modo Completo precisou do mesmo fluxo).

Ordem de prioridade: arquivo já baixado (offline, sem rede) -> resolver via
yt-dlp (rede, `playback/resolver.py`). Sempre registra no histórico local
(`core/historico_local.py`) quando toca de verdade - inclusive no Modo
Leve, que antes não registrava nada."""
from siren.core import downloads as downloads_mod
from siren.core import historico_local as historico_mod
from siren.playback import resolver as resolver_mod
from siren.playback.resolver import ResolvedStream


def resolver_faixa(titulo, artista, url=None):
    """Só acha o áudio (arquivo baixado, senão a rede), sem tocar - pode
    levar segundos, então o controlador chama isto fora da thread da
    interface. `None` se não achou em lugar nenhum. `url`: vídeo exato
    escolhido na tela Busca."""
    caminho_local = downloads_mod.obter_caminho_local(titulo, artista)
    if caminho_local:
        return ResolvedStream(
            url=caminho_local, title=titulo, artist=artista,
            duration=None, thumbnail=None, source="local", expires_at=float("inf"),
        )
    if url:
        return resolver_mod.resolver_stream(titulo, artista, url=url)
    return resolver_mod.resolver_stream(titulo, artista)


def tocar_resolvido(player, resolved, titulo, artista, origem="fila"):
    """Toca um áudio já achado e registra no histórico local."""
    player.tocar(resolved)
    historico_mod.registrar(titulo, artista, origem=origem)


def tocar_faixa(player, titulo, artista, origem="fila"):
    """Acha e toca de uma vez (bloqueia enquanto resolve). Devolve o
    `ResolvedStream` tocado, ou `None` se não achou em lugar nenhum - quem
    chama decide como comunicar a falha na UI (nunca inventa uma faixa)."""
    resolved = resolver_faixa(titulo, artista)
    if resolved is None:
        return None
    tocar_resolvido(player, resolved, titulo, artista, origem=origem)
    return resolved
