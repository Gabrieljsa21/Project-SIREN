# -*- coding: utf-8 -*-
"""Letras sincronizadas via LRCLIB (lrclib.net) - banco de letras aberto,
gratuito, sem chave de API nem login (mesmo critério que já levou o ECHO a
escolher Last.fm em vez de Spotify: sem assinatura, sem OAuth de usuário).

Devolve as linhas já PARSEADAS do formato LRC (`[mm:ss.xx]texto`) em
`tempo_segundos`/`texto` - quem chama (a UI) nunca precisa entender a
sintaxe LRC.

🔥 SEM TRADUÇÃO ainda (2026-09-06, pedido do usuário: "gosto de ter como ver
a letra e a tradução no momento que é cantada") - decisão em ABERTO, não
esquecida: LRCLIB não traduz, e as opções de tradução disponíveis (API paga,
ou chamar um LLM) rompem "SIREN funciona sozinho" (dependeriam de chave/
custo/login, contra o mesmo princípio que já levou o ECHO a escolher
provedores gratuitos e sem login). Fica registrado como pendência real em
PLANO_SIREN.md até haver decisão de produto sobre qual serviço usar."""
import re
import requests

URL_BASE = "https://lrclib.net/api/get"
USER_AGENT = "SIREN/0.1.0 (https://github.com/Gabrieljsa21/Project-SIREN)"
TIMEOUT = 10

_PADRAO_LINHA_LRC = re.compile(r"^\[(\d{2}):(\d{2})(?:\.(\d{1,3}))?\](.*)$")


def parsear_lrc(texto_lrc):
    """"[00:27.93]Listen to the wind blow" -> [{"tempo_segundos": 27.93,
    "texto": "Listen to the wind blow"}, ...] - ignora linha de metadado
    ([ar:]/[ti:]/etc., sem grupo de tempo válido) e linha vazia, mantém a
    ordem de aparição (o LRC já vem cronológico)."""
    linhas = []
    for bruta in texto_lrc.splitlines():
        m = _PADRAO_LINHA_LRC.match(bruta.strip())
        if not m:
            continue
        minutos, segundos, centesimos, texto = m.groups()
        tempo = int(minutos) * 60 + int(segundos) + (int(centesimos.ljust(3, "0")) / 1000 if centesimos else 0)
        texto = texto.strip()
        if texto:
            linhas.append({"tempo_segundos": round(tempo, 2), "texto": texto})
    return linhas


def buscar_letra(titulo, artista, duracao_segundos=None):
    """Devolve `{"sincronizada": bool, "linhas": [...], "texto_simples": str|None}`
    ou `None` se não achou nada ou a API falhou - nunca inventa letra (mesmo
    princípio da seção 27 do ECHO_SPEC: nunca inventar dado que o provedor
    não confirmou). `linhas` vem vazio quando só existe letra "simples"
    (sem timestamp) ou a faixa é instrumental - quem chama decide o que
    mostrar nesse caso."""
    params = {"artist_name": artista, "track_name": titulo}
    if duracao_segundos:
        params["duration"] = round(duracao_segundos)
    try:
        resp = requests.get(URL_BASE, params=params, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
    except Exception:
        return None
    if resp.status_code != 200:
        return None
    try:
        dados = resp.json()
    except Exception:
        return None
    if dados.get("instrumental"):
        return {"sincronizada": False, "linhas": [], "texto_simples": None}

    bruto_sincronizado = dados.get("syncedLyrics")
    linhas = parsear_lrc(bruto_sincronizado) if bruto_sincronizado else []
    return {
        "sincronizada": bool(linhas),
        "linhas": linhas,
        "texto_simples": dados.get("plainLyrics"),
    }
