"""SQLite connection management, schema creation, and initial data."""

from pathlib import Path
import sqlite3


CATEGORIES = (
    ("Cafés Especiais", "Grãos selecionados e cafés preparados com cuidado."),
    ("Bebidas Geladas", "Bebidas refrescantes feitas na cafeteria."),
    ("Acompanhamentos", "Doces e salgados para acompanhar seu café."),
    ("Kits Gourmet", "Seleções especiais para presentear ou compartilhar."),
)

PRODUCTS = (
    (1, "Espresso da Casa", "Espresso encorpado com notas de chocolate.", 8.50, 24, "☕"),
    (1, "Cappuccino Artesanal", "Café, leite vaporizado e uma camada de espuma.", 14.00, 18, "🫖"),
    (1, "Coado V60", "Café especial preparado individualmente.", 12.00, 15, "🫘"),
    (2, "Cold Brew", "Café extraído a frio por 18 horas.", 16.00, 12, "🧊"),
    (2, "Frappé de Caramelo", "Bebida gelada de café com caramelo.", 19.50, 10, "🥤"),
    (3, "Pão de Queijo", "Porção com três pães de queijo artesanais.", 10.00, 20, "🧀"),
    (3, "Cookie de Chocolate", "Cookie macio com gotas de chocolate.", 9.00, 16, "🍪"),
    (4, "Kit Degustação", "Três cafés especiais em embalagens de 100 g.", 79.90, 8, "🎁"),
)


def get_db_connection(database_path):
    """Return a configured SQLite connection for the requested database."""
    path = Path(database_path)
    if str(database_path) != ":memory:":
        path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(str(database_path), timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 10000")
    return connection


def initialize_database(database_path):
    """Create the schema and insert starter data when the database is empty."""
    connection = get_db_connection(database_path)
    try:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS categorias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL UNIQUE CHECK (length(trim(nome)) >= 1),
                descricao TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS produtos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                categoria_id INTEGER NOT NULL,
                nome TEXT NOT NULL CHECK (length(trim(nome)) >= 3),
                descricao TEXT NOT NULL DEFAULT '',
                preco REAL NOT NULL CHECK (preco > 0),
                quantidade_estoque INTEGER NOT NULL DEFAULT 0
                    CHECK (quantidade_estoque >= 0),
                imagem_emoji TEXT NOT NULL DEFAULT '☕',
                data_criacao TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (categoria_id) REFERENCES categorias(id)
            );

            CREATE TABLE IF NOT EXISTS pedidos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cliente_nome TEXT NOT NULL,
                cliente_telefone TEXT NOT NULL,
                endereco_entrega TEXT NOT NULL,
                valor_total REAL NOT NULL CHECK (valor_total > 0),
                status TEXT NOT NULL DEFAULT 'confirmado'
                    CHECK (status IN ('confirmado', 'em_preparo', 'enviado', 'concluido', 'cancelado')),
                data_pedido TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS pedido_itens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pedido_id INTEGER NOT NULL,
                produto_id INTEGER,
                produto_nome TEXT NOT NULL,
                quantidade INTEGER NOT NULL CHECK (quantidade > 0),
                preco_unitario REAL NOT NULL CHECK (preco_unitario > 0),
                FOREIGN KEY (pedido_id) REFERENCES pedidos(id) ON DELETE CASCADE,
                FOREIGN KEY (produto_id) REFERENCES produtos(id) ON DELETE SET NULL
            );

            CREATE INDEX IF NOT EXISTS idx_produtos_categoria
                ON produtos(categoria_id);
            CREATE INDEX IF NOT EXISTS idx_pedidos_data
                ON pedidos(data_pedido);
            CREATE INDEX IF NOT EXISTS idx_pedido_itens_pedido
                ON pedido_itens(pedido_id);
            """
        )

        category_count = connection.execute(
            "SELECT COUNT(*) FROM categorias"
        ).fetchone()[0]
        if category_count == 0:
            with connection:
                connection.executemany(
                    "INSERT INTO categorias (nome, descricao) VALUES (?, ?)", CATEGORIES
                )
                connection.executemany(
                    """
                    INSERT INTO produtos
                        (categoria_id, nome, descricao, preco, quantidade_estoque, imagem_emoji)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    PRODUCTS,
                )
    finally:
        connection.close()
