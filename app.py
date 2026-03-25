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
     ['Meu nome é ChatBotMusic, seu assistente musical!']),

    (r'Qual (é a sua|a sua|sua) idade\??',
     ['Eu sou um ChatBot, então não tenho idade! Mas nasci com muito amor pela música.']),

    (r'(Você é|Voce é) (um robô|um bot|humano|real)\??',
     ['Sou um ChatBot especializado em música! Não sou humano, mas entendo tudo sobre o mundo musical.']),

    (r'(Qual é o seu|Qual seu|Seu) gênero (musical )?(favorito|preferido)\??',
     ['Eu gosto de todos os gêneros musicais! De MPB ao heavy metal, cada um tem seu charme.']),

    (r'(Você gosta|Voce gosta) de música\??',
     ['Sim, eu adoro música! É minha razão de existir!']),

    (r'(Qual (é o seu|seu)|Seu) artista favorito\??',
     ['Eu gosto tanto de música que não consigo escolher um só! Há tantos artistas incríveis no mundo.']),

    (r'(Quem é|Quem foi) o? ?Michael Jackson\??',
     ['Michael Jackson é o "Rei do Pop"! Foi um dos maiores artistas da história, com hits como "Thriller", "Billie Jean" e "Beat It".']),

    (r'(Quem é|Quem foi) o? ?Eminem\??',
     ['Eminem é um rapper, compositor e produtor americano. Conhecido por suas letras impactantes, é considerado um dos maiores rappers de todos os tempos.']),

    (r'(Quem é|Quem foi) a? ?(Madonna|madonna)\??',
     ['Madonna é a "Rainha do Pop"! Com décadas de carreira, revolucionou a música pop com hits como "Like a Virgin" e "Material Girl".']),

    (r'(Quem é|Quem foi) o? ?(The Beatles|Beatles)\??',
     ['The Beatles foram uma das bandas mais influentes da história! John Lennon, Paul McCartney, George Harrison e Ringo Starr mudaram a música para sempre.']),

    (r'(Quem é|Quem foi) a? ?(Beyoncé|Beyonce)\??',
     ['Beyoncé é uma das maiores artistas do mundo! Conhecida por sua voz poderosa e performances incríveis, com hits como "Halo" e "Crazy in Love".']),

    (r'(O que é|Me fale sobre) (o )?rap\??',
     ['Rap é um estilo musical que combina rimas, ritmo e batidas. Surgiu nos Estados Unidos nos anos 70 e se tornou um dos gêneros mais populares do mundo!']),

    (r'(O que é|Me fale sobre) (o )?rock\??',
     ['Rock é um gênero musical baseado em guitarras elétricas, bateria e baixo. Surgiu nos anos 50 e gerou subgêneros como heavy metal, punk e grunge!']),

    (r'(O que é|Me fale sobre) (a )?MPB\??',
     ['MPB significa Música Popular Brasileira! É um gênero que mistura influências do samba, bossa nova, rock e outros estilos. Artistas como Caetano Veloso e Gilberto Gil são ícones da MPB.']),

    (r'(O que é|Me fale sobre) (o )?samba\??',
     ['Samba é um ritmo genuinamente brasileiro! Nasceu no Rio de Janeiro e é símbolo da cultura do Brasil, muito presente no carnaval.']),

    (r'(O que é|Me fale sobre) (o )?funk\??',
     ['Funk é um gênero muito popular no Brasil! Nasceu nos subúrbios do Rio de Janeiro e mistura batidas eletrônicas com letras do cotidiano.']),

    (r'(Me recomende|Recomende|Indique|Sugira) (uma )?música',
     ['Que tal ouvir "Bohemian Rhapsody" do Queen? É uma obra-prima!',
      'Recomendo "Thriller" do Michael Jackson, um clássico atemporal!',
      'Que tal "Garota de Ipanema" de Tom Jobim? Uma joia da bossa nova!',
      'Experimente "Lose Yourself" do Eminem, é impossível não se emocionar!']),

    (r'(Me recomende|Recomende|Indique|Sugira) (uma )?banda',
     ['O Queen é uma escolha incrível! Freddie Mercury era um gênio.',
      'Experimente os Beatles, eles revolucionaram a música!',
      'Que tal os Led Zeppelin? Rock puro e poderoso!']),

    (r'Estou (triste|chateado|mal|deprimido)',
     ['Para animar o dia nada melhor do que ouvir uma boa música! Que tal uma playlist animada?',
      'A música tem o poder de curar! Tente ouvir algo que te faça sorrir.']),

    (r'Estou (feliz|animado|bem|ótimo)',
     ['Que ótimo! Aproveite para ouvir sua música favorita e curtir ainda mais o dia!',
      'Felicidade combina muito com boa música! Bote um som e curta!']),

    (r'Estou (cansado|com sono|exausto)',
     ['Que tal uma música calma para relaxar? Jazz ou bossa nova funcionam muito bem!',
      'Música suave é ótima para descansar. Tente ouvir algo instrumental!']),

    (r'(Me conte|Sabia que|Curiosidade|Fato) (sobre )?música',
     ['Sabia que ouvir música ativa diversas áreas do cérebro simultaneamente? É uma das atividades mais complexas para o cérebro humano!',
      'Curiosidade: a canção "Happy Birthday to You" foi a mais reconhecida do século XX, segundo o Guinness World Records!',
      'Fato interessante: Mozart compôs sua primeira peça aos 5 anos de idade!']),

    (r'(Sair|Tchau|Adeus|Até mais|até logo)',
     ['Até mais! Foi um prazer falar sobre música com você! 🎵',
      'Tchau! Continue ouvindo boa música! 🎶']),

    (r'(.*)', ['Desculpe, não entendi. Pode reformular a pergunta?',
               'Pode me explicar de outra forma? Estou aqui para falar sobre música!',
               'Não entendi bem. Tente perguntar sobre artistas, gêneros musicais ou recomendações!'])
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
