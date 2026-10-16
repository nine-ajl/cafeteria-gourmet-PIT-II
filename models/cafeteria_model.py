"""Data-access and transactional operations for the cafeteria domain."""

import math
import sqlite3

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database import get_db_connection


class CafeteriaModel:
    """Encapsulate persistence operations used by the HTTP controller."""

    def __init__(self, database_path):
        self.database_path = database_path

    def list_categories(self):
        connection = get_db_connection(self.database_path)
        try:
            rows = connection.execute(
                "SELECT id, nome, descricao FROM categorias ORDER BY id"
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            connection.close()

    def category_exists(self, category_id):
        connection = get_db_connection(self.database_path)
        try:
            return (
                connection.execute(
                    "SELECT 1 FROM categorias WHERE id = ?", (category_id,)
                ).fetchone()
                is not None
            )
        finally:
            connection.close()

    def list_products(self, category_id=None):
        query = """
            SELECT p.id, p.categoria_id, c.nome AS categoria_nome, p.nome,
                   p.descricao, p.preco, p.quantidade_estoque, p.imagem_emoji,
                   p.data_criacao
            FROM produtos p
            JOIN categorias c ON c.id = p.categoria_id
        """
        parameters = ()
        if category_id is not None:
            query += " WHERE p.categoria_id = ?"
            parameters = (category_id,)
        query += " ORDER BY p.id"

        connection = get_db_connection(self.database_path)
        try:
            rows = connection.execute(query, parameters).fetchall()
            return [dict(row) for row in rows]
        finally:
            connection.close()

    def create_product(self, product):
        connection = get_db_connection(self.database_path)
        try:
            with connection:
                cursor = connection.execute(
                    """
                    INSERT INTO produtos
                        (categoria_id, nome, descricao, preco, quantidade_estoque, imagem_emoji)
                    VALUES (:categoria_id, :nome, :descricao, :preco, :quantidade_estoque, :imagem_emoji)
                    """,
                    product,
                )
                product_id = cursor.lastrowid
            return self._get_product(connection, product_id)
        finally:
            connection.close()

    def update_product(self, product_id, product):
        connection = get_db_connection(self.database_path)
        try:
            with connection:
                cursor = connection.execute(
                    """
                    UPDATE produtos SET categoria_id = :categoria_id, nome = :nome,
                        descricao = :descricao, preco = :preco,
                        quantidade_estoque = :quantidade_estoque,
                        imagem_emoji = :imagem_emoji
                    WHERE id = :id
                    """,
                    {**product, "id": product_id},
                )
            if cursor.rowcount == 0:
                return None
            return self._get_product(connection, product_id)
        finally:
            connection.close()

    def delete_product(self, product_id):
        connection = get_db_connection(self.database_path)
        try:
            with connection:
                cursor = connection.execute(
                    "DELETE FROM produtos WHERE id = ?", (product_id,)
                )
            return cursor.rowcount > 0
        finally:
            connection.close()

    def create_order(self, customer_name, customer_phone, delivery_address, quantities):
        connection = get_db_connection(self.database_path)
        try:
            connection.execute("BEGIN IMMEDIATE")
            order_lines = []
            total = 0.0
            for product_id, quantity in quantities.items():
                product = connection.execute(
                    """
                    SELECT id, nome, preco, quantidade_estoque
                    FROM produtos WHERE id = ?
                    """,
                    (product_id,),
                ).fetchone()
                if product is None:
                    raise ValueError("Um dos produtos do pedido não existe.")
                if product["quantidade_estoque"] == 0:
                    raise ValueError(f'{product["nome"]} está esgotado.')
                if product["quantidade_estoque"] < quantity:
                    raise ValueError(
                        f'Estoque insuficiente para {product["nome"]}. '
                        f'Disponível: {product["quantidade_estoque"]}.'
                    )
                line_total = product["preco"] * quantity
                if not math.isfinite(line_total) or not math.isfinite(total + line_total):
                    raise ValueError("O valor total do pedido excede o limite permitido.")
                total += line_total
                order_lines.append((product, quantity))

            cursor = connection.execute(
                """
                INSERT INTO pedidos
                    (cliente_nome, cliente_telefone, endereco_entrega, valor_total, status)
                VALUES (?, ?, ?, ?, 'confirmado')
                """,
                (customer_name, customer_phone, delivery_address, total),
            )
            order_id = cursor.lastrowid
            for product, quantity in order_lines:
                update = connection.execute(
                    """
                    UPDATE produtos SET quantidade_estoque = quantidade_estoque - ?
                    WHERE id = ? AND quantidade_estoque >= ?
                    """,
                    (quantity, product["id"], quantity),
                )
                if update.rowcount != 1:
                    raise ValueError(f'Estoque insuficiente para {product["nome"]}.')
                connection.execute(
                    """
                    INSERT INTO pedido_itens
                        (pedido_id, produto_id, produto_nome, quantidade, preco_unitario)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (order_id, product["id"], product["nome"], quantity, product["preco"]),
                )

            connection.commit()
            return dict(
                connection.execute(
                    """
                    SELECT id, cliente_nome, cliente_telefone, endereco_entrega,
                           valor_total, status, data_pedido
                    FROM pedidos WHERE id = ?
                    """,
                    (order_id,),
                ).fetchone()
            )
        except ValueError:
            connection.rollback()
            raise
        except sqlite3.Error:
            connection.rollback()
            raise
        finally:
            connection.close()

    def list_orders(self):
        connection = get_db_connection(self.database_path)
        try:
            orders = connection.execute(
                """
                SELECT id, cliente_nome, cliente_telefone, endereco_entrega,
                       valor_total, status, data_pedido
                FROM pedidos ORDER BY data_pedido DESC, id DESC
                """
            ).fetchall()
            result = []
            for order in orders:
                items = connection.execute(
                    """
                    SELECT produto_nome, quantidade, preco_unitario
                    FROM pedido_itens WHERE pedido_id = ? ORDER BY id
                    """,
                    (order["id"],),
                ).fetchall()
                result.append({**dict(order), "itens": [dict(item) for item in items]})
            return result
        finally:
            connection.close()

    def get_dashboard(self):
        connection = get_db_connection(self.database_path)
        try:
            row = connection.execute(
                """
                SELECT
                    COALESCE(SUM(CASE WHEN status != 'cancelado' THEN valor_total ELSE 0 END), 0)
                        AS faturamento_total,
                    COUNT(CASE WHEN status != 'cancelado' THEN 1 END) AS total_pedidos,
                    COALESCE(
                        (SELECT SUM(preco * quantidade_estoque) FROM produtos), 0
                    ) AS valor_estoque,
                    COALESCE(
                        (SELECT COUNT(*) FROM produtos WHERE quantidade_estoque = 0), 0
                    ) AS itens_esgotados
                FROM pedidos
                """
            ).fetchone()
            return dict(row)
        finally:
            connection.close()

    @staticmethod
    def _get_product(connection, product_id):
        row = connection.execute(
            """
            SELECT p.id, p.categoria_id, c.nome AS categoria_nome, p.nome,
                   p.descricao, p.preco, p.quantidade_estoque, p.imagem_emoji,
                   p.data_criacao
            FROM produtos p JOIN categorias c ON c.id = p.categoria_id
            WHERE p.id = ?
            """,
            (product_id,),
        ).fetchone()
        return dict(row) if row is not None else None
