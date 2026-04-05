from flask import Flask, request, jsonify, render_template
import random
import nltk
from nltk.chat.util import Chat, reflections

app = Flask(__name__)

pares = [
    (r'Olá|Oi|E aí|Oi tudo bem\??|Olá tudo bem\??',
     ['Olá! Bem-vindo ao ChatBotMusic! Como posso ajudar você hoje?',
      'Oi! Estou aqui para falar tudo sobre música. O que você quer saber?']),

    (r'Qual (é o seu|o seu|seu) nome\??',
     ['Meu nome é ChatBotMusic, seu assistente musical! Qual é o seu nome?']),

    (r'Qual (é a sua|a sua|sua) idade\??',
     ['Eu sou um ChatBot, então não tenho idade! Você gosta de música há muito tempo?']),

    (r'(Você é|Voce é) (um robô|um bot|humano|real)\??',
     ['Sou um ChatBot especializado em música! Qual tipo de música você gosta?']),

    (r'(Qual é o seu|Qual seu|Seu) gênero (musical )?(favorito|preferido)\??',
     ['Eu gosto de todos os gêneros musicais! Qual é o seu gênero favorito?']),

    (r'(Você gosta|Voce gosta) de música\??',
     ['Sim, eu adoro música! Qual música você mais tem ouvido ultimamente?']),

    (r'(Qual (é o seu|seu)|Seu) artista favorito\??',
     ['Eu gosto de muitos artistas! Qual é o seu artista favorito?']),

    (r'(Quem é|Quem foi) o? ?Michael Jackson\??',
     ['Michael Jackson é o "Rei do Pop"! Você gosta das músicas dele?']),

    (r'(Quem é|Quem foi) o? ?Eminem\??',
     ['Eminem é um dos maiores rappers de todos os tempos! Você curte rap?']),

    (r'(Quem é|Quem foi) a? ?(Madonna|madonna)\??',
     ['Madonna é a "Rainha do Pop"! Você gosta de música pop?']),

    (r'(Quem é|Quem foi) o? ?(The Beatles|Beatles)\??',
     ['The Beatles foram extremamente influentes! Você já ouviu alguma música deles?']),

    (r'(Quem é|Quem foi) a? ?(Beyoncé|Beyonce)\??',
     ['Beyoncé é uma das maiores artistas do mundo! Você gosta das músicas dela?']),

    (r'(O que é|Me fale sobre) (o )?rap\??',
     ['Rap combina rimas, ritmo e batidas! Você gosta desse estilo?']),

    (r'(O que é|Me fale sobre) (o )?rock\??',
     ['Rock é baseado em guitarras e bateria! Você prefere rock clássico ou moderno?']),

    (r'(O que é|Me fale sobre) (a )?MPB\??',
     ['MPB mistura várias influências brasileiras! Você costuma ouvir MPB?']),

    (r'(O que é|Me fale sobre) (o )?samba\??',
     ['Samba é um ritmo brasileiro muito tradicional! Você gosta de samba?']),

    (r'(O que é|Me fale sobre) (o )?funk\??',
     ['Funk é muito popular no Brasil! Você costuma ouvir funk?']),

    (r'(Me recomende|Recomende|Indique|Sugira) (uma )?música',
     ['Que tal ouvir "Bohemian Rhapsody" do Queen? Você já ouviu essa música?',
      'Recomendo "Thriller" do Michael Jackson! Você gosta desse estilo?',
      'Que tal "Garota de Ipanema" de Tom Jobim? Você curte bossa nova?',
      'Experimente "Lose Yourself" do Eminem! Você gosta de rap?']),

    (r'(Me recomende|Recomende|Indique|Sugira) (uma )?banda',
     ['O Queen é uma escolha incrível! Você gosta de rock?',
      'Experimente os Beatles! Você já ouviu alguma música deles?',
      'Que tal Led Zeppelin? Você prefere rock mais pesado?']),

    (r'Estou (triste|chateado|mal|deprimido)',
     ['A música pode animar! Quer que eu recomende algo animado?',
      'Que tal ouvir algo alegre? Prefere pop ou rock?']),

    (r'Estou (feliz|animado|bem|ótimo)',
     ['Que ótimo! Quer uma recomendação para comemorar?',
      'Felicidade combina com música! Quer que eu sugira algo?']),

    (r'Estou (cansado|com sono|exausto)',
     ['Que tal uma música calma? Prefere instrumental ou lo-fi?',
      'Música suave ajuda a relaxar! Quer uma recomendação?']),

    (r'(Me conte|Sabia que|Curiosidade|Fato) (sobre )?música',
     ['Sabia que ouvir música ativa várias áreas do cérebro? Você gosta de curiosidades?',
      'Mozart compôs sua primeira peça aos 5 anos! Quer saber outra curiosidade?']),

    (r'(Sair|Tchau|Adeus|Até mais|até logo)',
     ['Até mais! Quer conversar novamente depois?',
      'Tchau! Quer voltar para falar mais sobre música?']),

    (r'(.*)', ['Desculpe, não entendi. Pode reformular a pergunta?',
               'Pode me explicar de outra forma?',
               'Não entendi bem. Quer perguntar sobre artistas ou gêneros musicais?'])
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