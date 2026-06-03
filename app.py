from flask import Flask, request, jsonify, render_template
import random
import re
import os
import base64
import requests
from dotenv import load_dotenv
import nltk
from nltk.chat.util import Chat, reflections

load_dotenv()
app = Flask(__name__)

_spotify_token = None  # cache do token em memória


def _get_spotify_token():
    """Gera (ou reutiliza) o access token via Client Credentials."""
    global _spotify_token
    if _spotify_token:
        return _spotify_token

    client_id     = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")

    if not client_id or not client_secret:
        return None

    # Codifica "client_id:client_secret" em Base64
    creds = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()

    resp = requests.post(
        "https://accounts.spotify.com/api/token",
        headers={
            "Authorization": f"Basic {creds}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={"grant_type": "client_credentials"},
        timeout=10,
    )

    if resp.status_code != 200:
        return None

    _spotify_token = resp.json()["access_token"]
    return _spotify_token


def spotify_search_track(query):
    """Busca até 3 faixas no Spotify pelo nome."""
    token = _get_spotify_token()
    if not token:
        return None

    resp = requests.get(
        "https://api.spotify.com/v1/search",
        headers={"Authorization": f"Bearer {token}"},
        params={"q": query, "type": "track", "limit": 3, "market": "BR"},
        timeout=10,
    )

    if resp.status_code != 200:
        return None

    items = resp.json().get("tracks", {}).get("items", [])
    if not items:
        return None

    results = []
    for t in items:
        results.append({
            "name":   t["name"],
            "artist": t["artists"][0]["name"],
            "album":  t["album"]["name"],
            "url":    t["external_urls"]["spotify"],
        })
    return results


def spotify_search_artist(query):
    token = _get_spotify_token()

    if not token:
        return None

    resp = requests.get(
        "https://api.spotify.com/v1/search",
        headers={"Authorization": f"Bearer {token}"},
        params={
            "q": query,
            "type": "artist",
            "limit": 1
        },
        timeout=10,
    )

    if resp.status_code != 200:
        print(resp.text)
        return None

    items = resp.json().get("artists", {}).get("items", [])

    if not items:
        return None

    artist = items[0]

    return {
        "id": artist["id"],
        "name": artist["name"],
        "url": artist["external_urls"]["spotify"],
        "image": artist["images"][0]["url"] if artist.get("images") else None,
    }


def spotify_get_recommendations(seed_artist_name):
    """Gera 5 recomendações de faixas baseadas em um artista."""
    token = _get_spotify_token()
    if not token:
        return None

    # Primeiro busca o ID do artista-semente
    artist = spotify_search_artist(seed_artist_name)
    params = {"limit": 5, "market": "BR"}

    if artist:
        params["seed_artists"] = artist["id"]
    else:
        params["seed_genres"] = "pop"  # fallback genérico

    resp = requests.get(
        "https://api.spotify.com/v1/recommendations",
        headers={"Authorization": f"Bearer {token}"},
        params=params,
        timeout=10,
    )

    if resp.status_code != 200:
        return None

    tracks = resp.json().get("tracks", [])
    return [
        {
            "name":   t["name"],
            "artist": t["artists"][0]["name"],
            "url":    t["external_urls"]["spotify"],
        }
        for t in tracks
    ]

def fmt_spotify_tracks(tracks, query):
    if not tracks:
        return f"Não encontrei nada no Spotify para <b>{query}</b>. Tente outro nome!"

    linhas = [f"🎵 Resultados no Spotify para <b>{query}</b>:<br>"]
    for i, t in enumerate(tracks, 1):
        linhas.append(
            f"{i}. <b>{t['name']}</b> — {t['artist']}<br>"
            f"&nbsp;&nbsp;&nbsp;💿 {t['album']}"
            f" &nbsp;<a href='{t['url']}' target='_blank'>▶ Ouvir</a>"
        )
    return "<br>".join(linhas)


def fmt_spotify_artist(info):
    if not info:
        return "Artista não encontrado no Spotify."

    imagem_html = ""

    if info.get("image"):
        imagem_html = (
            f"<img src='{info['image']}' "
            f"style='width:200px;border-radius:10px;margin-bottom:10px;'><br>"
        )

    return (
        imagem_html +
        f"🎤 <b>{info['name']}</b><br>"
        f"<a href='{info['url']}' target='_blank'>🔗 Ver perfil no Spotify</a>"
    )


def fmt_spotify_recommendations(tracks, seed):
    if not tracks:
        return f"Não consegui gerar recomendações baseadas em <b>{seed}</b>."

    linhas = [f"🎯 Recomendações baseadas em <b>{seed}</b>:<br>"]
    for t in tracks:
        linhas.append(
            f"• <b>{t['name']}</b> — {t['artist']}"
            f" <a href='{t['url']}' target='_blank'>▶</a>"
        )
    return "<br>".join(linhas)

def detect_spotify_intent(message):
    """
    Retorna (intent, payload) se a mensagem for um comando Spotify.
    Retorna (None, None) caso contrário — o NLTK assume o controle.
    """
    msg = message.lower().strip()

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

    # Recomendações: "recomendações parecidas com X", "músicas similares a X"
    m = re.search(
        r"(?:recomenda[çc][oõ]es?\s+(?:parecidas?\s+com|baseadas?\s+em|do\s+estilo\s+de)\s+|"
        r"m[úu]sicas?\s+(?:parecidas?\s+com|similares?\s+a[o]?\s+))(.+)",
        msg,
    )
    if m:
        return "recommendations", m.group(1).strip()

    return None, None

pares = [
    # 1. Olá
    (r'Ol[aá]|Oi|E a[íi]|Oi tudo bem\??|Ol[aá] tudo bem\??|Bom dia|Boa tarde|Boa noite',
     ['Olá! Seja bem-vindo ao ChatBotMusic! Aqui a gente só fala de música. Qual ritmo te move mais: rap, rock, pop ou outro?']),

    # 2. Rap
    (r'(.*)(rap|Rap|RAP)(.*)',
     ['Boa escolha! Rap é a arte de transformar palavras em impacto. Tem algum rapper que você já acompanha, ou quer que eu te apresente um?']),

    # 3 e 4. Sim / Quero
    (r'^(Sim|sim|Quero|quero|Pode|pode|Claro|claro|Com certeza|Vai|vai)$',
     ['Se você quer a essência do Eminem, vai de "Lose Yourself". É intensa, motivacional e tem um dos melhores flows da história do rap! Quer falar sobre outro tema?']),

    # 5. Me fale sobre pop
    (r'(.*)(pop|Pop|POP)(.*)',
     ['Pop é o gênero que une todo mundo! Tem artistas incríveis nessa cena. Você tem algum favorito, ou quer uma indicação minha?']),

    # 6. Me indique uma banda
    (r'(.*)(indique|recomende|sugira|quero)(.*)banda(.*)',
     ['Boa! Para quem curte energia e técnica, o Queen é obrigatório. Se preferir algo mais atual, o Imagine Dragons entrega muito. Quer saber mais sobre algum dos dois?']),

    # 7. Fala do Queen / Imagine Dragons
    (r'(.*)(Queen|queen)(.*)',
     ['Clássico absoluto! Uma curiosidade incrível sobre o Queen é que o guitarrista Brian May construiu sua icônica guitarra, a "Red Special", junto com seu pai. Eles usaram a madeira da moldura de uma lareira que tinha mais de 200 anos de idade! Quer saber mais sobre outro artista?']),

    (r'(.*)(Imagine Dragons|imagine dragons)(.*)',
     ['Que vibe boa! Você sabia que o nome "Imagine Dragons" é na verdade um anagrama? Os membros da banda pegaram uma frase que criaram juntos, misturaram as letras e formaram o nome. Até hoje, eles mantêm a frase original em segredo absoluto! Quer saber mais sobre outro artista?']),

    # 8. Me fale sobre Michael Jackson
    (r'(.*)(Michael Jackson|michael jackson)(.*)',
     ['Michael Jackson é o Rei do Pop sem discussão! Uma carreira que misturou dança, melodia e mensagem como ninguém. Já ouviu "Thriller" ou "Billie Jean"? Se não, começa por aí. Quer que eu te recomende uma música no estilo dele?']),

    # 9. Me recomende uma música no estilo dele (Michael)
    (r'(.*)estilo (dele|do michael|do michael jackson)(.*)',
     ['Ótima pedida! Se você curte o groove e a energia vocal do Michael, precisa ouvir "Treasure" do Bruno Mars ou "I Feel It Coming" do The Weeknd. Ambos bebem muito da fonte do Rei do Pop! Curtiu ou quer que eu te indique algo de outro estilo agora?']),

    # Rock
    # 10. Vamos falar de rock
    (r'(.*)(vamos falar de rock|falar sobre rock|falar de rock|quero falar de rock)(.*)',
     ['Excelente escolha! O rock tem muita atitude e história. Tem alguma banda que você quer saber mais, tipo o Nirvana?']),

    # 11. Me fale sobre Nirvana
    (r'(.*)(Nirvana|nirvana)(.*)',
     ['O Nirvana foi a voz da geração grunge nos anos 90! Com riffs sujos e as letras marcantes de Kurt Cobain, eles revolucionaram a música com o álbum "Nevermind". Quer que eu te recomende uma música no estilo deles?']),

    # 12. Me recomende uma música no estilo deles (Nirvana)
    (r'(.*)estilo (deles|do nirvana)(.*)',
     ['Se você curte a energia crua do Nirvana, recomendo ouvir "Everlong" do Foo Fighters (a banda do ex-baterista deles, Dave Grohl!) ou "Black Hole Sun" do Soundgarden. É rock na veia! Quer explorar mais algum ritmo agora?']),

    # Saídas e Respostas Curtas Extras
    (r'(Obrigad[ao]|Valeu|Vl[wv]|Tmj|At[eé] mais|Tchau|Flw)',
     ['Foi um prazer! Volta sempre que quiser descobrir música nova. A trilha sonora da sua vida fica ainda melhor com boas indicações!']),

    (r'(N[aã]o|nao|N[aã]o sei|nao sei|Talvez|talvez)',
     ['Sem problema! Me conta um pouco mais sobre o que você gosta de sentir quando ouve música. É para animar, relaxar, refletir? Assim consigo te indicar algo mais certeiro.']),

    # Rock genérico
    (r'(.*)(rock|Rock|ROCK)(.*)',
     ['Rock é paixão pura! De clássico a alternativo, tem muita coisa boa. Você prefere algo mais antigo, tipo anos 70-80, ou um rock mais atual?']),

    # Fallback
    (r'(.*)',
     ['Hmm, não entendi bem. Me conta: você prefere rap, rock, pop ou música brasileira? Assim consigo te ajudar melhor!',
      'Pode me dar mais uma dica? Me diz um artista ou gênero que você curte e eu te mostro o caminho!'])
]

reflexoes = {
    "eu": "você",
    "meu": "seu",
    "minha": "sua",
    "você": "eu",
    "seu": "meu",
    "sua": "minha",
}

chatbot = Chat(pares, reflexoes)

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/chat', methods=['POST'])
def chat():
    data         = request.get_json()
    user_message = (data.get('message') or '').strip()

    if not user_message:
        return jsonify({'response': 'Mensagem vazia!'})

    # ── 1ª tentativa: Spotify ─────────────────────────────
    intent, payload = detect_spotify_intent(user_message)

    try:
        if intent == "track":
            tracks = spotify_search_track(payload)
            return jsonify({'response': fmt_spotify_tracks(tracks, payload)})

        elif intent == "artist":
            info = spotify_search_artist(payload)
            return jsonify({'response': fmt_spotify_artist(info)})

        elif intent == "recommendations":
            tracks = spotify_get_recommendations(payload)
            return jsonify({'response': fmt_spotify_recommendations(tracks, payload)})

    except Exception as e:
        print(f"[Spotify Error] {e}")
        # Se a API falhar, cai no NLTK normalmente

    # ── 2ª tentativa: padrões NLTK originais ──────────────
    response = chatbot.respond(user_message)

    if response is None:
        response = random.choice([
            "Não entendi muito bem! Me diz um gênero ou artista que você curte e eu te ajudo.",
            "Pode reformular? Me conta o que você gosta de ouvir e a gente conversa melhor!"
        ])

    return jsonify({'response': response})


if __name__ == '__main__':
    app.run(debug=True)
