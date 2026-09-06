# -*- coding: utf-8 -*-
"""Tradução de letras SOB DEMANDA - pedido do usuário (2026-09-06): "na
maioria das vezes não vou querer saber da letra", então nenhuma linha é
traduzida sozinha - só quando o usuário clica em "Traduzir" na UI. Dois
provedores, escolhidos por `core/config.py::traducao_provedor`:

- `"gratis"` - MyMemory (api.mymemory.translated.net), sem chave, cota
  diária pequena (~5000 palavras/dia sem e-mail cadastrado), qualidade
  inferior a um LLM. Validado contra a API real.
- `"llm"` - Groq (mesma API que a GAIA já usa), melhor qualidade, custa
  dinheiro por chamada, precisa de `GROQ_API_KEY` no ambiente.
- `"nenhum"` (padrão) - desliga o botão de tradução de vez, sem chamada
  nenhuma a nenhum serviço externo.

Nenhum dos dois provedores é obrigatório - com `"nenhum"` (ou sem
`GROQ_API_KEY` configurada, no caso do LLM), `traducao_disponivel()` avisa
a UI a esconder o botão, mantendo "SIREN funciona sozinho"."""
import os
import requests

from siren.core import config as config_mod

TIMEOUT = 15
_URL_MYMEMORY = "https://api.mymemory.translated.net/get"
_URL_GROQ = "https://api.groq.com/openai/v1/chat/completions"
_MODELO_GROQ = "openai/gpt-oss-120b"  # llama-3.3-70b-versatile foi descomissionado (ver GAIA, 2026-08-15)


def traducao_disponivel():
    provedor = config_mod.obter("traducao_provedor")
    if provedor == "llm":
        return bool(os.getenv("GROQ_API_KEY"))
    return provedor == "gratis"


def traduzir_linhas(linhas):
    """`linhas`: lista de `{"tempo_segundos", "texto"}` (mesmo formato de
    `lyrics.parsear_lrc`) - devolve a MESMA lista com uma chave `traducao`
    a mais em cada item (`None` quando essa linha específica falhou), ou
    `None` inteiro se nenhum provedor estiver configurado/disponível.
    Nunca inventa tradução quando o serviço falha."""
    provedor = config_mod.obter("traducao_provedor")
    idioma_alvo = config_mod.obter("traducao_idioma_alvo")
    if provedor == "llm":
        return _traduzir_via_llm(linhas, idioma_alvo)
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


def _traduzir_via_llm(linhas, idioma_alvo):
    """1 chamada só pra letra inteira (não 1 por linha, como o MyMemory) -
    um LLM entende contexto entre linhas, e evita pagar N chamadas por
    faixa. Numeração "N: texto" mantém o pareamento linha a linha mesmo se
    o modelo reordenar/juntar frases um pouco."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return None

    texto_numerado = "\n".join(f"{i}: {linha['texto']}" for i, linha in enumerate(linhas))
    prompt = (
        f"Traduza cada linha numerada abaixo para {idioma_alvo}, mantendo a mesma "
        f"numeração 'N: texto' e a mesma quantidade de linhas. Responda só com as "
        f"linhas traduzidas, sem nenhum comentário a mais.\n\n{texto_numerado}"
    )
    try:
        resp = requests.post(
            _URL_GROQ,
            headers={"Authorization": f"Bearer {api_key}"},
            json={"model": _MODELO_GROQ, "messages": [{"role": "user", "content": prompt}], "temperature": 0.2},
            timeout=TIMEOUT,
        )
        conteudo = resp.json()["choices"][0]["message"]["content"]
    except Exception:
        return None

    traducoes_por_indice = {}
    for linha_bruta in conteudo.splitlines():
        if ":" not in linha_bruta:
            continue
        indice_str, texto = linha_bruta.split(":", 1)
        try:
            indice = int(indice_str.strip())
        except ValueError:
            continue
        traducoes_por_indice[indice] = texto.strip()

    return [{**linha, "traducao": traducoes_por_indice.get(i)} for i, linha in enumerate(linhas)]
