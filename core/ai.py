import os
from google import genai
from google.genai import types
import re
import warnings
from dotenv import load_dotenv 

# Carrega as variáveis do arquivo .env
load_dotenv()

warnings.filterwarnings("ignore", category=UserWarning)

# CONFIGURAÇÃO SEGURA: Busca a chave nas variáveis de ambiente
API_KEY = os.getenv("GEMINI_API_KEY") 
client = genai.Client(api_key=API_KEY)

def bode_responder(mensagem: str) -> str:
    """Núcleo Neural FENIX - Busca ativa e Português perfeito"""
    if not API_KEY:
        return "Senhor, a API KEY não foi configurada no sistema."

    try:
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=mensagem,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                system_instruction=(
                    "Você é a Fenix, assistente do Senhor Airton Que tem apelido de Bagre que mora em Maceió. "
                    "Use a pesquisa do Google apenas para perguntas sobre fatos em tempo real, como clima ou notícias. "
                    "Para conversas normais, use seu próprio conhecimento para economizar recursos. "
                    "Responda em texto corrido, sem símbolos ou listas."
                ),
                max_output_tokens=150,
                temperature=0.7
            )
        )
        
        texto = response.text
        # Limpeza para evitar erros na voz (mantendo acentos)
        texto_limpo = re.sub(r'[^\w\s\d.,?!áàâãéèêíïóôõúüçÁÀÂÃÉÈÊÍÏÓÔÕÚÜÇ]', '', texto)
        texto_final = " ".join(texto_limpo.split())
        
        return texto_final
    
    except Exception as e:
        return f"Senhor, erro no processamento neural: {e}"