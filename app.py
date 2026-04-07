from flask import Flask, request, jsonify, render_template
import random
import nltk
from nltk.chat.util import Chat, reflections

app = Flask(__name__)

pares = [
    # 1. Olá
    (r'Ol[aá]|Oi|E a[íi]|Oi tudo bem\??|Ol[aá] tudo bem\??|Bom dia|Boa tarde|Boa noite',
     ['Olá! Seja bem-vindo ao ChatBotMusic! Aqui a gente só fala de música. Qual ritmo te move mais?']),

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

    # --- NOVO FLUXO DE ROCK ---
    # 10. Vamos falar de rock
    (r'(.*)(vamos falar de rock|falar sobre rock|falar de rock|quero falar de rock)(.*)',
     ['Excelente escolha! O rock tem muita atitude e história. Tem alguma banda que você quer saber mais, tipo o Nirvana?']),

    # 11. Me fale sobre Nirvana
    (r'(.*)(Nirvana|nirvana)(.*)',
     ['O Nirvana foi a voz da geração grunge nos anos 90! Com riffs sujos e as letras marcantes de Kurt Cobain, eles revolucionaram a música com o álbum "Nevermind". Quer que eu te recomende uma música no estilo deles?']),

    # 12. Me recomende uma música no estilo deles (Nirvana)
    (r'(.*)estilo (deles|do nirvana)(.*)',
     ['Se você curte a energia crua do Nirvana, recomendo ouvir "Everlong" do Foo Fighters (a banda do ex-baterista deles, Dave Grohl!) ou "Black Hole Sun" do Soundgarden. É rock na veia! Quer explorar mais algum ritmo agora?']),
    # --------------------------

    # Saídas e Respostas Curtas Extras
    (r'(Obrigad[ao]|Valeu|Vl[wv]|Tmj|At[eé] mais|Tchau|Flw)',
     ['Foi um prazer! Volta sempre que quiser descobrir música nova. A trilha sonora da sua vida fica ainda melhor com boas indicações!']),

    (r'(N[aã]o|nao|N[aã]o sei|nao sei|Talvez|talvez)',
     ['Sem problema! Me conta um pouco mais sobre o que você gosta de sentir quando ouve música. É para animar, relaxar, refletir? Assim consigo te indicar algo mais certeiro.']),

    # Regra de Rock genérica (caso o usuário diga apenas "rock" e não "vamos falar de rock")
    (r'(.*)(rock|Rock|ROCK)(.*)',
     ['Rock é paixão pura! De clássico a alternativo, tem muita coisa boa. Você prefere algo mais antigo, tipo anos 70-80, ou um rock mais atual?']),

    # Fallback (Gatilho de Segurança)
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
    data = request.get_json()
    user_message = data.get('message', '').strip()

    if not user_message:
        return jsonify({'response': 'Mensagem vazia!'})

    response = chatbot.respond(user_message)
    
    if response is None:
        response = random.choice([
            "Não entendi muito bem! Me diz um gênero ou artista que você curte e eu te ajudo.",
            "Pode reformular? Me conta o que você gosta de ouvir e a gente conversa melhor!"
        ])

    return jsonify({'response': response})

if __name__ == '__main__':
    app.run(debug=True)