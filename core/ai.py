import os
import re
from dotenv import load_dotenv 
from groq import Groq
from supabase import create_client, Client

load_dotenv()

# Configurações
client_groq = Groq(api_key=os.getenv("GROQ_API_KEY"))
supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

# Dicionário de Gatilhos e Respostas Personalizadas para Anotação

GATILHOS_ANOTACAO = {
    "novo amigo": ("Quem seria senhor?", "amigos"),
    "comida favorita": ("Sério? Qual senhor?", "comida"),
    "adicionar uma informação": ("O quê desejar incrementar?", "pessoal"),
    "novo conhecimento": ("Que bom, poderia compartilhar esse conhecimento?", "trabalho"),
    "relacionamento": ("Pode falar senhor", "relacionamento"),
    "redes sociais": ("Estou ouvindo", "rede_social"),
    "nova preferencia": ("O que seria senhor?", "hobby")
}

# Dicionário de Gatilhos para Remoção
GATILHOS_REMOVER = {
    "remover amigo": ("Qual amigo deseja retirar da lista?", "amigos"),
    "remover comida": ("Qual prato devo esquecer?", "comida"),
    "remover informação": ("O que deseja que eu esqueça sobre você?", "pessoal"),
    "remover conhecimento": ("Qual tecnologia não faz mais parte do seu foco?", "trabalho"),
    "limpar rede social": ("Qual rede social deseja remover?", "rede_social")
}

def salvar_no_supabase(categoria, nova_info):
    """Atualiza a informação no banco de dados concatenando com o que já existe"""
    try:
        res = supabase.table("memoria_fenix").select("informacao").eq("categoria", categoria).execute()
        if res.data:
            valor_atual = res.data[0]['informacao']
            # Se for 'A definir', substitui. Se não, adiciona com vírgula.
            novo_valor = nova_info if "definir" in valor_atual.lower() else f"{valor_atual}, {nova_info}"
            supabase.table("memoria_fenix").update({"informacao": novo_valor}).eq("categoria", categoria).execute()
            return True
    except Exception as e:
        print(f"Erro ao salvar: {e}")
    return False

def remover_do_supabase(categoria, item_para_remover):
    """Localiza e remove um item específico da lista na tabela memoria_fenix"""
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

    # 1. Lógica de Anotação Melhorada
    if "anotar" in msg:
        for gatilho, (resposta, categoria) in GATILHOS_ANOTACAO.items():
            if gatilho in msg:
                # Extrai tudo o que vem DEPOIS do gatilho ou depois de dois pontos
                partes = re.split(f"{gatilho}|:", msg)
                info_para_salvar = partes[-1].strip()
                
                # Se o usuário falou o item na mesma frase (ex: "anotar comida favorita pizza")
                if info_para_salvar and len(info_para_salvar) > 2:
                    if salvar_no_supabase(categoria, info_para_salvar):
                        return f"Entendido, Senhor. {info_para_salvar} foi registrado em {categoria}."
                
                # Se ele só deu o comando, retorna a pergunta de confirmação
                return resposta

        return "Senhor, não entendi o que deseja anotar. Poderia repetir o comando com a categoria correta?"

    # 2. Lógica de Remoção
    if any(palavra in msg for palavra in ["remover", "esquecer", "tirar"]):
        for gatilho, (resposta, categoria) in GATILHOS_REMOVER.items():
            palavra_chave_categoria = gatilho.split()[-1] 
            if gatilho in msg or palavra_chave_categoria in msg:
                item_alvo = msg.split(palavra_chave_categoria)[-1].replace(":", "").replace("remover", "").replace("tirar", "").strip()
                
                if item_alvo and len(item_alvo) > 2:
                    status = remover_do_supabase(categoria, item_alvo)
                    if status == "removido":
                        return f"Entendido, Senhor. Removi '{item_alvo}' de sua lista de {categoria}."
                    elif status == "nao_encontrado":
                        return f"Senhor, não encontrei '{item_alvo}' na lista de {categoria}."
                return resposta

    # 3. Fluxo Normal: Groq + Memória do Supabase
    try:
        res_memoria = supabase.table("memoria_fenix").select("*").execute()
        perfil = "\n".join([f"{m['categoria']}: {m['informacao']}" for m in res_memoria.data])
        
        # Instrução de sistema para que a Groq saiba que pode sugerir anotações
        sys_inst = (
            f"Você é o Fenix, assistente pessoal do Senhor Airton. "
            f"Suas memórias atuais são: {perfil}. "
            "Sempre que o Senhor Airton mencionar algo que pareça uma nova preferência, "
            "comida, amigo ou conhecimento, confirme e lembre-o de usar o comando 'anotar' para salvar."
        )
        
        chat = client_groq.chat.completions.create(
            messages=[{"role": "system", "content": sys_inst}, {"role": "user", "content": mensagem}],
            model="llama-3.3-70b-versatile",
            temperature=0.6
        )
        
        resposta_final = chat.choices[0].message.content
        # Limpeza básica mantendo acentuação
        return re.sub(r'[^\w\s\d.,?!áàâãéèêíïóôõúüçÁÀÂÃÉÈÊÍÏÓÔÕÚÜÇ]', '', resposta_final)
    except Exception as e:
        return f"Senhor, erro no processamento do núcleo Fenix: {e}"