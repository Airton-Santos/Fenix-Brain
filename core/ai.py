import os
import re
from dotenv import load_dotenv 
from groq import Groq
from supabase import create_client, Client

load_dotenv()

# Configurações
client_groq = Groq(api_key=os.getenv("GROQ_API_KEY"))
supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

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
        cat_clean = categoria.lower().strip()
        res = supabase.table("memoria_fenix").select("informacao").eq("categoria", cat_clean).execute()
        
        if res.data:
            valor_atual = res.data[0]['informacao']
            
            if "definir" in valor_atual.lower():
                novo_valor = nova_info.capitalize()
            else:
                if nova_info.lower() not in valor_atual.lower():
                    novo_valor = f"{valor_atual}, {nova_info.capitalize()}"
                else:
                    return True
            
            update_res = supabase.table("memoria_fenix").update({"informacao": novo_valor}).eq("categoria", cat_clean).execute()
            
            if update_res.data:
                print(f"DEBUG: Sucesso ao salvar {nova_info} em {cat_clean}")
                return True
    except Exception as e:
        print(f"Erro crítico ao salvar no Supabase: {e}")
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
    if not mensagem: return "Senhor, aguardo seu comando."
    msg = mensagem.lower()

    # 1. Lógica de Anotação (Apenas comandos explícitos)
    if "anotar" in msg:
        for gatilho, (resposta, categoria) in GATILHOS_ANOTACAO.items():
            if gatilho in msg:
                partes = re.split(f"{gatilho}|:", msg)
                info_para_salvar = partes[-1].strip()
                
                if info_para_salvar and len(info_para_salvar) > 2:
                    if salvar_no_supabase(categoria, info_para_salvar):
                        return f"Entendido, Senhor. {info_para_salvar} foi registrado em {categoria}."
                
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

    # 3. Fluxo Normal (Conversa e Consulta à Memória)
    try:
        res_memoria = supabase.table("memoria_fenix").select("*").execute()
        perfil = "\n".join([f"{m['categoria']}: {m['informacao']}" for m in res_memoria.data])
        
        sys_inst = (
            f"Você é o Fenix, o fiel assistente pessoal do Senhor Airton. "
            f"Sua memória atual é: {perfil}. "
            "Regras de personalidade: "
            "1. Seja extremamente breve e direto. "
            "2. Você é leal ao Senhor Airton, mas também à Nathalia (noiva dele). "
            "3. Se o Senhor Airton pedir algo que contradiga a memória (como procurar sites de relacionamento), "
            "lembre-o de forma bem-humorada ou irônica sobre o compromisso dele com a Nathalia."
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