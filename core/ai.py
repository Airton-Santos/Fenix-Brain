import os
import re
from dotenv import load_dotenv 
from groq import Groq
from supabase import create_client, Client

load_dotenv()

# Configurações
client_groq = Groq(api_key=os.getenv("GROQ_API_KEY"))
supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

# Variável Global para manter o contexto entre as frases
# Isso resolve o problema de ele perguntar "Qual senhor?" e esquecer no próximo passo.
CONTEXTO_ANOTACAO = {"categoria": None}

GATILHOS_ANOTACAO = {
    "novo amigo": ("Quem seria senhor?", "amigos"),
    "comida favorita": ("Sério? Qual senhor?", "comida"),
    "comida preferida": ("Sério? Qual senhor?", "comida"),
    "adicionar uma informação": ("O quê desejar incrementar?", "pessoal"),
    "novo conhecimento": ("Que bom, poderia compartilhar esse conhecimento?", "trabalho"),
    "relacionamento": ("Pode falar senhor", "relacionamento"),
    "redes sociais": ("Estou ouvindo", "rede_social"),
    "nova preferencia": ("O que seria senhor?", "hobby")
}

GATILHOS_REMOVER = {
    "remover amigo": ("Qual amigo deseja retirar da lista?", "amigos"),
    "remover comida": ("Qual prato devo esquecer?", "comida"),
    "remover informação": ("O que deseja que eu esqueça sobre você?", "pessoal"),
    "remover conhecimento": ("Qual tecnologia não faz mais parte do seu foco?", "trabalho"),
    "limpar rede social": ("Qual rede social deseja remover?", "rede_social")
}

def salvar_no_supabase(categoria, nova_info):
    try:
        res = supabase.table("memoria_fenix").select("informacao").eq("categoria", categoria).execute()
        if res.data:
            valor_atual = res.data[0]['informacao']
            novo_valor = nova_info if "definir" in valor_atual.lower() else f"{valor_atual}, {nova_info}"
            supabase.table("memoria_fenix").update({"informacao": novo_valor}).eq("categoria", categoria).execute()
            return True
    except Exception as e:
        print(f"Erro ao salvar: {e}")
    return False

def remover_do_supabase(categoria, item_para_remover):
    try:
        res = supabase.table("memoria_fenix").select("informacao").eq("categoria", categoria).execute()
        if res.data:
            valor_atual = res.data[0]['informacao']
            itens = [i.strip() for i in valor_atual.split(",")]
            if item_para_remover.lower() not in [i.lower() for i in itens]:
                return "nao_encontrado"
            novos_itens = [i for i in itens if i.lower() != item_para_remover.lower()]
            novo_valor = ", ".join(novos_itens) if novos_itens else "A definir"
            supabase.table("memoria_fenix").update({"informacao": novo_valor}).eq("categoria", categoria).execute()
            return "removido"
    except Exception as e:
        print(f"Erro ao remover: {e}")
        return "erro"

def fenix_responder(mensagem: str) -> str:
    global CONTEXTO_ANOTACAO
    if not mensagem: return "Senhor, aguardo seu comando."
    msg = mensagem.lower()

    # --- LÓGICA DE CONTINUIDADE (O "Pulo do Gato") ---
    # Se ele estava esperando uma informação de uma categoria anterior
    if CONTEXTO_ANOTACAO["categoria"] is not None and "anotar" not in msg:
        categoria = CONTEXTO_ANOTACAO["categoria"]
        if salvar_no_supabase(categoria, mensagem.strip()):
            CONTEXTO_ANOTACAO["categoria"] = None # Limpa o contexto após salvar
            return f"Entendido, Senhor. Registrei '{mensagem.strip()}' em {categoria}."

    # 1. Lógica de Anotação (Comando Inicial)
    if "anotar" in msg:
        for gatilho, (resposta, categoria) in GATILHOS_ANOTACAO.items():
            if gatilho in msg:
                partes = re.split(f"{gatilho}|:", msg)
                info_para_salvar = partes[-1].strip()
                
                if info_para_salvar and len(info_para_salvar) > 2:
                    if salvar_no_supabase(categoria, info_para_salvar):
                        return f"Registro atualizado: {info_para_salvar} em {categoria}."
                
                # Se não tem o item na frase, ele "lembra" a categoria para a próxima fala
                CONTEXTO_ANOTACAO["categoria"] = categoria
                return resposta

    # 2. Lógica de Remoção
    if any(p in msg for p in ["remover", "esquecer", "tirar"]):
        for gatilho, (resposta, categoria) in GATILHOS_REMOVER.items():
            palavra_chave = gatilho.split()[-1] 
            if gatilho in msg or palavra_chave in msg:
                item_alvo = msg.split(palavra_chave)[-1].replace(":", "").strip()
                if item_alvo and len(item_alvo) > 2:
                    status = remover_do_supabase(categoria, item_alvo)
                    if status == "removido": return f"Removi '{item_alvo}' de {categoria}."
                return resposta

    # 3. Fluxo Normal
    try:
        res_memoria = supabase.table("memoria_fenix").select("*").execute()
        perfil = "\n".join([f"{m['categoria']}: {m['informacao']}" for m in res_memoria.data])
        
        sys_inst = (
            f"Você é o Fenix, assistente do Senhor Airton. Memória: {perfil}. "
            "Seja extremamente breve. Se o usuário disser apenas o nome de um item sem contexto, "
            "provavelmente é algo que ele quer anotar."
        )
        
        chat = client_groq.chat.completions.create(
            messages=[{"role": "system", "content": sys_inst}, {"role": "user", "content": mensagem}],
            model="llama-3.3-70b-versatile",
            temperature=0.5
        )
        
        resposta_final = chat.choices[0].message.content
        return re.sub(r'[^\w\s\d.,?!áàâãéèêíïóôõúüçÁÀÂÃÉÈÊÍÏÓÔÕÚÜÇ]', '', resposta_final)
    except Exception as e:
        return f"Senhor, erro no núcleo Fenix: {e}"