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
- **Testar de verdade com display real** - tudo aqui foi validado só
  offscreen (`QT_QPA_PLATFORM=offscreen`) e por instanciação direta; o
  Modo Completo (vidro fosco de verdade, Acrylic) nunca foi CONFIRMADO
  visualmente por ninguém ainda. Abri as duas janelas (Leve e Completo)
  rodando de verdade nesta máquina em 2026-09-06 - conferir se o Acrylic
  aplicou mesmo (Windows 10/11 recente) e se a barra de título própria
  (arrastar/minimizar/fechar/duplo clique) funciona como esperado.
