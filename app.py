from flask import Flask, request, jsonify, render_template
import random
import nltk
from nltk.chat.util import Chat, reflections

app = Flask(__name__)

pares = [
    (r'Olá|Oi|E aí|Oi tudo bem\??|Olá tudo bem\??',
     ['Olá! Bem-vindo ao ChatBotMusic! Você gosta de música? (Você gosta de música?)',
      'Oi! Estou aqui para falar sobre música! Qual é o seu gênero favorito? (Qual é o seu gênero favorito?)']),

    (r'Qual (é o seu|o seu|seu) nome\??',
     ['Meu nome é ChatBotMusic! Você gosta de música? (Você gosta de música?)']),

    (r'(Qual é o seu|Qual seu|Seu) gênero (musical )?(favorito|preferido)\??',
     ['Eu gosto de todos os gêneros musicais! Quer saber mais sobre rap? (O que é rap?)']),

    (r'(Você gosta|Voce gosta) de música\??',
     ['Sim, eu adoro música! Qual é o seu artista favorito? (Qual é o seu artista favorito?)']),

    (r'(Qual (é o seu|seu)|Seu) artista favorito\??',
     ['Há muitos artistas incríveis! Quer uma recomendação? (Me recomende uma música)']),

    (r'(Quem é|Quem foi) o? ?Michael Jackson\??',
     ['Michael Jackson é o "Rei do Pop"! Você já ouviu falar sobre funk? (O que é funk?)']),

    (r'(Quem é|Quem foi) o? ?Eminem\??',
     ['Eminem é um dos maiores rappers! Quer saber mais sobre rap? (O que é rap?)']),

    (r'(Quem é|Quem foi) a? ?(Madonna|madonna)\??',
     ['Madonna é a "Rainha do Pop"! Você gosta de pop? (Qual é o seu gênero favorito?)']),

    (r'(Quem é|Quem foi) o? ?(The Beatles|Beatles)\??',
     ['The Beatles foram muito influentes! Quer conhecer rock? (O que é rock?)']),

    (r'(Quem é|Quem foi) a? ?(Beyoncé|Beyonce)\??',
     ['Beyoncé é uma grande artista! Quer uma recomendação? (Me recomende uma música)']),

    (r'(O que é|Me fale sobre) (o )?rap\??',
     ['Rap combina rimas e batidas! Quer uma sugestão? (Me recomende uma música)']),

    (r'(O que é|Me fale sobre) (o )?rock\??',
     ['Rock é baseado em guitarras! Quer uma banda? (Me recomende uma banda)']),

    (r'(O que é|Me fale sobre) (a )?MPB\??',
     ['MPB mistura vários estilos! Quer saber sobre samba? (O que é samba?)']),

    (r'(O que é|Me fale sobre) (o )?samba\??',
     ['Samba é um ritmo brasileiro! Quer saber sobre funk? (O que é funk?)']),

    (r'(O que é|Me fale sobre) (o )?funk\??',
     ['Funk é muito popular no Brasil! Quer uma recomendação? (Me recomende uma música)']),

    (r'(Me recomende|Recomende|Indique|Sugira) (uma )?música',
     ['Que tal "Thriller" do Michael Jackson? Quer outra? (Me recomende uma banda)',
      'Experimente "Lose Yourself"! Quer mais? (Me recomende uma música)']),

    (r'(Me recomende|Recomende|Indique|Sugira) (uma )?banda',
     ['Experimente Queen! Quer uma música deles? (Me recomende uma música)',
      'Que tal Beatles? Quer outra banda? (Me recomende uma banda)']),

    (r'(.*)', ['Não entendi bem. Quer falar sobre artistas? (Qual é o seu artista favorito?)',
               'Pode reformular? Quer falar sobre gêneros? (Qual é o seu gênero favorito?)'])
]

reflexoes = {
    "eu": "você",
    "meu": "seu",
    "minha": "sua",
    "você": "eu",
    "seu": "meu",
    "sua": "minha",
    "eu sou": "você é",
    "você é": "eu sou",
    "eu estava": "você estava",
    "você estava": "eu estava",
}

chatbot = Chat(pares, reflexoes)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    user_message = data.get('message', '')

    if not user_message:
        return jsonify({'response': 'Mensagem vazia!'})

    response = chatbot.respond(user_message)
    if response is None:
        response = random.choice([
            "Desculpe, não entendi. Pode reformular?",
            "Pode me explicar de outra forma?",
            "Não entendi bem. Tente perguntar sobre artistas ou gêneros musicais!"
        ])

    return jsonify({'response': response})


if __name__ == '__main__':
    app.run(debug=True)
