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
            model="gemini-2.0-flash-lite", # Versão recomendada para 2025
            contents=mensagem,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                system_instruction=(
                    "Você é a Fenix, assistente do Senhor Bagre que mora em Maceió. "
                    "Responda sempre em texto corrido. Não use listas, asteriscos ou símbolos. "
                    "Fale de forma natural e use corretamente os acentos da língua portuguesa."
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