# Café Aurora - E-Commerce de Cafeteria Gourmet

Aplicação web completa para uma cafeteria gourmet com vitrine virtual, carrinho de compras, checkout com entrega, painel administrativo e gestão de estoque.

## Visão geral

Este projeto foi desenvolvido com Flask, SQLite e arquitetura MVC, seguindo requisitos de negócio e regras de qualidade, segurança e validação do PIT-I e PIT-II. A aplicação oferece:

- Vitrine virtual com categorias e produtos dinâmicos
- Carrinho de compras e checkout com dados de entrega
- Controle de estoque no momento da confirmação do pedido
- Painel do gestor com indicadores operacionais em tempo real
- API REST padronizada com respostas em JSON
- Interface única com navegação fluida sem recarga

## Stack

- Python 3
- Flask
- SQLite3
- Tailwind CSS CDN
- JavaScript Vanilla ES6+
- python-dotenv

## Estrutura do projeto

```text
cafeteria-gourmet/
├── app.py
├── database.py
├── requirements.txt
├── .env
├── controllers/
│   └── cafeteria_controller.py
├── models/
│   └── cafeteria_model.py
├── utils/
│   └── api_response.py
├── templates/
│   └── index.html
├── static/
│   └── js/
│       └── main.js
└── README.md
```

## Regras de negócio implementadas

- Validação de preço maior que zero
- Validação de nome de produto com mínimo de 3 caracteres
- Tratamento de estoque negativo e valores inválidos
- Bloqueio de produtos esgotados durante o pedido
- Baixa automática de estoque ao confirmar pedido
- Padronização de respostas da API com estrutura:

```json
{
  "success": true,
  "message": "Mensagem",
  "data": {},
  "timestamp": "2026-10-15T12:00:00+00:00"
}
```

- Tratamento global de erros para 404, 405, 413 e 500
- Renderização segura de textos no front-end com DOM nativo (`textContent`)
- Notificações visuais com Toastify
- Modal de confirmação antes de excluir produto

## Banco de dados

A criação automática do banco e das tabelas acontece em `database.py`, com as seguintes entidades:

- `categorias`
- `produtos`
- `pedidos`
- `pedido_itens`

Dados iniciais são inseridos automaticamente para popular a vitrine do sistema.

## Configuração

O arquivo `.env` contém as configurações do ambiente:

```env
PORT=5000
FLASK_DEBUG=false
DATABASE_PATH=instance/cafeteria.db
```

## Como executar

1. Instale as dependências:

```bash
pip install -r requirements.txt
```

2. Execute a aplicação:

```bash
python app.py
```

3. Acesse no navegador:

```text
http://localhost:5000
```

## Endpoints principais

### Categorias

- `GET /api/categorias`

### Produtos

- `GET /api/produtos`
- `POST /api/produtos`
- `PUT /api/produtos/<id>`
- `DELETE /api/produtos/<id>`

### Pedidos

- `POST /api/pedidos`
- `GET /api/pedidos`

### Dashboard

- `GET /api/dashboard`

## Observações de segurança

- Todas as respostas HTTP de erro seguem o mesmo padrão JSON da API
- O front-end evita uso de `innerHTML` para conteúdo que venha de dados de usuário
- Validações estritas são aplicadas também no back-end para garantir integridade da aplicação

## Autor

Projeto desenvolvido para a cafeteria gourmet com foco em usabilidade, arquitetura limpa e operação digital.
