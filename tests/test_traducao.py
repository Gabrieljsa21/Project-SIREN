# -*- coding: utf-8 -*-
from siren.core import config as config_mod
from siren.integrations import traducao as traducao_mod


def test_disponivel_false_por_padrao():
    assert traducao_mod.traducao_disponivel() is False


def test_disponivel_true_quando_gratis():
    config_mod.definir("traducao_provedor", "gratis")
    assert traducao_mod.traducao_disponivel() is True


def test_disponivel_llm_depende_de_chave_no_ambiente(monkeypatch):
    config_mod.definir("traducao_provedor", "llm")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    assert traducao_mod.traducao_disponivel() is False
    monkeypatch.setenv("GROQ_API_KEY", "chave-falsa")
    assert traducao_mod.traducao_disponivel() is True


def test_traduzir_linhas_none_quando_provedor_nenhum():
    linhas = [{"tempo_segundos": 1.0, "texto": "Hello"}]
    assert traducao_mod.traduzir_linhas(linhas) is None


def test_traduzir_via_mymemory(monkeypatch):
    config_mod.definir("traducao_provedor", "gratis")

    class _RespFalsa:
        def json(self):
            return {"responseData": {"translatedText": "Olá"}}
    monkeypatch.setattr(traducao_mod.requests, "get", lambda *a, **k: _RespFalsa())

    linhas = [{"tempo_segundos": 1.0, "texto": "Hello"}]
    resultado = traducao_mod.traduzir_linhas(linhas)
    assert resultado == [{"tempo_segundos": 1.0, "texto": "Hello", "traducao": "Olá"}]


def test_traduzir_via_mymemory_linha_com_falha_vira_none_sem_derrubar_as_outras(monkeypatch):
    config_mod.definir("traducao_provedor", "gratis")
    respostas = iter([Exception("falhou"), {"responseData": {"translatedText": "Mundo"}}])

    def _get_falso(*a, **k):
        proximo = next(respostas)
        if isinstance(proximo, Exception):
            raise proximo
        class _R:
            def json(self):
                return proximo
        return _R()
    monkeypatch.setattr(traducao_mod.requests, "get", _get_falso)

    linhas = [{"tempo_segundos": 1.0, "texto": "Hello"}, {"tempo_segundos": 2.0, "texto": "World"}]
    resultado = traducao_mod.traduzir_linhas(linhas)
    assert resultado[0]["traducao"] is None
    assert resultado[1]["traducao"] == "Mundo"


def test_traduzir_via_llm_sem_chave_devolve_none(monkeypatch):
    config_mod.definir("traducao_provedor", "llm")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    linhas = [{"tempo_segundos": 1.0, "texto": "Hello"}]
    assert traducao_mod.traduzir_linhas(linhas) is None


def test_traduzir_via_llm_parseia_linhas_numeradas(monkeypatch):
    config_mod.definir("traducao_provedor", "llm")
    monkeypatch.setenv("GROQ_API_KEY", "chave-falsa")

    class _RespFalsa:
        def json(self):
            return {"choices": [{"message": {"content": "0: Olá\n1: Mundo"}}]}
    monkeypatch.setattr(traducao_mod.requests, "post", lambda *a, **k: _RespFalsa())

    linhas = [{"tempo_segundos": 1.0, "texto": "Hello"}, {"tempo_segundos": 2.0, "texto": "World"}]
    resultado = traducao_mod.traduzir_linhas(linhas)
    assert resultado[0]["traducao"] == "Olá"
    assert resultado[1]["traducao"] == "Mundo"


def test_traduzir_via_llm_falha_de_rede_devolve_none(monkeypatch):
    config_mod.definir("traducao_provedor", "llm")
    monkeypatch.setenv("GROQ_API_KEY", "chave-falsa")

    def _levanta(*a, **k):
        raise ConnectionError("sem rede")
    monkeypatch.setattr(traducao_mod.requests, "post", _levanta)

    linhas = [{"tempo_segundos": 1.0, "texto": "Hello"}]
    assert traducao_mod.traduzir_linhas(linhas) is None
