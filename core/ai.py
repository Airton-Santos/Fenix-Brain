import os
import re
import warnings
from dotenv import load_dotenv 
from groq import Groq

# Carrega as variáveis do arquivo .env
load_dotenv()

warnings.filterwarnings("ignore", category=UserWarning)

# CONFIGURAÇÃO: Busca a chave da Groq nas variáveis de ambiente do Railway
API_KEY = os.getenv("GROQ_API_KEY") 
client = Groq(api_key=API_KEY)

def bode_responder(mensagem: str) -> str:
    if not mensagem: return "Senhor, aguardo seu comando."

    # MODELO ÚNICO: Llama 3.3 70B (Extremamente inteligente e rápido)
    # Você também pode usar "gemma2-9b-it" se preferir a linha Gemma
    model_id = "llama-3.3-70b-versatile"
    sys_inst = "Você é a Fenix, assistente pessoal do Senhor Airton. Responda de forma direta, inteligente e em português."

    try:
        # Chamada única para a Groq
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": sys_inst},
                {"role": "user", "content": mensagem}
            ],
            model=model_id,
            temperature=0.7,
            max_tokens=500,
        )
        
        resposta_bruta = chat_completion.choices[0].message.content
        
        # Limpeza para evitar erros na voz (Edge-TTS)
        texto = re.sub(r'[^\w\s\d.,?!áàâãéèêíïóôõúüçÁÀÂÃÉÈÊÍÏÓÔÕÚÜÇ]', '', resposta_bruta)
        return " ".join(texto.split())
    
    except Exception as e:
        return f"Senhor, tive um problema técnico no núcleo Groq: {e}"