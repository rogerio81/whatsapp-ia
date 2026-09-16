"""Popula um negócio + catálogo de teste, para simular o agente sem depender do
fluxo de onboarding nem de uma instância real do Evolution API.

Uso (dentro de backend/, com o venv ativado e DATABASE_URL apontando pro banco):
    python -m scripts.seed_demo

Cria a instância "loja-teste" — o mesmo nome usado no exemplo de curl do README.
Rodar de novo é seguro: não duplica produtos se já existirem.
"""

import asyncio
from decimal import Decimal

from sqlalchemy import select

from app.db import session_scope
from app.models import Business, BusinessStatus, Product, ProductVariant

INSTANCE_NAME = "loja-teste"


async def seed() -> None:
    async with session_scope() as db:
        stmt = select(Business).where(Business.evolution_instance_name == INSTANCE_NAME)
        business = (await db.execute(stmt)).scalar_one_or_none()

        if business is None:
            business = Business(
                name="Loja Teste",
                evolution_instance_name=INSTANCE_NAME,
                status=BusinessStatus.active,
                business_hours={"seg_sex": "9h-19h", "sab": "9h-13h"},
                delivery_info="Motoboy na região e Correios para o resto do Brasil.",
                payment_methods={"pix": True, "cartao": True, "dinheiro": True},
            )
            db.add(business)
            await db.flush()
            print(f"Business criado: {business.id} ({INSTANCE_NAME})")
        else:
            print(f"Business já existia: {business.id} ({INSTANCE_NAME})")

        has_products = (
            await db.execute(select(Product).where(Product.business_id == business.id))
        ).first()
        if has_products is not None:
            print("Catálogo já tem produtos — não vou duplicar. Nada a fazer.")
            await db.commit()
            return

        blusa = Product(
            business_id=business.id,
            name="Blusa preta básica",
            description="Blusa preta de algodão, corte reto",
            category="blusas",
        )
        db.add(blusa)
        await db.flush()
        db.add_all(
            [
                ProductVariant(product_id=blusa.id, sku="BLZ-P-P", size="P", color="preto", price=Decimal("89.90"), stock_qty=5),
                ProductVariant(product_id=blusa.id, sku="BLZ-P-M", size="M", color="preto", price=Decimal("89.90"), stock_qty=8),
                ProductVariant(product_id=blusa.id, sku="BLZ-P-G", size="G", color="preto", price=Decimal("89.90"), stock_qty=3),
            ]
        )

        calca = Product(
            business_id=business.id,
            name="Calça jeans skinny",
            description="Calça jeans skinny cintura alta",
            category="calças",
        )
        db.add(calca)
        await db.flush()
        db.add_all(
            [
                ProductVariant(product_id=calca.id, sku="CLC-JN-38", size="38", color="azul", price=Decimal("159.90"), stock_qty=4),
                ProductVariant(product_id=calca.id, sku="CLC-JN-40", size="40", color="azul", price=Decimal("159.90"), stock_qty=6),
            ]
        )

        await db.commit()
        print("Catálogo de teste criado: Blusa preta básica (P/M/G) e Calça jeans skinny (38/40).")


if __name__ == "__main__":
    asyncio.run(seed())
