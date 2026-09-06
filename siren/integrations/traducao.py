# -*- coding: utf-8 -*-
"""Tradução de letras SOB DEMANDA - pedido do usuário (2026-09-06): "na
maioria das vezes não vou querer saber da letra", então nenhuma linha é
traduzida sozinha - só quando o usuário clica em "Traduzir" na UI. Dois
provedores, escolhidos por `core/config.py::traducao_provedor`:

- `"gratis"` - MyMemory (api.mymemory.translated.net), sem chave, cota
  diária pequena (~5000 palavras/dia sem e-mail cadastrado), qualidade
  inferior a um LLM. Validado contra a API real.
- `"llm"` - pede pra GAIA (não fala com o Groq direto!). Achado do usuário
  (2026-09-06): "como está usando IA, isso já não foge da responsabilidade
  da SIREN e entra na GAIA?" - correto: um cliente Groq cru dentro do
  SIREN duplicaria a rotação de conta/cooldown que a GAIA já tem pronta
  (`core/agent/llm_fallback.py` de lá). Webhook reverso
  `POST /siren/traduzir_letra` na porta 8766 (mesma porta de
  `assistant/integrations/iris_bridge.py`, mesmo padrão que ERIS/MOIRAI/
  HESTIA já usam pra pedir algo à GAIA).
- `"nenhum"` (padrão) - desliga o botão de tradução de vez, sem chamada
  nenhuma a nenhum serviço externo.

Nenhum dos dois provedores é obrigatório - com `"nenhum"` (ou com a GAIA
fora do ar, no caso do "llm"), `traducao_disponivel()` avisa a UI a
esconder o botão, mantendo "SIREN funciona sozinho" (a GAIA é só mais uma
integração opcional, no mesmo espírito do ECHO)."""
import os
import requests

from siren.core import config as config_mod

TIMEOUT = 15
_URL_MYMEMORY = "https://api.mymemory.translated.net/get"
_URL_GAIA_BASE = os.environ.get("GAIA_URL", "http://127.0.0.1:8766")


def traducao_disponivel():
    provedor = config_mod.obter("traducao_provedor")
    if provedor == "llm":
        return _gaia_disponivel()
    return provedor == "gratis"


def _gaia_disponivel():
    """Ping leve (`GET /funcoes`, já existe na GAIA pra outro propósito -
    lista de tags ensinadas à LLM) - só confirma que o servidor da GAIA
    está de pé, não faz nenhuma tradução de teste."""
    try:
        resp = requests.get(f"{_URL_GAIA_BASE}/funcoes", timeout=3)
        return resp.status_code == 200
    except Exception:
        return False


def traduzir_linhas(linhas):
    """`linhas`: lista de `{"tempo_segundos", "texto"}` (mesmo formato de
    `lyrics.parsear_lrc`) - devolve a MESMA lista com uma chave `traducao`
    a mais em cada item (`None` quando essa linha específica falhou), ou
    `None` inteiro se nenhum provedor estiver configurado/disponível.
    Nunca inventa tradução quando o serviço falha."""
    provedor = config_mod.obter("traducao_provedor")
    idioma_alvo = config_mod.obter("traducao_idioma_alvo")
    if provedor == "llm":
        return _traduzir_via_gaia(linhas, idioma_alvo)
    if provedor == "gratis":
        return _traduzir_via_mymemory(linhas, idioma_alvo)
    return None


def _traduzir_via_mymemory(linhas, idioma_alvo):
    resultado = []
    for linha in linhas:
        try:
            resp = requests.get(
                _URL_MYMEMORY, params={"q": linha["texto"], "langpair": f"en|{idioma_alvo}"}, timeout=TIMEOUT,
            )
            traduzido = resp.json()["responseData"]["translatedText"]
        except Exception:
            traduzido = None
        resultado.append({**linha, "traducao": traduzido})
    return resultado


def _traduzir_via_gaia(linhas, idioma_alvo):
    """A GAIA faz 1 chamada só pra letra inteira (não 1 por linha, como o
    MyMemory) - ver `assistant/core/agent/turno.py::traduzir_linhas_letra`
    pro porquê e pro parsing de "N: texto". Aqui só a chamada HTTP; timeout
    generoso (o LLM pode precisar tentar mais de uma conta/modelo antes de
    responder, ver rotação de conta da GAIA)."""
    try:
        resp = requests.post(
            f"{_URL_GAIA_BASE}/siren/traduzir_letra",
            json={"linhas": linhas, "idioma_alvo": idioma_alvo},
            timeout=45,
        )
        return resp.json().get("linhas")
    except Exception:
        return None
