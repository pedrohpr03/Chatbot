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

ATIVIDADES = {
    "treinar", "treino", "malhar", "academia", "correr", "corrida", "pedalar",
    "relaxar", "descansar", "dormir", "meditar", "estudar", "concentrar",
    "trabalhar", "trabalho", "foco", "festa", "balada", "dancar", "dançar",
    "churrasco", "viajar", "viagem", "dirigir", "cozinhar",
}


def _separa_musica_artista(texto: str) -> tuple[str, str | None]:
    """Separa 'música do/da artista' em (música, artista).

    Só tratamos ' do '/' da ' como separador de artista — e nunca ' de ', que
    aparece com frequência dentro do nome da música (ex.: 'Garota de Ipanema').
    Usa a ÚLTIMA ocorrência, então 'Garota de Ipanema do Tom Jobim' vira
    ('Garota de Ipanema', 'Tom Jobim'). Sem separador, o artista volta None.
    """
    m = re.search(r"^(.*\S)\s+d[oa]\s+(\S.*)$", texto)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return texto.strip(), None


def detect(message: str) -> tuple[str | None, object | None]:
    """
    Retorna (intent, payload) se a mensagem for um comando Spotify/Genius.
    Retorna (None, None) caso contrário — o NLTK assume o controle.

    O payload costuma ser uma string (o termo buscado); para o intent "lyrics"
    é a tupla (musica, artista_ou_None).
    """
    msg = message.lower().strip()

    # Letra de música (Genius): "letra de X", "qual a letra de X",
    # "letra da música X", "letra de X do/da <artista>".
    # Vem antes das demais porque "letra" é específico e não rouba outros intents.
    m = re.search(
        r"letra\s+(?:completa\s+)?(?:d[ao]\s+m[úu]sica\s+|de\s+|d[ao]\s+)?(.+)",
        msg,
    )
    if m:
        resto = m.group(1).strip(" ?!.")
        if resto:
            musica, artista = _separa_musica_artista(resto)
            if musica:
                return "lyrics", (musica, artista)

    # Playlists: "playlist de rock", "playlists para relaxar", "playlist pra treinar"
    m = re.search(
        r"playlists?\s+(?:de\s+|para\s+|pra\s+|d[oa]\s+)?(.+)",
        msg,
    )
    if m:
        return "playlist", m.group(1).strip()

    m = re.search(r"\b(?:para|pra)\s+(?:a\s+|o\s+)?([a-zà-ú]+)", msg)
    if m and m.group(1) in ATIVIDADES:
        return "playlist", m.group(1)

    # Buscar/tocar faixa: "buscar música X", "toca/toque/tocar X", "põe X",
    # "coloca X", "bota X", "ouvir X", "escutar X"
    m = re.search(
        r"(?:buscar?\s+(?:a\s+)?(?:música|musica|faixa|track|song)\s+|"
        r"(?:toca[r]?|toque)\s+|p[õo]e\s+|coloca[r]?\s+|bota[r]?\s+|"
        r"ouvir\s+|escutar\s+)(.+)",
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
        termo = m.group(1).strip()
        if not termo.startswith(("para ", "pra ")):
            return "discography", termo

    # Buscar álbum: "buscar álbum X", "álbum X", "buscar disco X"
    m = re.search(
        r"(?:buscar?\s+(?:o\s+)?(?:[áa]lbum|disco)\s+|[áa]lbum\s+)(.+)",
        msg,
    )
    if m:
        termo = m.group(1).strip()
        if not termo.startswith(("para ", "pra ")):
            return "album", termo

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
