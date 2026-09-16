"""Resolve o tenant (lojista) e o cliente a partir do payload de um webhook.

Isolamento por business_id é a regra desde a primeira query — ver ARCHITECTURE.md.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Business, BusinessStatus, Conversation, Customer


async def get_or_create_business(db: AsyncSession, evolution_instance_name: str) -> Business:
    stmt = select(Business).where(Business.evolution_instance_name == evolution_instance_name)
    business = (await db.execute(stmt)).scalar_one_or_none()
    if business is not None:
        return business

    # Instância nova falando com o backend pela primeira vez — cria em modo onboarding.
    # O fluxo de onboarding conversacional (PRD seção 04) preenche o resto depois.
    business = Business(
        name=evolution_instance_name,
        evolution_instance_name=evolution_instance_name,
        status=BusinessStatus.onboarding,
    )
    db.add(business)
    await db.flush()
    return business


async def get_or_create_customer(db: AsyncSession, business: Business, wa_id: str, name: str = "") -> Customer:
    stmt = select(Customer).where(Customer.business_id == business.id, Customer.wa_id == wa_id)
    customer = (await db.execute(stmt)).scalar_one_or_none()
    if customer is not None:
        return customer

    customer = Customer(business_id=business.id, wa_id=wa_id, name=name)
    db.add(customer)
    await db.flush()
    return customer


async def get_or_create_active_conversation(db: AsyncSession, business: Business, customer: Customer) -> Conversation:
    stmt = (
        select(Conversation)
        .where(Conversation.business_id == business.id, Conversation.customer_id == customer.id)
        .order_by(Conversation.created_at.desc())
    )
    conversation = (await db.execute(stmt)).scalars().first()
    if conversation is not None:
        return conversation

    conversation = Conversation(business_id=business.id, customer_id=customer.id)
    db.add(conversation)
    await db.flush()
    return conversation
