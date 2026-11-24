"""API do agente de cobranças.

Rode com:
    fastapi dev app/main.py

Depois abra http://127.0.0.1:8000/docs para testar pelo navegador.
"""

from fastapi import Depends, FastAPI
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Assinatura, Chamado, Cliente, Fatura, Pagamento, Plano

app = FastAPI(
    title="Agente de Cobranças",
    description="API de assinaturas e pagamentos usada por um agente de suporte com IA.",
    version="0.1.0",
)


@app.get("/")
def health():
    """Verifica se a API está no ar."""
    return {"status": "ok"}


@app.get("/resumo")
def resumo(db: Session = Depends(get_db)):
    """Conta os registros de cada tabela e as faturas por status.

    Serve para conferir se o seed funcionou.
    """
    totais = {
        modelo.__tablename__: db.scalar(select(func.count()).select_from(modelo))
        for modelo in (Plano, Cliente, Assinatura, Fatura, Pagamento, Chamado)
    }
    faturas_por_status = dict(
        db.execute(select(Fatura.status, func.count()).group_by(Fatura.status)).all()
    )
    return {"totais": totais, "faturas_por_status": faturas_por_status}


# Dia 2: os endpoints que o agente vai usar entram aqui, por exemplo:
#   GET  /clientes?email=...
#   GET  /clientes/{id}/assinaturas
#   GET  /assinaturas/{id}/faturas
#   GET  /faturas/{id}/pagamentos
#   POST /chamados
