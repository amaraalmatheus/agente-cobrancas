# Agente de Suporte para Cobranças

Agente com IA que atende clientes de um serviço de assinaturas: consulta faturas
e pagamentos por uma API REST e responde dúvidas como "por que fui cobrado duas vezes?".

> 🚧 Em desenvolvimento. Este README vai ganhar arquitetura, prints e resultados da avaliação no dia 7.

## Stack

- Python 3.11+ e FastAPI
- SQLAlchemy 2 com SQLite (PostgreSQL em produção)
- Faker para os dados fictícios
- pytest

## Como rodar

```bash
# 1. Criar e ativar o ambiente virtual
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# 2. Instalar as dependências
pip install -r requirements.txt

# 3. Criar o banco com dados fictícios
python -m scripts.seed

# 4. Subir a API
fastapi dev app/main.py
```

Abra http://127.0.0.1:8000/docs e teste o endpoint `/resumo`.

## Modelo de dados

```
Cliente 1──N Assinatura N──1 Plano
Assinatura 1──N Fatura 1──N Pagamento   (cada tentativa de cobrança é um pagamento)
Cliente 1──N Chamado
```

## Clientes de teste

O seed cria 50 clientes aleatórios e 4 com situações conhecidas, usados na avaliação do agente:

| E-mail | Situação | O agente deveria... |
|---|---|---|
| ana.duplicada@exemplo.com | Última fatura cobrada 2 vezes | Identificar a duplicidade e abrir chamado de estorno |
| bruno.recusado@exemplo.com | Cartão expirado, assinatura suspensa | Explicar o motivo e orientar a trocar o cartão |
| carla.cancelada@exemplo.com | Cobrada depois de cancelar | Identificar a cobrança indevida e abrir chamado |
| diego.emdia@exemplo.com | Tudo em dia | Confirmar que não há problema (sem inventar nada) |
