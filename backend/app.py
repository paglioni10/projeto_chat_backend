from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
import os
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup

# === 1️⃣ Carrega a chave da API ===
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("A chave GEMINI_API_KEY não foi encontrada no arquivo .env")

genai.configure(api_key=api_key)

# === 2️⃣ Inicializa o Flask ===
app = Flask(__name__)
CORS(app)

# === 3️⃣ Configura o modelo ===
model = genai.GenerativeModel("gemini-2.0-flash")

# === 4️⃣ Funções auxiliares ===
def extrair_conteudo_site(url: str) -> str:
    """Extrai texto do site Jovem Programador."""
    try:
        resposta = requests.get(url, timeout=10)
        resposta.raise_for_status()
        soup = BeautifulSoup(resposta.text, "html.parser")
        return soup.get_text(separator="\n", strip=True)
    except Exception:
        return "Erro ao acessar o site Jovem Programador."

def extrair_dados_imagens(url: str):
    """Extrai informações das imagens do site com atributos de acessibilidade."""
    try:
        resposta = requests.get(url, timeout=10)
        resposta.raise_for_status()
        soup = BeautifulSoup(resposta.text, "html.parser")

        imagens = []
        for figura in soup.find_all("figure"):
            img = figura.find("img")
            legenda = figura.find("figcaption")
            if img:
                imagens.append({
                    "src": img.get("src"),
                    "alt": img.get("alt"),
                    "title": img.get("title"),
                    "legenda": legenda.get_text(strip=True) if legenda else None
                })

        for img in soup.find_all("img"):
            if not any(img.get("src") == i["src"] for i in imagens):
                imagens.append({
                    "src": img.get("src"),
                    "alt": img.get("alt"),
                    "title": img.get("title"),
                    "legenda": None
                })
        return imagens
    except Exception:
        return []

# === 5️⃣ Rota principal ===
@app.route("/perguntar", methods=["POST"])
def perguntar():
    dados = request.json
    pergunta = dados.get("pergunta", "").strip()

    if not pergunta:
        return jsonify({"resposta": "Por favor, digite uma pergunta válida."})

    # ===========================================================================================
    # ✅  RESPOSTAS AUTOMÁTICAS PARA CUMPRIMENTOS E DESPEDIDAS
    # ===========================================================================================

    cumprimentos = {
        "oi": "Olá! Como posso ajudar você hoje?",
        "olá": "Olá! Tudo bem? Estou aqui para ajudar.",
        "bom dia": "Bom dia! Como posso ajudar você?",
        "boa tarde": "Boa tarde! Precisa de alguma informação?",
        "boa noite": "Boa noite! Como posso ajudar?",
        "e aí": "E aí! Tudo certo? Como posso ajudar?"
    }

    despedidas = {
        "tchau": "Até mais! Se precisar, estou aqui.",
        "até logo": "Até logo! Volte sempre 😊",
        "até mais": "Até mais! Foi um prazer ajudar.",
        "falou": "Falou! Qualquer coisa, me chame!",
        "obrigado": "Disponha! Sempre que precisar, estou por aqui.",
        "valeu": "Valeu! Conte comigo sempre!"
    }

    pergunta_lower = pergunta.lower()

    # ✔ Verifica cumprimentos
    for termo in cumprimentos:
        if termo in pergunta_lower:
            return jsonify({"resposta": cumprimentos[termo]})

    # ✔ Verifica despedidas
    for termo in despedidas:
        if termo in pergunta_lower:
            return jsonify({"resposta": despedidas[termo]})

    # ===========================================================================================

    # 🚫 Bloqueia perguntas fora do tema
    termos_permitidos = [
        "jovem programador", "curso", "inscrição", "site",
        "senac", "sesi", "empregabilidade", "ensino", "formação", "aprendizagem"
    ]

    if not any(palavra in pergunta_lower for palavra in termos_permitidos):
        return jsonify({
            "resposta": (
                "Posso responder apenas sobre o site Jovem Programador. "
                "Por favor, envie uma pergunta relacionada a ele."
            )
        })

    conteudo_site = extrair_conteudo_site("https://www.jovemprogramador.com.br")
    imagens_info = extrair_dados_imagens("https://www.jovemprogramador.com.br")

    imagens_texto = "\n".join([
        f"- Imagem: {img.get('alt', 'Sem descrição disponível')}. "
        f"Título: {img.get('title', 'sem título')}. "
        f"Legenda: {img.get('legenda', 'sem legenda')}."
        for img in imagens_info
    ])

    prompt = f"""
    Você é um assistente especializado no site Jovem Programador (https://www.jovemprogramador.com.br).
    Responda APENAS com base nas informações desse site.
    Caso a pergunta não esteja relacionada, informe que só pode responder sobre o site Jovem Programador.

    Conteúdo do site:
    {conteudo_site}

    Informações sobre imagens:
    {imagens_texto}

    Pergunta do usuário:
    {pergunta}
    """

    try:
        resposta = model.generate_content(prompt)
        texto_resposta = resposta.text.strip()
    except Exception as e:
        texto_resposta = f"Ocorreu um erro ao gerar a resposta: {e}"

    # Resposta de fallback acessível
    if not texto_resposta or len(texto_resposta) < 20:
        texto_resposta = (
            "Não encontrei informações suficientes no site Jovem Programador "
            "para responder a essa pergunta."
        )

    return jsonify({"resposta": texto_resposta})

# === 6️⃣ Executa o servidor ===
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
