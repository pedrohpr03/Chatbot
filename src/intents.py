"""Detecção de intenção das mensagens do usuário.

Decide se uma mensagem é um comando para o Spotify/Genius (e qual) ou se deve
ser tratada pelo chatbot de padrões (NLTK). Entende português e inglês.
"""
import re

NAO_ARTISTAS = {
    "rock", "pop", "rap", "hip hop", "funk", "sertanejo", "mpb", "jazz",
    "blues", "reggae", "samba", "pagode", "eletronica", "eletrônica", "metal",
    "trap", "country", "gospel", "classica", "clássica", "indie", "musica",
    "música", "musicas", "músicas", "som", "banda", "artista", "cantor",
    "cantora", "você", "voce", "vc", "tu", "ele", "ela", "isso", "isto",
    # inglês
    "music", "song", "songs", "band", "artist", "singer", "you", "it",
    "this", "that", "he", "she", "they", "them", "someone", "anyone",
}

ATIVIDADES = {
    "treinar", "treino", "malhar", "academia", "correr", "corrida", "pedalar",
    "relaxar", "descansar", "dormir", "meditar", "estudar", "concentrar",
    "trabalhar", "trabalho", "foco", "festa", "balada", "dancar", "dançar",
    "churrasco", "viajar", "viagem", "dirigir", "cozinhar",
    # inglês
    "workout", "gym", "running", "run", "study", "studying", "sleep",
    "sleeping", "relax", "relaxing", "party", "work", "focus", "driving",
    "drive", "cooking", "cook", "training", "meditate", "dancing", "dance",
    "chill", "chilling", "reading", "gaming",
}

# Pedido de tradução da letra (sempre para português).
_RE_TRADUZIR = r"\b(?:traduz\w*|tradu[çc][ãa]o|translate[d]?|translation)\b"
_RE_EM_PORTUGUES = r"\b(?:em|in|para|to)\s+(?:o\s+|the\s+)?portugu[eê]s\b"


def _quer_traducao(msg: str) -> bool:
    """True se o usuário pediu a letra traduzida (ex.: 'traduza a letra de X',
    'letra de X em português', 'translate the lyrics of X')."""
    return bool(re.search(_RE_TRADUZIR, msg) or re.search(_RE_EM_PORTUGUES, msg))


def _remove_termos_traducao(msg: str) -> str:
    """Remove os termos de tradução para não poluir o nome da música.

    Ex.: 'traduza a letra de X em português' → 'a letra de X' antes de
    extrair música/artista.
    """
    msg = re.sub(_RE_TRADUZIR, " ", msg)
    msg = re.sub(_RE_EM_PORTUGUES, " ", msg)
    return re.sub(r"\s+", " ", msg).strip()


def _separa_musica_artista(texto: str) -> tuple[str, str | None]:
    """Separa 'música do/da/by artista' em (música, artista).

    Só tratamos ' do '/' da ' (pt) e ' by ' (en) como separador — nunca ' de ',
    que aparece com frequência dentro do nome da música (ex.: 'Garota de
    Ipanema'). Usa a ÚLTIMA ocorrência, então 'Garota de Ipanema do Tom Jobim'
    vira ('Garota de Ipanema', 'Tom Jobim'). Sem separador, o artista volta None.
    """
    m = re.search(r"^(.*\S)\s+(?:d[oa]|by)\s+(\S.*)$", texto)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return texto.strip(), None


def detect(message: str) -> tuple[str | None, object | None]:
    """
    Retorna (intent, payload) se a mensagem for um comando Spotify/Genius.
    Retorna (None, None) caso contrário — o NLTK assume o controle.

    O payload costuma ser uma string (o termo buscado); para o intent "lyrics"
    é a tupla (musica, artista_ou_None, traduzir) — traduzir=True quando o
    usuário pede a letra traduzida (para português).
    """
    msg = message.lower().strip()

   
    
    traduzir = _quer_traducao(msg)
    msg_letra = _remove_termos_traducao(msg) if traduzir else msg
    m = re.search(
        r"(?:letra\s+(?:completa\s+)?(?:d[ao]\s+m[úu]sica\s+|de\s+|d[ao]\s+)?"
        r"|lyrics?\s+(?:to\s+|of\s+|for\s+)?)(.+)",
        msg_letra,
    )
    if not m:
        # Inglês com "lyrics" no fim: "Sicko Mode lyrics"
        m = re.search(r"(.+?)\s+lyrics?\b", msg_letra)
    if m:
        resto = m.group(1).strip(" ?!.")
        if resto:
            musica, artista = _separa_musica_artista(resto)
            if musica:
                return "lyrics", (musica, artista, traduzir)

    
    m = re.search(
        r"playlists?\s+(?:de\s+|para\s+|pra\s+|d[oa]\s+|of\s+|for\s+|to\s+)?(.+)",
        msg,
    )
    if m:
        return "playlist", m.group(1).strip()

    #
    m = re.search(r"\b(?:para|pra|for|to)\s+(?:a\s+|o\s+|the\s+)?([a-zà-ú]+)", msg)
    if m and m.group(1) in ATIVIDADES:
        return "playlist", m.group(1)

    
    m = re.search(
        r"(?:buscar?\s+(?:a\s+)?(?:música|musica|faixa|track|song)\s+|"
        r"search\s+(?:for\s+)?(?:song|track|music)\s+|"
        r"(?:toca[r]?|toque)\s+|p[õo]e\s+|coloca[r]?\s+|bota[r]?\s+|"
        r"ouvir\s+|escutar\s+|play\s+|listen\s+to\s+)(.+)",
        msg,
    )
    if m:
        return "track", m.group(1).strip()

    
    m = re.search(
        r"(?:buscar?\s+(?:o\s+)?(?:artista|banda|cantor[a]?)\s+|"
        r"search\s+(?:for\s+)?(?:the\s+)?(?:artist|band|singer)\s+)(.+)",
        msg,
    )
    if m:
        return "artist", m.group(1).strip()

    
    m = re.search(
        r"(?:quem\s+(?:é|e|foi|são|sao)\s+(?:os?\s+|as?\s+)?|"
        r"who\s+(?:is|was|are|were)\s+(?:the\s+)?|"
        r"(?:me\s+)?(?:fala|fale|conta|conte|diga)\s+(?:sobre|do|da|de)\s+|"
        r"tell\s+me\s+about\s+|tell\s+about\s+|talk\s+about\s+)(.+)",
        msg,
    )
    if m:
        termo = m.group(1).strip(" ?!.")
        if termo and termo.lower() not in NAO_ARTISTAS:
            
            return "artist_info", termo

    
    m = re.search(
        r"(?:[áa]lbuns|discografia|discos|albums|discography)\s+"
        r"(?:d[oae]s?\s+|do\s+|of\s+|by\s+)?(.+)",
        msg,
    )
    if not m:
        m = re.search(r"(.+?)(?:'s)?\s+(?:[áa]lbuns|albums|discography)\b", msg)
    if m:
        termo = m.group(1).strip()
        if not termo.startswith(("para ", "pra ", "for ", "to ")):
            return "discography", termo

    
    m = re.search(
        r"(?:buscar?\s+(?:o\s+)?(?:[áa]lbum|disco)\s+|"
        r"search\s+(?:for\s+)?(?:the\s+)?album\s+|[áa]lbum\s+)(.+)",
        msg,
    )
    if m:
        termo = m.group(1).strip()
        if not termo.startswith(("para ", "pra ", "for ", "to ")):
            return "album", termo

    
    m = re.search(
        r"(?:recomenda[çc][oõ]es?\s+(?:parecidas?\s+com|baseadas?\s+em|do\s+estilo\s+de)\s+|"
        r"m[úu]sicas?\s+(?:parecidas?\s+com|similares?\s+a[o]?\s+)|"
        r"recommendations?\s+(?:like|similar\s+to|based\s+on)\s+|"
        r"songs?\s+(?:like|similar\s+to)\s+|"
        r"music\s+(?:like|similar\s+to)\s+)(.+)",
        msg,
    )
    if m:
        return "recommendations", m.group(1).strip()

    
    if re.search(r"(recomend\w*|sugir\w*|sugere|indic\w*|recommend\w*|suggest\w*)", msg) and \
       re.search(r"(m[úu]sica|faixa|som|can[çc][ãa]o|track|algo|alguma|nova|"
                 r"song|songs|music|something|anything)", msg):
        return "recommendations", None

    return None, None
