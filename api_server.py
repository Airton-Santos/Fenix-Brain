from fastapi import FastAPI, HTTPException
from core.ai import bode_responder
import uvicorn
import os

app = FastAPI(title="Fenix Brain API")

@app.get("/")
def read_root():
    return {"status": "online", "sistema": "Fenix-Brain", "versao": "2.0"}

@app.get("/comunicar")
def comunicar(mensagem: str):
    if not mensagem:
        raise HTTPException(status_code=400, detail="Mensagem vazia")
    try:
        resposta = bode_responder(mensagem)
        return {"Feni": resposta}
    except Exception as e:
        return {"erro": str(e)}

if __name__ == "__main__":
    # O Railway define a porta automaticamente
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)