"""Tools do agente de vendas.

Regra central do produto (PRD seção 08 / ARCHITECTURE.md): o agente nunca responde
preço ou estoque de memória — toda informação de catálogo passa por `lookup_product`
ou `check_stock`, que leem direto do Postgres. O `system_prompt` reforça essa regra;
estas funções são o que a garante de fato.
"""

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Awaitable, Callable, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Business,
    Conversation,
    Customer,
    Followup,
    Opportunity,
    OpportunityStatus,
    Order,
    OrderItem,
    OrderStatus,
    Payment,
    Product,
    ProductVariant,
)


@dataclass
class ToolContext:
    db: AsyncSession
    business: Business
    customer: Customer
    conversation: Conversation
    # Pool de conexão do arq, usado para agendar o job de follow-up. Opcional para
    # facilitar testes de tool isolados sem precisar de um Redis rodando.
    enqueue_followup: Optional[Callable[[uuid.UUID, datetime], Awaitable[None]]] = None


TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "lookup_product",
        "description": (
            "Busca produtos no catálogo do lojista por nome ou descrição. Use sempre que o "
            "cliente perguntar sobre um produto — nunca responda preço ou estoque sem chamar essa tool."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Termo de busca, ex.: 'blusa preta'"}},
            "required": ["query"],
            "additionalProperties": False,
        },
    },
    {
        "name": "check_stock",
        "description": "Confirma o estoque exato de uma variação de produto específica antes de reservar.",
        "input_schema": {
            "type": "object",
            "properties": {"product_variant_id": {"type": "string"}},
            "required": ["product_variant_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "calculate_shipping",
        "description": "Calcula o custo estimado de entrega para um endereço.",
        "input_schema": {
            "type": "object",
            "properties": {"address": {"type": "string"}},
            "required": ["address"],
            "additionalProperties": False,
        },
    },
    {
        "name": "create_order",
        "description": "Registra um pedido com os itens escolhidos pelo cliente, já com o frete calculado.",
        "input_schema": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "product_variant_id": {"type": "string"},
                            "quantity": {"type": "integer", "minimum": 1},
                        },
                        "required": ["product_variant_id", "quantity"],
                        "additionalProperties": False,
                    },
                },
                "shipping_address": {"type": "string"},
                "shipping_cost": {"type": "number"},
            },
            "required": ["items", "shipping_address", "shipping_cost"],
            "additionalProperties": False,
        },
    },
    {
        "name": "generate_payment_link",
        "description": "Gera a cobrança (Pix) de um pedido já registrado e retorna o link/código para o cliente.",
        "input_schema": {
            "type": "object",
            "properties": {"order_id": {"type": "string"}},
            "required": ["order_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "schedule_followup",
        "description": (
            "Agenda um retorno de contato quando o cliente sinalizar que vai pensar/decidir depois. "
            "Não encerra a conversa — apenas garante que a IA retome no prazo certo."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "due_in_hours": {"type": "number", "description": "Em quantas horas retomar o contato"},
                "context": {"type": "string", "description": "O que lembrar ao retomar (produto, tamanho, dúvida)"},
            },
            "required": ["due_in_hours", "context"],
            "additionalProperties": False,
        },
    },
    {
        "name": "mark_opportunity",
        "description": (
            "Classifica a conversa atual como uma oportunidade para o resumo matinal do lojista. "
            "Use quoted_no_purchase quando o cliente pediu preço/orçamento e não comprou, vanished quando "
            "demonstrou interesse claro e parou de responder, repurchase_window quando parece o momento de "
            "comprar de novo."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["quoted_no_purchase", "vanished", "repurchase_window"],
                },
                "reason": {"type": "string"},
            },
            "required": ["status", "reason"],
            "additionalProperties": False,
        },
    },
]


def _variant_dict(variant: ProductVariant, product_name: str) -> dict[str, Any]:
    return {
        "product_variant_id": str(variant.id),
        "product_name": product_name,
        "size": variant.size,
        "color": variant.color,
        "price": float(variant.price),
        "stock_qty": variant.stock_qty,
    }


async def lookup_product(ctx: ToolContext, query: str) -> str:
    stmt = (
        select(ProductVariant, Product)
        .join(Product, ProductVariant.product_id == Product.id)
        .where(Product.business_id == ctx.business.id)
        .where(Product.name.ilike(f"%{query}%") | Product.description.ilike(f"%{query}%"))
        .limit(5)
    )
    rows = (await ctx.db.execute(stmt)).all()
    if not rows:
        return json.dumps({"matches": [], "note": "Nenhum produto encontrado com esse termo no catálogo."})
    matches = [_variant_dict(variant, product.name) for variant, product in rows]
    return json.dumps({"matches": matches})


async def check_stock(ctx: ToolContext, product_variant_id: str) -> str:
    variant = await ctx.db.get(ProductVariant, uuid.UUID(product_variant_id))
    if variant is None:
        return json.dumps({"error": "product_variant_id não encontrado"})
    return json.dumps({"product_variant_id": product_variant_id, "stock_qty": variant.stock_qty, "price": float(variant.price)})


async def calculate_shipping(ctx: ToolContext, address: str) -> str:
    # MVP: regra fixa a partir do texto livre de `delivery_info` cadastrado no onboarding.
    # TODO: integrar cálculo real (Correios/motoboy) quando o gateway logístico for escolhido.
    delivery_info = (ctx.business.delivery_info or "").lower()
    if "motoboy" in delivery_info:
        cost = 12.0
    else:
        cost = 25.0
    return json.dumps(
        {
            "address": address,
            "shipping_cost": cost,
            "note": "Estimativa fixa (MVP) baseada na config de entrega do lojista — não é cálculo real de frete.",
        }
    )


async def create_order(
    ctx: ToolContext, items: list[dict[str, Any]], shipping_address: str, shipping_cost: float
) -> str:
    total = Decimal(str(shipping_cost))
    order_items: list[OrderItem] = []

    for item in items:
        variant = await ctx.db.get(ProductVariant, uuid.UUID(item["product_variant_id"]))
        if variant is None:
            return json.dumps({"error": f"product_variant_id {item['product_variant_id']} não encontrado"})
        quantity = int(item["quantity"])
        if variant.stock_qty < quantity:
            return json.dumps(
                {"error": f"Estoque insuficiente para {variant.id}: disponível {variant.stock_qty}, pedido {quantity}"}
            )
        total += variant.price * quantity
        order_items.append(OrderItem(product_variant_id=variant.id, quantity=quantity, unit_price=variant.price))
        variant.stock_qty -= quantity

    order = Order(
        business_id=ctx.business.id,
        customer_id=ctx.customer.id,
        status=OrderStatus.pending,
        shipping_address=shipping_address,
        shipping_cost=Decimal(str(shipping_cost)),
        total_amount=total,
    )
    ctx.db.add(order)
    await ctx.db.flush()  # popula order.id

    for order_item in order_items:
        order_item.order_id = order.id
        ctx.db.add(order_item)

    await ctx.db.flush()
    return json.dumps({"order_id": str(order.id), "total_amount": float(total), "status": order.status.value})


async def generate_payment_link(ctx: ToolContext, order_id: str) -> str:
    order = await ctx.db.get(Order, uuid.UUID(order_id))
    if order is None:
        return json.dumps({"error": "order_id não encontrado"})

    # MVP: stub — sem gateway real integrado ainda (decisão em aberto, ver ARCHITECTURE.md).
    # A confirmação de pagamento só pode vir de um webhook real de gateway; este link não confirma nada sozinho.
    payment = Payment(order_id=order.id, provider="stub", amount=order.total_amount)
    ctx.db.add(payment)
    order.status = OrderStatus.awaiting_payment
    await ctx.db.flush()

    fake_pix_code = f"00020126PIXSTUB{str(payment.id).replace('-', '')[:20]}"
    return json.dumps(
        {
            "payment_id": str(payment.id),
            "pix_copia_e_cola": fake_pix_code,
            "amount": float(order.total_amount),
            "note": "Stub de pagamento — substituir por gateway real antes de ir a produção.",
        }
    )


async def schedule_followup(ctx: ToolContext, due_in_hours: float, context: str) -> str:
    due_at = datetime.now(timezone.utc) + timedelta(hours=due_in_hours)
    followup = Followup(
        business_id=ctx.business.id,
        customer_id=ctx.customer.id,
        conversation_id=ctx.conversation.id,
        due_at=due_at,
        context=context,
    )
    ctx.db.add(followup)
    await ctx.db.flush()

    if ctx.enqueue_followup is not None:
        await ctx.enqueue_followup(followup.id, due_at)

    return json.dumps({"followup_id": str(followup.id), "due_at": due_at.isoformat()})


async def mark_opportunity(ctx: ToolContext, status: str, reason: str) -> str:
    opportunity = Opportunity(
        business_id=ctx.business.id,
        customer_id=ctx.customer.id,
        status=OpportunityStatus(status),
        reason=reason,
    )
    ctx.db.add(opportunity)
    await ctx.db.flush()
    return json.dumps({"opportunity_id": str(opportunity.id), "status": status})


TOOL_HANDLERS: dict[str, Callable[..., Awaitable[str]]] = {
    "lookup_product": lookup_product,
    "check_stock": check_stock,
    "calculate_shipping": calculate_shipping,
    "create_order": create_order,
    "generate_payment_link": generate_payment_link,
    "schedule_followup": schedule_followup,
    "mark_opportunity": mark_opportunity,
}
