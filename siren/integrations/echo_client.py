# -*- coding: utf-8 -*-
"""Cliente HTTP pro Project ECHO (porta 8774, opcional - ver PLANO_SIREN.md
seção 2/8) - mesmo padrão de `assistant/integrations/echo_client.py` (GAIA):
toda chamada devolve sempre um valor usável (nunca deixa a exceção subir),
porque o SIREN precisa continuar funcionando com o ECHO desligado. Nenhuma
rota nova foi criada no ECHO pra isso - todas já existem, usadas hoje pelo
`/caos` do ERIS."""
import json
import os
import urllib.error
import urllib.parse
import urllib.request

URL_BASE = os.environ.get("ECHO_URL", "http://127.0.0.1:8774")
_TIMEOUT = 15

# Mesmo id fixo que `assistant/integrations/echo_client.py::DONO_DISCORD_ID`
# usa - SIREN é consumo pessoal (não social, como o Modo Música do ERIS), não
# precisa de um id por pessoa.
DONO_DISCORD_ID = "304469035607916545"


def _get(caminho, timeout=_TIMEOUT):
    try:
        with urllib.request.urlopen(URL_BASE + caminho, timeout=timeout) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read())
        except Exception:
            return None
    except Exception:
        return None


def _post(caminho, corpo, timeout=_TIMEOUT):
    try:
        dados = json.dumps(corpo).encode("utf-8")
        req = urllib.request.Request(URL_BASE + caminho, data=dados, method="POST", headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception:
        return None


def esta_disponivel():
    """True só quando o ECHO está rodando - guarda a camada opcional de
    inteligência (Caos/recomendação) atrás dessa checagem, nunca assume que
    o ECHO vai estar de pé."""
    return _get("/status") is not None


def sugerir_semente(excluidos=None):
    """`/radar/semente` - primeira sugestão de uma sessão, sem faixa de
    partida (mesmo endpoint que o `/caos` do ERIS usa). Devolve
    `{"artista", "titulo", ...}` ou `None` se o ECHO não respondeu ou não
    achou nada de qualidade."""
    dados = _post("/radar/semente", {"discord_user_id": DONO_DISCORD_ID, "excluir": list(excluidos or [])})
    if dados is None:
        return None
    return dados.get("semente")


def sugerir_proxima(artista_atual, titulo_atual, excluidos=None):
    """`/radar/proxima` - continuação a partir da faixa tocando agora."""
    dados = _post("/radar/proxima", {
        "discord_user_id": DONO_DISCORD_ID, "artista_atual": artista_atual, "titulo_atual": titulo_atual,
        "excluir": list(excluidos or []),
    })
    if dados is None:
        return None
    return dados.get("proxima")


def enviar_feedback(artista, titulo, feedback):
    """`/radar/feedback_ao_vivo` - 👍/👎 (sinal de treino do ECHO, seção 4 do
    PLANO_SIREN.md - NUNCA confundir com favoritar (★), que é local do
    SIREN e não passa por aqui). `feedback`: "positivo" ou "negativo"."""
    return _post("/radar/feedback_ao_vivo", {
        "discord_user_id": DONO_DISCORD_ID, "artista": artista, "titulo": titulo, "feedback": feedback,
    })


def obter_voto(artista, titulo):
    """`/perfil/voto` - devolve `"positivo"`/`"negativo"`/`None` se essa
    faixa já foi avaliada antes."""
    query = f"discord_user_id={DONO_DISCORD_ID}&titulo={urllib.parse.quote(titulo)}&artista={urllib.parse.quote(artista)}"
    dados = _get(f"/perfil/voto?{query}")
    return (dados or {}).get("voto")
