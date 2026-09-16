# Vendedor IA

Um funcionário de IA que atende, vende e faz follow-up pelo WhatsApp do lojista — sem painel, sem planilha, sem treinamento.

> Este repositório saiu da fase de concepção: já há um backend inicial rodando (`backend/`), com o produto ainda em fase de validação.

## A ideia

Não é um CRM tradicional. É um "funcionário" de IA que trabalha dentro do WhatsApp de pequenos negócios (o caso de uso inicial é varejo de moda feminina).

O lojista não abre painel nenhum para operar — configura o negócio numa conversa (o que vende, horário, entrega, forma de pagamento) e a IA assume:

- **Atendimento** — responde dúvidas de preço, tamanho e disponibilidade com base no catálogo real da loja.
- **Venda guiada** — registra pedido, verifica estoque, calcula frete, envia cobrança, acompanha o pagamento e registra a venda.
- **Follow-up automático** — quando o cliente diz "vou pensar", o sistema não esquece: retoma o contato depois de um prazo configurável.
- **Oportunidades perdidas** (recurso âncora) — todo dia o lojista recebe um resumo priorizado de quem pediu orçamento e não comprou, quem sumiu e quem está no momento certo de comprar de novo, com uma ação de um toque para a IA cuidar disso.
- **Motor de recompra** (evolução) — a IA aprende o ciclo de recompra de cada negócio e sugere contato proativo quando um cliente está no ponto de comprar de novo.

## Documento de produto

O PRD completo (problema, público-alvo, funcionalidades do MVP, fluxo de venda, requisitos técnicos, métricas, modelo de negócio, riscos e roadmap) está publicado aqui:

**https://claude.ai/artifact/GVcz2s4LiuDoZM3buRpad5**

## Arquitetura técnica

Primeira versão do desenho técnico (stack, componentes, fluxo de mensagem, modelo de dados, decisões e pontos em aberto) está em [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Backend

Implementação inicial em Python (FastAPI + SQLAlchemy + Claude API) em [`backend/`](backend) — ver [`backend/README.md`](backend/README.md) para rodar local ou com Docker.

## Status

- [x] Ideia e proposta de valor definidas
- [x] PRD v0.1
- [ ] Validação com lojistas piloto
- [x] Arquitetura técnica (v0.1 — sujeita a revisão)
- [ ] MVP (backend inicial no ar, faltam gateway de pagamento real e teste com instância viva do WhatsApp)
