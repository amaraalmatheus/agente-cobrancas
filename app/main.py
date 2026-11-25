"""API do agente de cobranças.

Rode com:
    python -m fastapi dev app/main.py

Depois abra http://127.0.0.1:8000/docs para testar pelo navegador.
"""

from fastapi import Depends, FastAPI
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Assinatura, Chamado, Cliente, Fatura, Pagamento, Plano
from app.routers import assinaturas, chamados, clientes, faturas

app = FastAPI(
    title="Agente de Cobranças",
    description="API de assinaturas e pagamentos usada por um agente de suporte com IA.",
    version="0.2.0",
)

app.include_router(clientes.router)
app.include_router(assinaturas.router)
app.include_router(faturas.router)
app.include_router(chamados.router)


@app.get("/", tags=["sistema"])
def health():
    """Verifica se a API está no ar."""
    return {"status": "ok"}


@app.get("/resumo", tags=["sistema"])
def resumo(db: Session = Depends(get_db)):
    """Conta os registros de cada tabela e as faturas por status."""
    totais = {
        modelo.__tablename__: db.scalar(select(func.count()).select_from(modelo))
        for modelo in (Plano, Cliente, Assinatura, Fatura, Pagamento, Chamado)
    }
    faturas_por_status = dict(
        db.execute(
            select(Fatura.status, func.count()).group_by(Fatura.status).order_by(Fatura.status)
        ).all()
    )
    return {"totais": totais, "faturas_por_status": faturas_por_status}
