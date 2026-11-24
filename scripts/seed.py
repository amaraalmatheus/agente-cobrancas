"""Gera dados fictícios para o banco.

Rode a partir da pasta raiz do projeto:
    python -m scripts.seed

ATENÇÃO: apaga e recria todas as tabelas a cada execução.

Além dos clientes aleatórios, cria 4 clientes com situações conhecidas.
Eles serão usados nos testes do agente (dia 5), porque sabemos
exatamente qual deveria ser a resposta para cada um.
"""

import random
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from faker import Faker

from app.database import Base, SessionLocal, engine
from app.models import (
    Assinatura,
    Chamado,
    Cliente,
    Fatura,
    MetodoPagamento,
    Pagamento,
    Plano,
    StatusAssinatura,
    StatusChamado,
    StatusFatura,
    StatusPagamento,
)

# Semente fixa: toda vez que rodar, os dados gerados são os mesmos.
SEED = 42
N_CLIENTES = 50
HOJE = date.today()

random.seed(SEED)
fake = Faker("pt_BR")
Faker.seed(SEED)

PLANOS = [
    ("Básico", "1 tela, qualidade HD", Decimal("19.90")),
    ("Padrão", "2 telas, qualidade Full HD", Decimal("39.90")),
    ("Premium", "4 telas, qualidade 4K", Decimal("59.90")),
    ("Família", "6 perfis, 4 telas, 4K e downloads", Decimal("79.90")),
]

MOTIVOS_RECUSA = [
    "Saldo insuficiente",
    "Cartão expirado",
    "Transação negada pelo banco emissor",
    "Limite excedido",
]


# --- Funções auxiliares de data ---------------------------------------------

def primeiro_dia_do_mes(d: date) -> date:
    return d.replace(day=1)


def somar_meses(d: date, n: int) -> date:
    """Retorna o dia 1 do mês que está n meses depois de d."""
    total = d.month - 1 + n
    return date(d.year + total // 12, total % 12 + 1, 1)


def momento_no_dia(d: date) -> datetime:
    """Um horário aleatório (entre 6h e 22h) no dia d."""
    return datetime.combine(d, time(random.randint(6, 22), random.randint(0, 59)))


# --- Simulação de pagamentos ------------------------------------------------

def simular_pagamentos(fatura: Fatura, metodo: str, modo: str = "aleatorio") -> None:
    """Cria as tentativas de pagamento de uma fatura que já venceu.

    modo:
        "aleatorio" -> 85% paga de primeira, 10% paga na 2ª tentativa, 5% fica vencida
        "ok"        -> paga de primeira
        "recusado"  -> não paga (fica vencida)
    """
    if modo == "aleatorio":
        sorteio = random.random()
        modo = "ok" if sorteio < 0.85 else "retentativa" if sorteio < 0.95 else "recusado"

    dia = fatura.vencimento - timedelta(days=random.randint(0, 5))

    def tentativa(status: str, quando: date, motivo: str | None = None) -> None:
        fatura.pagamentos.append(
            Pagamento(
                valor=fatura.valor,
                metodo=metodo,
                status=status,
                motivo_recusa=motivo,
                criado_em=momento_no_dia(min(quando, HOJE)),
            )
        )

    # Pix e boleto não têm "recusa": se o cliente não paga, simplesmente não há pagamento.
    eh_cartao = metodo == MetodoPagamento.CARTAO

    if modo == "ok":
        tentativa(StatusPagamento.APROVADO, dia)
        fatura.status = StatusFatura.PAGA
    elif modo == "retentativa":
        if eh_cartao:
            tentativa(StatusPagamento.RECUSADO, dia, random.choice(MOTIVOS_RECUSA))
        tentativa(StatusPagamento.APROVADO, dia + timedelta(days=2))
        fatura.status = StatusFatura.PAGA
    else:  # recusado
        if eh_cartao:
            tentativa(StatusPagamento.RECUSADO, dia, random.choice(MOTIVOS_RECUSA))
        fatura.status = StatusFatura.VENCIDA


def gerar_faturas(
    assinatura: Assinatura,
    modo: str = "aleatorio",
    modo_ultima: str | None = None,
) -> list[Fatura]:
    """Cria uma fatura por mês, do início da assinatura até hoje (ou até o cancelamento).

    modo_ultima permite forçar o resultado da fatura vencida mais recente.
    """
    faturas: list[Fatura] = []
    mes = primeiro_dia_do_mes(assinatura.data_inicio)
    fim = assinatura.data_cancelamento or HOJE

    while mes <= fim:
        fatura = Fatura(
            mes_referencia=mes,
            valor=assinatura.plano.preco_mensal,
            vencimento=mes.replace(day=10),
            status=StatusFatura.PENDENTE,
        )
        assinatura.faturas.append(fatura)
        faturas.append(fatura)
        mes = somar_meses(mes, 1)

    vencidas_ate_hoje = [f for f in faturas if f.vencimento <= HOJE]
    for f in vencidas_ate_hoje:
        modo_desta = modo_ultima if (modo_ultima and f is vencidas_ate_hoje[-1]) else modo
        simular_pagamentos(f, assinatura.metodo_pagamento, modo_desta)
    # As faturas com vencimento no futuro continuam "pendente", sem pagamento.

    return faturas


def atualizar_status_assinatura(assinatura: Assinatura) -> None:
    """Cancelada se tem data de cancelamento; suspensa se a última fatura vencida não foi paga."""
    if assinatura.data_cancelamento:
        assinatura.status = StatusAssinatura.CANCELADA
        return
    ja_venceram = [f for f in assinatura.faturas if f.vencimento <= HOJE]
    if ja_venceram and ja_venceram[-1].status == StatusFatura.VENCIDA:
        assinatura.status = StatusAssinatura.SUSPENSA
    else:
        assinatura.status = StatusAssinatura.ATIVA


# --- Criação de clientes ----------------------------------------------------

def novo_cliente(nome: str | None = None, email: str | None = None, criado_em: date | None = None) -> Cliente:
    criado_em = criado_em or fake.date_between(start_date="-18M", end_date="-1M")
    return Cliente(
        nome=nome or fake.name(),
        email=email or fake.unique.email(),
        cpf=fake.unique.cpf(),
        telefone=fake.phone_number(),
        criado_em=momento_no_dia(criado_em),
    )


def nova_assinatura(cliente: Cliente, plano: Plano, metodo: str, inicio: date) -> Assinatura:
    assinatura = Assinatura(
        plano=plano,
        metodo_pagamento=metodo,
        status=StatusAssinatura.ATIVA,
        data_inicio=inicio,
    )
    cliente.assinaturas.append(assinatura)
    return assinatura


def criar_clientes_aleatorios(planos: list[Plano]) -> list[Cliente]:
    clientes = []
    for _ in range(N_CLIENTES):
        cliente = novo_cliente()
        inicio_cliente = cliente.criado_em.date()

        # 80% têm 1 assinatura, 20% têm 2 (de planos diferentes)
        qtd = 2 if random.random() < 0.2 else 1
        for plano in random.sample(planos, qtd):
            metodo = random.choices(
                [MetodoPagamento.CARTAO, MetodoPagamento.PIX, MetodoPagamento.BOLETO],
                weights=[60, 30, 10],
            )[0]
            inicio = inicio_cliente + timedelta(days=random.randint(0, 20))
            assinatura = nova_assinatura(cliente, plano, metodo, min(inicio, HOJE))

            # ~15% cancelaram em algum momento
            dias_de_vida = (HOJE - assinatura.data_inicio).days
            if random.random() < 0.15 and dias_de_vida > 60:
                assinatura.data_cancelamento = assinatura.data_inicio + timedelta(
                    days=random.randint(31, dias_de_vida)
                )

            gerar_faturas(assinatura)
            atualizar_status_assinatura(assinatura)

        clientes.append(cliente)
    return clientes


def criar_cenarios_de_teste(planos: dict[str, Plano]) -> list[Cliente]:
    """Clientes com problemas conhecidos, para testar o agente depois."""
    inicio = somar_meses(HOJE, -5).replace(day=5)
    clientes = []

    # 1) Cobrança em duplicidade: a última fatura paga tem DOIS pagamentos aprovados.
    ana = novo_cliente("Ana Souza", "ana.duplicada@exemplo.com", inicio - timedelta(days=3))
    assinatura = nova_assinatura(ana, planos["Padrão"], MetodoPagamento.CARTAO, inicio)
    gerar_faturas(assinatura, modo="ok")
    ultima_paga = [f for f in assinatura.faturas if f.status == StatusFatura.PAGA][-1]
    ultima_paga.pagamentos.append(
        Pagamento(
            valor=ultima_paga.valor,
            metodo=MetodoPagamento.CARTAO,
            status=StatusPagamento.APROVADO,
            criado_em=ultima_paga.pagamentos[0].criado_em + timedelta(minutes=3),
        )
    )
    atualizar_status_assinatura(assinatura)
    clientes.append(ana)

    # 2) Pagamento recusado: cartão expirado na última fatura -> assinatura suspensa.
    bruno = novo_cliente("Bruno Lima", "bruno.recusado@exemplo.com", inicio - timedelta(days=3))
    assinatura = nova_assinatura(bruno, planos["Premium"], MetodoPagamento.CARTAO, inicio)
    gerar_faturas(assinatura, modo="ok", modo_ultima="recusado")
    ultima = [f for f in assinatura.faturas if f.vencimento <= HOJE][-1]
    ultima.pagamentos[-1].motivo_recusa = "Cartão expirado"
    atualizar_status_assinatura(assinatura)
    clientes.append(bruno)

    # 3) Cobrada depois de cancelar: cancelou no mês passado, mas foi cobrada este mês.
    carla = novo_cliente("Carla Mendes", "carla.cancelada@exemplo.com", inicio - timedelta(days=3))
    assinatura = nova_assinatura(carla, planos["Família"], MetodoPagamento.CARTAO, inicio)
    assinatura.data_cancelamento = somar_meses(HOJE, -1).replace(day=15)
    gerar_faturas(assinatura, modo="ok")
    mes_indevido = somar_meses(assinatura.data_cancelamento, 1)
    fatura_indevida = Fatura(
        mes_referencia=mes_indevido,
        valor=assinatura.plano.preco_mensal,
        vencimento=mes_indevido.replace(day=10),
        status=StatusFatura.PAGA,
    )
    fatura_indevida.pagamentos.append(
        Pagamento(
            valor=fatura_indevida.valor,
            metodo=MetodoPagamento.CARTAO,
            status=StatusPagamento.APROVADO,
            criado_em=momento_no_dia(min(fatura_indevida.vencimento, HOJE)),
        )
    )
    assinatura.faturas.append(fatura_indevida)
    atualizar_status_assinatura(assinatura)
    clientes.append(carla)

    # 4) Tudo em dia (caso de controle: o agente NÃO deve inventar problema).
    diego = novo_cliente("Diego Rocha", "diego.emdia@exemplo.com", inicio - timedelta(days=3))
    assinatura = nova_assinatura(diego, planos["Básico"], MetodoPagamento.PIX, inicio)
    gerar_faturas(assinatura, modo="ok")
    atualizar_status_assinatura(assinatura)
    clientes.append(diego)

    return clientes


def criar_chamados_antigos(clientes: list[Cliente], quantidade: int = 10) -> None:
    assuntos = [
        "Dúvida sobre valor da fatura",
        "Alterar forma de pagamento",
        "Não consigo acessar minha conta",
        "Quero mudar de plano",
        "Segunda via de boleto",
    ]
    for cliente in random.sample(clientes, quantidade):
        dia = fake.date_between(start_date=cliente.criado_em.date(), end_date=HOJE)
        cliente.chamados.append(
            Chamado(
                assunto=random.choice(assuntos),
                descricao=fake.paragraph(nb_sentences=2),
                status=StatusChamado.RESOLVIDO,
                criado_em=momento_no_dia(dia),
            )
        )


def main() -> None:
    print("Recriando tabelas...")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    with SessionLocal() as db:
        planos = [Plano(nome=n, descricao=d, preco_mensal=p) for n, d, p in PLANOS]
        db.add_all(planos)

        aleatorios = criar_clientes_aleatorios(planos)
        cenarios = criar_cenarios_de_teste({p.nome: p for p in planos})
        criar_chamados_antigos(aleatorios)

        db.add_all(aleatorios + cenarios)
        db.commit()

        print("Pronto!")
        for modelo in (Plano, Cliente, Assinatura, Fatura, Pagamento, Chamado):
            print(f"  {modelo.__tablename__:<12} {db.query(modelo).count()}")
        print("\nClientes de teste:")
        for c in cenarios:
            print(f"  {c.email}")


if __name__ == "__main__":
    main()
