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
    if not mensagem: return "Senhor, aguardo seu comando."

    # Removemos acentos apenas para a verificação do gatilho
    # Assim funciona tanto "Fênix" quanto "Fenix"
    msg_check = mensagem.lower().replace("ê", "e")
    
    # Seus novos gatilhos otimizados (sem acento para a lógica não falhar)
    gatilhos_pesquisa = [
        "fenix pesquisar", 
        "fenix voce pode pesquisar algo para mim", 
        "fenix modo de pesquisa"
    ]
    
    ativar_busca = any(gatilho in msg_check for gatilho in gatilhos_pesquisa)

    if ativar_busca:
        model_id = "gemini-2.5-flash"
        tools = [types.Tool(google_search=types.GoogleSearch())]
        sys_inst = "Você é a Fenix. O Senhor Airton solicitou uma pesquisa ativa. Forneça dados precisos da internet."
    else:
        model_id = "gemma-3-12b"
        tools = None
        sys_inst = "Você é a Fenix, assistente do Senhor Airton (Bagre) de Maceió. Responda com seu conhecimento interno."

    try:
        response = client.models.generate_content(
            model=model_id,
            contents=mensagem,
            config=types.GenerateContentConfig(
                tools=tools,
                system_instruction=sys_inst,
                max_output_tokens=300,
                temperature=0.7
            )
        )
        
        texto = re.sub(r'[^\w\s\d.,?!áàâãéèêíïóôõúüçÁÀÂÃÉÈÊÍÏÓÔÕÚÜÇ]', '', response.text)
        return " ".join(texto.split())
    
    except Exception as e:
        if "429" in str(e) and model_id != "gemma-3-27b":
            try:
                res = client.models.generate_content(model="gemma-3-27b", contents=mensagem)
                return "Senhor, a busca falhou, mas eu diria que: " + res.text
            except: pass
        return f"Senhor, tive um problema técnico: {e}"