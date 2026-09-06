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


def tocar_faixa(player, titulo, artista, origem="fila"):
    """Devolve `True` se conseguiu tocar (local ou resolvida pela rede),
    `False` se não achou em lugar nenhum - quem chama decide como comunicar
    a falha na UI (nunca inventa uma faixa)."""
    caminho_local = downloads_mod.obter_caminho_local(titulo, artista)
    if caminho_local:
        resolved = ResolvedStream(
            url=caminho_local, title=titulo, artist=artista,
            duration=None, thumbnail=None, source="local", expires_at=float("inf"),
        )
    else:
        resolved = resolver_mod.resolver_stream(titulo, artista)
        if resolved is None:
            return False

    player.tocar(resolved)
    historico_mod.registrar(titulo, artista, origem=origem)
    return True
