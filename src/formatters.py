"""Formatação das respostas do Spotify em HTML.

Cada função recebe os dados já buscados pelo spotify_client e devolve
a string HTML que será exibida no balão do chat.

Todo valor dinâmico (nomes, busca do usuário, URLs) passa por `_e()` para
evitar injeção de HTML/JS (XSS), já que o frontend usa innerHTML.
"""
import html

# Quantas linhas da letra são exibidas no chat. Mostramos só um trecho por se
# tratar de conteúdo protegido por direitos autorais — a letra completa fica no
# link para o Genius. Para um projeto acadêmico, basta aumentar este valor.
MAX_LINHAS_LETRA = 8


def _e(value) -> str:
    """Escapa um valor para inserção segura no HTML."""
    return html.escape(str(value))


def _imagem(url: str | None, largura: int = 200) -> str:
    """Gera a tag <img> de uma capa/foto, ou string vazia se não houver."""
    if not url:
        return ""
    return (
        f"<img src='{_e(url)}' "
        f"style='width:{largura}px;border-radius:10px;margin-bottom:10px;'><br>"
    )


def track(t: dict) -> str:
    """Exibe uma única faixa — usado no comando 'toque/toca X'."""
    return (
        f"<b>{_e(t['name'])}</b> — {_e(t['artist'])}<br>"
        f"{_e(t['album'])}"
        f" &nbsp;<a href='{_e(t['url'])}' target='_blank'>▶ Ouvir</a>"
    )


def tracks(items: list[dict], query: str) -> str:
    if not items:
        return f"Não encontrei nada para <b>{_e(query)}</b>. Tente outro nome!"

    linhas = [f"Resultados para <b>{_e(query)}</b>:<br>"]
    for i, t in enumerate(items, 1):
        linhas.append(
            f"{i}. <b>{_e(t['name'])}</b> — {_e(t['artist'])}<br>"
            f"&nbsp;&nbsp;&nbsp; {_e(t['album'])}"
            f" &nbsp;<a href='{_e(t['url'])}' target='_blank'>▶ Ouvir</a>"
        )
    return "<br>".join(linhas)


def artist(info: dict, resumo: str | None = None) -> str:
    if not info:
        return "Artista não encontrado."

    # `resumo` (texto curto da LLM) é opcional: a base do Spotify não guarda
    # biografia, então quando há um, ele apresenta o artista acima do conteúdo.
    bloco_resumo = ""
    if resumo:
        texto = _e(resumo).replace("\n", "<br>")
        bloco_resumo = f"<br>{texto}<br>"

    partes = [
        _imagem(info.get("image")) +
        f"<b>{_e(info['name'])}</b><br>"
        f"{bloco_resumo}"
        f"<a href='{_e(info['url'])}' target='_blank'> Ver perfil</a>"
    ]

    if info.get("tracks"):
        linhas = ["<br><br> <b>Músicas conhecidas:</b>"]
        for t in info["tracks"]:
            linhas.append(f"• <a href='{_e(t['url'])}' target='_blank'>{_e(t['name'])}</a>")
        partes.append("<br>".join(linhas))

    if info.get("albums"):
        linhas = ["<br> <b>Álbuns recentes:</b>"]
        for a in info["albums"]:
            ano = f" ({_e(a['year'])})" if a.get("year") else ""
            linhas.append(f"• <a href='{_e(a['url'])}' target='_blank'>{_e(a['name'])}</a>{ano}")
        partes.append("<br>".join(linhas))

    return "".join(partes)


def artist_summary(nome: str, resumo: str, image_url: str | None = None) -> str:
    """Resumo em texto do artista (gerado pelo LLM) + foto do perfil, se houver."""
    texto = _e(resumo).replace("\n", "<br>")
    return (
        _imagem(image_url) +
        f"<b>{_e(nome)}</b><br><br>"
        f"{texto}"
    )


def album(info: dict) -> str:
    if not info:
        return "Álbum não encontrado. Tente outro nome!"

    ano = f" ({_e(info['year'])})" if info.get("year") else ""
    cabecalho = (
        _imagem(info.get("image")) +
        f" <b>{_e(info['name'])}</b> — {_e(info['artist'])}{ano}<br>"
        f"<a href='{_e(info['url'])}' target='_blank'> Abrir álbum</a><br>"
    )

    linhas = [
        f"{t['number']}. <a href='{_e(t['url'])}' target='_blank'>{_e(t['name'])}</a>"
        for t in info["tracks"]
    ]
    return cabecalho + "<br>".join(linhas)


def discography(info: dict) -> str:
    if not info or not info.get("albums"):
        return "Não encontrei a discografia desse artista."

    linhas = [f" Álbuns de <b>{_e(info['artist'])}</b>:<br>"]
    for a in info["albums"]:
        ano = f" ({_e(a['year'])})" if a.get("year") else ""
        linhas.append(f"• <a href='{_e(a['url'])}' target='_blank'>{_e(a['name'])}</a>{ano}")
    return "<br>".join(linhas)


def playlists(items: list[dict], query: str) -> str:
    if not items:
        return f"Não encontrei playlists para <b>{_e(query)}</b>. Tente outro tema!"

    linhas = [f" Playlists para <b>{_e(query)}</b>:<br>"]
    for p in items:
        thumb = ""
        if p.get("image"):
            thumb = (
                f"<img src='{_e(p['image'])}' "
                f"style='width:45px;height:45px;border-radius:6px;"
                f"vertical-align:middle;margin-right:8px;'>"
            )
        dono = f" <small>por {_e(p['owner'])}</small>" if p.get("owner") else ""
        linhas.append(f"{thumb}<a href='{_e(p['url'])}' target='_blank'>{_e(p['name'])}</a>{dono}")
    return "<br>".join(linhas)


def lyrics(info: dict) -> str:
    """Exibe um TRECHO da letra (Genius) + link para a letra completa.

    Mostramos apenas as primeiras `MAX_LINHAS_LETRA` linhas: letra é conteúdo
    protegido, então o padrão seguro é trecho + link para a página do Genius.
    """
    if not info:
        return "Não encontrei a letra dessa música."

    linhas = info["text"].strip().split("\n")
    trecho = "<br>".join(_e(linha) for linha in linhas[:MAX_LINHAS_LETRA])

    link = ""
    if info.get("url"):
        reticencias = "… " if len(linhas) > MAX_LINHAS_LETRA else ""
        link = (
            f"<br>{reticencias}<a href='{_e(info['url'])}' target='_blank'>"
            f"ver letra completa no Genius</a>"
        )

    return (
        f"🎵 <b>{_e(info['song'])}</b> — {_e(info['artist'])}<br><br>"
        f"{trecho}{link}"
    )


def recommendations(items: list[dict], seed: str) -> str:
    if not items:
        return f"Não consegui gerar recomendações baseadas em <b>{_e(seed)}</b>."

    linhas = [f"Recomendações baseadas em <b>{_e(seed)}</b>:<br>"]
    for t in items:
        linhas.append(
            f"• <b>{_e(t['name'])}</b> — {_e(t['artist'])}"
            f" <a href='{_e(t['url'])}' target='_blank'>▶</a>"
        )
    return "<br>".join(linhas)
