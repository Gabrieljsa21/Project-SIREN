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
- **Confirmar clique em espaço vazio das views não passa mais através**
  (2026-09-06) - causa raiz real das 2 tentativas anteriores falharem:
  `rgba()` no QSS usa alpha como FRAÇÃO 0.0-1.0, não inteiro 0-255 -
  `rgba(0, 0, 0, 1)` = opacidade TOTAL, não "1 de 255" (mesmo erro que o
  Project-ARGUS já tinha documentado). Corrigido pra `rgba(0, 0, 0,
  0.004)` (≈1/255 de verdade) + `Qt.WA_StyledBackground` na janela de
  topo inteira (`chrome.py::configurar_janela_vidro_fosco`) - cobre
  qualquer espaço vazio sem escurecer o vidro fosco. Status: aguardando
  confirmação do usuário.
