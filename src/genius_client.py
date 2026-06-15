"""Cliente da API do Genius (camada de dados — letras de música).

Busca a letra de uma música no Genius usando a biblioteca `lyricsgenius`
(busca pela API oficial + extração da letra da página). Não contém HTML nem
lógica de conversa, apenas a consulta. Quando o artista não é informado,
reaproveita o Spotify (a "base") para descobrir o intérprete mais provável e
melhorar a precisão da busca.

Segue o mesmo contrato dos demais clientes: retorna `dict` em caso de sucesso
e `None` em qualquer falha (sem token, rede, música não encontrada, etc.).
"""
import os
import re
import logging

from dotenv import load_dotenv

from src import spotify_client as spotify

load_dotenv()

logger = logging.getLogger(__name__)

TIMEOUT = 10  # segundos por requisição

_genius       = None
_init_tentada = False


def _get_client():
    """Cria (uma única vez) o cliente do Genius. None se não der."""
    global _genius, _init_tentada
    if _init_tentada:
        return _genius
    _init_tentada = True

    token = os.getenv("GENIUS_ACCESS_TOKEN")
    if not token:
        logger.warning("GENIUS_ACCESS_TOKEN não configurado no .env — letras desativadas.")
        return None

    try:
        from lyricsgenius import Genius
        _genius = Genius(
            token,
            timeout=TIMEOUT,
            retries=2,
            remove_section_headers=True,   # remove marcações [Verse], [Chorus] etc.
        )
    except Exception:
        logger.exception("Falha ao inicializar o cliente do Genius.")
        _genius = None

    return _genius


def _limpa_letra(texto: str) -> str:
    """Remove os ruídos que o Genius adiciona à letra extraída.

    O `lyricsgenius` costuma trazer um cabeçalho ('<música> Lyrics', contagem
    de contribuidores) e um sufixo final ('Embed' / número + 'Embed'). Tiramos
    isso para exibir apenas a letra.
    """
    texto = texto.strip()
    # Sufixo "...Embed" / "123Embed" no fim
    texto = re.sub(r"\d*Embed\s*$", "", texto)
    linhas = texto.split("\n")
    # A 1ª linha costuma ser o cabeçalho "<algo> Lyrics", não parte da letra
    if linhas and linhas[0].strip().endswith("Lyrics"):
        linhas = linhas[1:]
    return "\n".join(linhas).strip()


def get_lyrics(artist: str | None, song: str) -> dict | None:
    """Busca a letra de uma música no Genius.

    `artist` é opcional: quando não vem na pergunta, usamos o Spotify para
    descobrir o intérprete mais provável da `song` (melhora muito a precisão e
    reaproveita a "base").

    Sucesso → {"artist", "song", "text", "url"}. Retorna None se não houver
    token configurado, em falha de rede ou se a letra não for encontrada.
    """
    song = (song or "").strip()
    if not song:
        return None

    client = _get_client()
    if client is None:
        return None

    artist = (artist or "").strip()
    if not artist:
        # Sem artista na pergunta: pergunta ao Spotify quem é o intérprete mais
        # provável dessa música, reaproveitando a "base" de dados.
        tracks = spotify.search_track(song)
        if tracks:
            artist = tracks[0]["artist"]

    try:
        if artist:
            resultado = client.search_song(song, artist)
        else:
            resultado = client.search_song(song)
    except Exception:
        # Cobre rede, timeout, erro/cota da API, etc.
        logger.exception("Erro ao consultar o Genius.")
        return None

    if resultado is None or not getattr(resultado, "lyrics", None):
        return None

    return {
        "artist": resultado.artist or artist or "",
        "song":   resultado.title or song,
        "text":   _limpa_letra(resultado.lyrics),
        "url":    resultado.url or "",
    }
