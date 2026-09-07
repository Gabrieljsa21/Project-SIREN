# TODO - Project SIREN

## Prioridade média

- **Biblioteca real** (view "library" hoje é só placeholder) - artistas/
  álbuns a partir de `historico_local.obter_artistas_mais_tocados` +
  favoritos + playlists, não um scanner de arquivo (SIREN não tem arquivo
  de música além do que já foi baixado). Complexidade: média. Status: não
  iniciado.
- **Busca própria** (view "search" hoje é só placeholder) - `yt_dlp` direto
  (`ytsearch5:`), sem precisar do ECHO (v1.3 do roadmap). Complexidade:
  baixa. Status: não iniciado.
- **Seek na barra de player** - clicar na barra de progresso pra pular
  pra um ponto da faixa (v1.1 do roadmap). Complexidade: baixa. Status:
  não iniciado.
- **Botão "Traduzir" trava a janela enquanto espera a API** - decisão
  consciente por enquanto (tradução é rara, sob demanda); mover pra uma
  thread própria (`QThread`/`QRunnable`) se isso incomodar na prática.
  Complexidade: baixa. Status: não iniciado.

## Prioridade baixa

- **Mini-player + atalhos multimídia do Windows** (v1.2 do roadmap,
  SMTC/`Qt.Key_MediaPlay` etc.) - Complexidade: média. Status: não iniciado.
- **Resolver avançado + múltiplas fontes + cache/fallback** (v2 do roadmap)
  - só faz sentido depois que o resto estiver estável. Status: não
  iniciado.
- **Importar do YouTube não bloqueia clique duplo** - clicar em "Importar do
  YouTube" de novo enquanto uma importação já está rodando dispara uma
  segunda `ImportYoutubeWorker` sobreposta (o botão não fica desabilitado
  durante a espera, diferente do botão de baixar). Complexidade: baixa.
  Status: não iniciado.
- **Confirmar auto-avanço do Caos com faixa real até o fim** (2026-09-06) -
  `Player.observar_fim_de_faixa` foi verificado só até o registro da API
  (sem erro, contra o código-fonte real do python-mpv) - nunca vi uma
  faixa tocar até o fim de verdade e confirmar que a próxima começa
  sozinha. Status: aguardando confirmação do usuário.
- **Duplo clique pra maximizar pode ter ficado instável com
  `startSystemMove()`** (2026-09-06) - trocar o arrasto manual pelo
  arrasto nativo pode interferir na detecção de duplo clique do Qt, já
  que o SO agora entra num loop de mover a cada 1º clique da barra de
  título. Não confirmado se ainda funciona. Status: aguardando
  confirmação do usuário.
- **Clique-através em espaço genuinamente vazio do Modo Completo**
  (2026-09-06) - barra de título/sidebar/barra de player já foram
  corrigidas (`Qt.WA_StyledBackground` por widget, ver `chrome.py` e
  `full/main_window.py`), mas área vazia de dentro das views (ex.: fundo
  em branco da tela "Busca") ainda pode deixar o clique passar direto pra
  janela de trás - tentativa de resolver isso de forma genérica (pintando
  a janela de topo inteira) tornou a área de conteúdo preta sólida
  (revertido, "essas cores ficaram horríveis"). Resolver direito precisa
  de outra técnica (interceptar `WM_NCHITTEST` nativo, não CSS/alpha).
  Complexidade: média. Status: não iniciado.
