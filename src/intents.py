"""Detecção de intenção das mensagens do usuário.

Decide se uma mensagem é um comando para o Spotify (e qual) ou se deve
ser tratada pelo chatbot de padrões (NLTK).
"""
import re

NAO_ARTISTAS = {
    "rock", "pop", "rap", "hip hop", "funk", "sertanejo", "mpb", "jazz",
    "blues", "reggae", "samba", "pagode", "eletronica", "eletrônica", "metal",
    "trap", "country", "gospel", "classica", "clássica", "indie", "musica",
    "música", "musicas", "músicas", "som", "banda", "artista", "cantor",
    "cantora", "você", "voce", "vc", "tu", "ele", "ela", "isso", "isto",
}


def detect(message: str) -> tuple[str | None, str | None]:
    """
    Retorna (intent, payload) se a mensagem for um comando Spotify.
    Retorna (None, None) caso contrário — o NLTK assume o controle.
    """
    msg = message.lower().strip()

    # Playlists: "playlist de rock", "playlists para relaxar", "playlist pra treinar"
    m = re.search(
        r"playlists?\s+(?:de\s+|para\s+|pra\s+|d[oa]\s+)?(.+)",
        msg,
    )
    if m:
        return "playlist", m.group(1).strip()

    # Buscar faixa: "buscar música X", "toca X", "ouvir X"
    m = re.search(
        r"(?:buscar?\s+(?:a\s+)?(?:música|musica|faixa|track|song)\s+|"
        r"toca[r]?\s+|ouvir\s+|escutar\s+)(.+)",
        msg,
    )
    if m:
        return "track", m.group(1).strip()

    # Buscar artista: "buscar artista X", "buscar banda X"
    m = re.search(
        r"buscar?\s+(?:o\s+)?(?:artista|banda|cantor[a]?)\s+(.+)",
        msg,
    )
    if m:
        return "artist", m.group(1).strip()

    # Pergunta natural sobre artista: "quem é X", "quem foi X", "fala/fale sobre X"
    m = re.search(
        r"(?:quem\s+(?:é|e|foi|são|sao)\s+(?:os?\s+|as?\s+)?|"
        r"(?:me\s+)?(?:fala|fale|conta|conte|diga)\s+(?:sobre|do|da|de)\s+)(.+)",
        msg,
    )
    if m:
        termo = m.group(1).strip(" ?!.")
        if termo and termo.lower() not in NAO_ARTISTAS:
            # Pergunta natural → resumo em texto (LLM) + foto, e não o card
            return "artist_info", termo

    # Discografia: "álbuns do X", "discografia de X", "discos do X"
    m = re.search(
        r"(?:[áa]lbuns|discografia|discos)\s+(?:d[oae]s?\s+|do\s+)?(.+)",
        msg,
    )
    if m:
        return "discography", m.group(1).strip()

    # Buscar álbum: "buscar álbum X", "álbum X", "buscar disco X"
    m = re.search(
        r"(?:buscar?\s+(?:o\s+)?(?:[áa]lbum|disco)\s+|[áa]lbum\s+)(.+)",
        msg,
    )
    if m:
        return "album", m.group(1).strip()

    # Recomendações baseadas num artista: "recomendações parecidas com X", "músicas similares a X"
    m = re.search(
        r"(?:recomenda[çc][oõ]es?\s+(?:parecidas?\s+com|baseadas?\s+em|do\s+estilo\s+de)\s+|"
        r"m[úu]sicas?\s+(?:parecidas?\s+com|similares?\s+a[o]?\s+))(.+)",
        msg,
    )
    if m:
        return "recommendations", m.group(1).strip()

    # Recomendação genérica (sem artista): "me recomende uma música", "indica um som", "sugira algo"
    if re.search(r"(recomend\w*|sugir\w*|sugere|indic\w*)", msg) and \
       re.search(r"(m[úu]sica|faixa|som|can[çc][ãa]o|track|algo|alguma|nova)", msg):
        return "recommendations", None

    return None, None
