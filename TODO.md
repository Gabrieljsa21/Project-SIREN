# TODO - Project SIREN

## Prioridade alta

- **Letras sincronizadas sem UI nenhuma** - `integrations/lyrics.py` funciona
  e foi validado contra a API real do LRCLIB, mas nenhuma tela mostra letra
  nenhuma. Falta: painel na view "Tocando agora" (ou aba própria) chamando
  `lyrics.buscar_letra` quando a faixa muda, e um timer lendo
  `player.posicao_segundos` pra destacar a linha atual. Complexidade: média.
  Status: não iniciado.
- **Download offline sem UI nenhuma** - `core/downloads.py` funciona
  (manifesto testado, prioridade sobre resolver pela rede já integrada em
  `orquestrador.py`), mas nenhum botão em nenhuma tela chama
  `downloads.baixar()`. Falta: botão "baixar" em Playlists/Favoritos/
  Histórico, rodando em thread própria (download é bloqueante e faz chamada
  de rede - não pode travar a janela). Complexidade: baixa (função já existe,
  só falta UI + threading). Status: não iniciado.
- **Decisão de produto: tradução de letras** - LRCLIB não traduz. Toda opção
  disponível (API paga, ou um LLM) quebra "SIREN funciona sozinho" (chave/
  custo/login). Precisa decidir COM o usuário qual serviço usar antes de
  implementar - ver PLANO_SIREN.md, seção 15.

## Prioridade média

- **Biblioteca real** (view "library" hoje é só placeholder) - artistas/
  álbuns a partir de `historico_local.obter_artistas_mais_tocados` +
  favoritos + playlists, não um scanner de arquivo (SIREN não tem arquivo
  de música além do que já foi baixado). Complexidade: média. Status: não
  iniciado.
- **Busca própria** (view "search" hoje é só placeholder) - `yt_dlp` direto
  (`ytsearch5:`), sem precisar do ECHO (v1.3 do roadmap). Complexidade:
  baixa. Status: não iniciado.
- **"Adicionar à fila"/"tocar a seguir" nas views** - hoje clicar numa
  faixa (Playlists/Favoritos/Histórico/Descoberta) toca IMEDIATO, nunca
  enfileira. Falta um menu de contexto ou botão "+" chamando
  `core/fila.Fila.adicionar`/`adicionar_a_seguir`. Complexidade: baixa.
  Status: não iniciado.
- **Playlist "Descobertas do SIREN" automática** - `playlists.
  adicionar_a_descobertas` já existe, mas nenhuma view chama isso quando
  uma faixa de origem "descoberta"/"caos" recebe ❤️ (só a view Descoberta
  sabe a origem no momento do voto). Complexidade: baixa. Status: não
  iniciado.
- **Seek na barra de player** - clicar na barra de progresso pra pular
  pra um ponto da faixa (v1.1 do roadmap). Complexidade: baixa. Status:
  não iniciado.

## Prioridade baixa

- **Mini-player + atalhos multimídia do Windows** (v1.2 do roadmap,
  SMTC/`Qt.Key_MediaPlay` etc.) - Complexidade: média. Status: não iniciado.
- **Resolver avançado + múltiplas fontes + cache/fallback** (v2 do roadmap)
  - só faz sentido depois que o resto estiver estável. Status: não
  iniciado.
- **Testar de verdade com display real** - tudo aqui foi validado só
  offscreen (`QT_QPA_PLATFORM=offscreen`) e por instanciação direta; o
  Modo Completo (vidro fosco de verdade, Acrylic) nunca foi CONFIRMADO
  visualmente por ninguém ainda. Abri as duas janelas (Leve e Completo)
  rodando de verdade nesta máquina em 2026-09-06 - conferir se o Acrylic
  aplicou mesmo (Windows 10/11 recente) e se a barra de título própria
  (arrastar/minimizar/fechar/duplo clique) funciona como esperado.
