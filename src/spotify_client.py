"""Cliente da API do Spotify (camada de dados).

Autenticação via Client Credentials e funções de busca/consulta.
Não contém HTML nem lógica de conversa — apenas chamadas à API.
"""
import os
import re
import time
import base64
import logging
import unicodedata

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ─ Configuração
API_BASE  = "https://api.spotify.com/v1"
TOKEN_URL = "https://accounts.spotify.com/api/token"
MARKET    = "BR"
TIMEOUT   = 10          # segundos por requisição
PAGE_SIZE = 10          # apps novos têm cota reduzida (limit máx. ~10)

# Usados quando o usuário pede recomendação sem citar um artista
SEED_ARTISTS = [
    "Queen", "Michael Jackson", "Eminem", "Imagine Dragons", "Nirvana",
    "The Beatles", "Coldplay", "Bruno Mars", "The Weeknd", "Racionais MC's",
    "Foo Fighters", "Beyoncé", "Linkin Park", "Adele", "Red Hot Chili Peppers",
]

# ─ Autenticação 
_token = None
_token_expira_em = 0.0  # timestamp (epoch) de expiração do token


def _get_token() -> str | None:
    """Gera (ou reutiliza) o access token via Client Credentials.

    O token é cacheado em memória e renovado automaticamente quando expira.
    """
    global _token, _token_expira_em
    if _token and time.time() < _token_expira_em:
        return _token

    client_id     = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    if not client_id or not client_secret:
        logger.warning("SPOTIFY_CLIENT_ID/SECRET não configurados no .env")
        return None

    creds = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    try:
        resp = requests.post(
            TOKEN_URL,
            headers={
                "Authorization": f"Basic {creds}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={"grant_type": "client_credentials"},
            timeout=TIMEOUT,
        )
    except requests.RequestException as e:
        logger.warning("Falha de rede ao obter token: %s", e)
        return None

    if resp.status_code != 200:
        logger.warning("Falha ao obter token (%s): %s", resp.status_code, resp.text[:200])
        return None

    data = resp.json()
    _token = data["access_token"]
    # renova 60s antes do prazo, por segurança
    _token_expira_em = time.time() + data.get("expires_in", 3600) - 60
    return _token


def _api_get(path: str, params: dict | None = None, _retry: bool = True) -> dict | None:
    """GET autenticado na API do Spotify. Retorna o JSON ou None em caso de erro."""
    token = _get_token()
    if not token:
        return None

    try:
        resp = requests.get(
            f"{API_BASE}{path}",
            headers={"Authorization": f"Bearer {token}"},
            params=params,
            timeout=TIMEOUT,
        )
    except requests.RequestException as e:
        logger.warning("Falha de rede em %s: %s", path, e)
        return None

    # Token pode ter expirado no meio do uso → renova e tenta uma vez
    if resp.status_code == 401 and _retry:
        global _token
        _token = None
        return _api_get(path, params, _retry=False)

    if resp.status_code != 200:
        logger.warning("Spotify %s em %s: %s", resp.status_code, path, resp.text[:200])
        return None

    return resp.json()


# ─ Comparação de nomes
def _normaliza_nome(texto: str) -> str:
    """Reduz um nome a minúsculas, sem acentos e só alfanumérico (para comparar)."""
    nfkd = unicodedata.normalize("NFKD", texto.lower())
    sem_acento = "".join(c for c in nfkd if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "", sem_acento)


def nome_corresponde(nome_spotify: str, consulta: str) -> bool:
    """True se o artista devolvido pelo Spotify realmente corresponde à consulta.

    A busca do Spotify é "fuzzy" e devolve algum artista para quase qualquer
    texto (ex.: 'vinicius junior' → 'Rafinha RSQ'). Comparando os nomes
    normalizados evitamos exibir um perfil que não tem nada a ver com o pedido.
    """
    a = _normaliza_nome(nome_spotify)
    b = _normaliza_nome(consulta)
    if not a or not b:
        return False
    if a == b:
        return True
    # tolera variações como "banda queen" ⊃ "queen"
    return len(a) >= 3 and len(b) >= 3 and (a in b or b in a)


# ─ Buscas
def search_track(query: str) -> list[dict] | None:
    """Busca até 3 faixas no Spotify pelo nome."""
    data = _api_get("/search", {"q": query, "type": "track", "limit": 3, "market": MARKET})
    if not data:
        return None

    items = data.get("tracks", {}).get("items", [])
    if not items:
        return None

    return [
        {
            "name":   t["name"],
            "artist": t["artists"][0]["name"],
            "album":  t["album"]["name"],
            "url":    t["external_urls"]["spotify"],
        }
        for t in items
    ]


def search_artist(query: str) -> dict | None:
    """Busca um artista pelo nome e retorna seus dados básicos.

    O Spotify às vezes ranqueia outro artista no topo (ex.: 'anitta' devolvia
    'Luísa Sonza' como 1º resultado), então pedimos vários candidatos e
    preferimos aquele cujo nome realmente corresponde à busca.
    """
    data = _api_get("/search", {"q": query, "type": "artist", "limit": PAGE_SIZE, "market": MARKET})
    if not data:
        return None

    items = data.get("artists", {}).get("items", [])
    if not items:
        return None

    artist = next((a for a in items if nome_corresponde(a["name"], query)), items[0])
    return {
        "id":    artist["id"],
        "name":  artist["name"],
        "url":   artist["external_urls"]["spotify"],
        "image": artist["images"][0]["url"] if artist.get("images") else None,
    }


def search_album(query: str) -> dict | None:
    """Busca um álbum pelo nome e retorna seus dados + a lista de faixas."""
    # 1) Encontra o álbum pela busca
    data = _api_get("/search", {"q": query, "type": "album", "limit": 1, "market": MARKET})
    if not data:
        return None

    items = data.get("albums", {}).get("items", [])
    if not items:
        return None

    alb = items[0]

    # 2) Busca o álbum completo, que traz a lista de faixas
    full = _api_get(f"/albums/{alb['id']}", {"market": MARKET})
    if not full:
        return None

    faixas = [
        {
            "number": t["track_number"],
            "name":   t["name"],
            "url":    t["external_urls"]["spotify"],
        }
        for t in full.get("tracks", {}).get("items", [])
    ]

    return {
        "name":   alb["name"],
        "artist": alb["artists"][0]["name"],
        "year":   (alb.get("release_date") or "")[:4],
        "image":  alb["images"][0]["url"] if alb.get("images") else None,
        "url":    alb["external_urls"]["spotify"],
        "tracks": faixas,
    }


def get_discography(artist_name: str, max_albums: int = 12) -> dict | None:
    """Lista os álbuns de um artista, sem duplicatas de reedição.

    A cota do app limita 'limit' a ~10 por página, então paginamos com
    'offset' e depois agrupamos as versões (remaster/deluxe/etc.) pelo
    nome-base, mantendo o ano mais antigo de cada álbum.
    """
    artist = search_artist(artist_name)
    if not artist:
        return None

    brutos = []
    for offset in range(0, 50, PAGE_SIZE):
        data = _api_get(
            f"/artists/{artist['id']}/albums",
            {"market": MARKET, "include_groups": "album", "limit": PAGE_SIZE, "offset": offset},
        )
        if not data:
            break
        pagina = data.get("items", [])
        brutos.extend(pagina)
        if len(pagina) < PAGE_SIZE:        # última página
            break

    if not brutos:
        return None

    # Agrupa versões do mesmo álbum pelo nome-base (parte antes de "(", "[" ou "-")
    melhores: dict[str, dict] = {}
    for a in brutos:
        nome = re.split(r"[\(\[\-]", a["name"])[0].strip()
        nome = re.sub(r"\s+", " ", nome) or a["name"].strip()
        base = nome.lower()
        ano  = (a.get("release_date") or "")[:4]
        atual = melhores.get(base)
        if atual is None or (ano and ano < atual["year"]):
            melhores[base] = {
                "name": nome,
                "year": ano,
                "url":  a["external_urls"]["spotify"],
            }

    albuns = sorted(melhores.values(), key=lambda x: x["year"], reverse=True)
    return {
        "artist": artist["name"],
        "url":    artist["url"],
        "albums": albuns[:max_albums],
    }


def search_playlists(query: str, limit: int = 5) -> list[dict] | None:
    """Busca playlists públicas por gênero, tema ou clima."""
    data = _api_get("/search", {"q": query, "type": "playlist", "limit": PAGE_SIZE, "market": MARKET})
    if not data:
        return None

    results = []
    for p in data.get("playlists", {}).get("items", []):
        if not p:                 # a busca de playlist retorna itens nulos às vezes
            continue
        results.append({
            "name":  p.get("name") or "Playlist",
            "owner": (p.get("owner") or {}).get("display_name", ""),
            "image": p["images"][0]["url"] if p.get("images") else None,
            "url":   (p.get("external_urls") or {}).get("spotify", ""),
        })
        if len(results) == limit:
            break

    return results or None


def get_recommendations(seed_artist_name: str) -> list[dict] | None:
    """Gera até 5 recomendações de faixas baseadas num artista.

    Os endpoints /v1/recommendations e /v1/artists/{id}/top-tracks foram
    restringidos pelo Spotify para apps novos (passaram a retornar 403/404),
    então usamos a busca por faixas do próprio artista, que continua liberada.
    """
    # Confirma o nome canônico do artista (e que ele existe)
    artist = search_artist(seed_artist_name)
    if not artist:
        return None
    artist_name = artist["name"]

    data = _api_get(
        "/search",
        {"q": f'artist:"{artist_name}"', "type": "track", "limit": PAGE_SIZE, "market": MARKET},
    )
    if not data:
        return None

    # Mantém só faixas em que o artista-semente realmente aparece
    results = []
    vistos = set()
    for t in data.get("tracks", {}).get("items", []):
        nomes_artistas = [a["name"].lower() for a in t["artists"]]
        if artist_name.lower() not in nomes_artistas:
            continue
        if t["name"].lower() in vistos:      # evita repetir a mesma música
            continue
        vistos.add(t["name"].lower())
        results.append({
            "name":   t["name"],
            "artist": t["artists"][0]["name"],
            "url":    t["external_urls"]["spotify"],
        })
        if len(results) == 5:
            break

    return results or None


def get_artist_profile(name: str) -> dict | None:
    """Monta um perfil rico do artista: foto, músicas conhecidas e álbuns recentes.

    Observação: gêneros, seguidores e popularidade foram removidos pelo Spotify
    para apps novos, então enriquecemos com dados que continuam liberados.
    """
    artist = search_artist(name)
    if not artist:
        return None

    tracks = get_recommendations(artist["name"]) or []
    disco  = get_discography(artist["name"], max_albums=3)

    return {
        "name":   artist["name"],
        "url":    artist["url"],
        "image":  artist["image"],
        "tracks": tracks[:4],
        "albums": disco["albums"] if disco else [],
    }
