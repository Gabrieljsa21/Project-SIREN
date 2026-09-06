# -*- coding: utf-8 -*-
"""Fila de reprodução do SIREN (PLANO_SIREN.md - "SIREN é dono de: fila
atual") - autoridade SEMPRE do SIREN, nunca do ECHO (ele só entra sugerindo
QUEM adicionar, através de `integrations/echo_client.py`).

Em memória, NÃO persistida entre reinícios de propósito - fila é estado de
SESSÃO (o que você tá tocando agora), diferente de playlist/favorito/
histórico, que são dado de longo prazo."""


class Fila:
    def __init__(self):
        self._itens = []  # cada item: {"titulo", "artista", "origem"}

    def adicionar(self, titulo, artista, origem="fila"):
        self._itens.append({"titulo": titulo, "artista": artista, "origem": origem})

    def adicionar_a_seguir(self, titulo, artista, origem="fila"):
        """Insere no topo (próxima a tocar) - "tocar a seguir" é uma ação
        diferente de "adicionar ao final da fila"."""
        self._itens.insert(0, {"titulo": titulo, "artista": artista, "origem": origem})

    def remover(self, indice):
        if 0 <= indice < len(self._itens):
            return self._itens.pop(indice)
        return None

    def mover(self, indice, delta):
        """`delta`: -1 sobe, +1 desce - usado pelas setinhas de reordenar da
        tela de Fila. Sem efeito se o movimento sair dos limites."""
        novo_indice = indice + delta
        if 0 <= indice < len(self._itens) and 0 <= novo_indice < len(self._itens):
            self._itens[indice], self._itens[novo_indice] = self._itens[novo_indice], self._itens[indice]

    def proxima(self):
        """Remove e devolve o PRIMEIRO item - `None` se a fila estiver
        vazia (quem chama decide o fallback, ex.: pedir mais uma sugestão
        ao ECHO)."""
        if not self._itens:
            return None
        return self._itens.pop(0)

    def limpar(self):
        self._itens = []

    def listar(self):
        return list(self._itens)

    def __len__(self):
        return len(self._itens)
