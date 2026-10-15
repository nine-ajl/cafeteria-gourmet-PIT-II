"""REST endpoints and business rules for the coffee shop."""

import math
import sys

# pyright: reportMissingImports=false
from flask import Blueprint, current_app, request

from models.cafeteria_model import CafeteriaModel
from utils.api_response import api_response


cafeteria_api = Blueprint("cafeteria_api", __name__, url_prefix="/api")
MAX_SQLITE_INTEGER = 9223372036854775807


class ValidationError(ValueError):
    """Raised when a request does not satisfy the business rules."""


def _model():
    return CafeteriaModel(current_app.config["DATABASE_PATH"])


def _required_text(payload, field, label, minimum=1, maximum=500):
    value = payload.get(field)
    if not isinstance(value, str):
        raise ValidationError(f"O campo {label} é obrigatório.")
    value = value.strip()
    if len(value) < minimum:
        raise ValidationError(f"{label} deve ter no mínimo {minimum} caracteres.")
    if len(value) > maximum:
        raise ValidationError(f"{label} deve ter no máximo {maximum} caracteres.")
    return value


def _positive_id(value, label):
    if isinstance(value, bool):
        raise ValidationError(f"{label} inválido.")
    try:
        parsed = int(value)
    except (TypeError, ValueError, OverflowError):
        raise ValidationError(f"{label} inválido.") from None
    if parsed <= 0 or str(parsed) != str(value).strip():
        raise ValidationError(f"{label} inválido.")
    return parsed


def _product_payload(payload):
    if not isinstance(payload, dict):
        raise ValidationError("O corpo da requisição deve ser um objeto JSON.")

    name = _required_text(payload, "nome", "Nome do produto", minimum=3, maximum=120)
    description = payload.get("descricao", "")
    if not isinstance(description, str) or len(description) > 1000:
        raise ValidationError("A descrição deve ser um texto de até 1000 caracteres.")

    raw_price = payload.get("preco")
    if raw_price is None or isinstance(raw_price, bool):
        raise ValidationError("O preço deve ser um número válido maior que zero.")
    try:
        price = float(raw_price)
    except (TypeError, ValueError, OverflowError):
        raise ValidationError("O preço deve ser um número válido maior que zero.") from None
    if not math.isfinite(price) or price <= 0 or price > sys.float_info.max:
        raise ValidationError("O preço deve ser um número válido maior que zero.")

    raw_stock = payload.get("quantidade_estoque")
    if raw_stock is None or isinstance(raw_stock, bool):
        raise ValidationError("O estoque deve ser um número inteiro não negativo.")
    try:
        stock = int(raw_stock)
    except (TypeError, ValueError, OverflowError):
        raise ValidationError("O estoque deve ser um número inteiro não negativo.") from None
    if str(stock) != str(raw_stock).strip() or stock < 0 or stock > MAX_SQLITE_INTEGER:
        raise ValidationError("O estoque deve ser um número inteiro não negativo válido.")

    category_id = _positive_id(payload.get("categoria_id"), "Categoria")
    emoji = payload.get("imagem_emoji", "☕")
    if not isinstance(emoji, str) or not emoji.strip() or len(emoji) > 16:
        raise ValidationError("Informe um emoji válido para o produto.")

    return {
        "categoria_id": category_id,
        "nome": name,
        "descricao": description.strip(),
        "preco": price,
        "quantidade_estoque": stock,
        "imagem_emoji": emoji.strip(),
    }


def _json_body():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise ValidationError("Envie os dados em formato JSON.")
    return payload


def _validation_error(error):
    return api_response(False, str(error), None, 400)


@cafeteria_api.get("/categorias")
def list_categories():
    return api_response(True, "Categorias carregadas.", _model().list_categories())


@cafeteria_api.get("/produtos")
def list_products():
    category_id = request.args.get("categoria_id")
    parsed_category_id = None
    if category_id is not None:
        try:
            parsed_category_id = _positive_id(category_id, "Categoria")
        except ValidationError as error:
            return _validation_error(error)
    return api_response(
        True, "Produtos carregados.", _model().list_products(parsed_category_id)
    )


@cafeteria_api.post("/produtos")
def create_product():
    try:
        product = _product_payload(_json_body())
        model = _model()
        if not model.category_exists(product["categoria_id"]):
            return api_response(False, "A categoria informada não existe.", None, 400)
        created = model.create_product(product)
        return api_response(True, "Produto cadastrado.", created, 201)
    except (ValidationError, ValueError) as error:
        return _validation_error(error)


@cafeteria_api.put("/produtos/<int:product_id>")
def update_product(product_id):
    try:
        product = _product_payload(_json_body())
        model = _model()
        if not model.category_exists(product["categoria_id"]):
            return api_response(False, "A categoria informada não existe.", None, 400)
        updated = model.update_product(product_id, product)
        if updated is None:
            return api_response(False, "Produto não encontrado.", None, 404)
        return api_response(True, "Produto atualizado.", updated)
    except (ValidationError, ValueError) as error:
        return _validation_error(error)


@cafeteria_api.delete("/produtos/<int:product_id>")
def delete_product(product_id):
    if not _model().delete_product(product_id):
        return api_response(False, "Produto não encontrado.", None, 404)
    return api_response(True, "Produto excluído.", {"id": product_id})


@cafeteria_api.post("/pedidos")
def create_order():
    try:
        payload = _json_body()
        customer_name = _required_text(payload, "cliente_nome", "Nome", 2, 120)
        customer_phone = _required_text(payload, "cliente_telefone", "Telefone", 8, 30)
        delivery_address = _required_text(
            payload, "endereco_entrega", "Endereço de entrega", 8, 300
        )
        raw_items = payload.get("itens")
        if not isinstance(raw_items, list) or not raw_items:
            raise ValidationError("O pedido deve conter ao menos um produto.")

        quantities = {}
        for item in raw_items:
            if not isinstance(item, dict):
                raise ValidationError("Há um item inválido no pedido.")
            product_id = _positive_id(item.get("produto_id"), "Produto")
            raw_quantity = item.get("quantidade")
            if raw_quantity is None or isinstance(raw_quantity, bool):
                raise ValidationError("A quantidade de cada item deve ser um inteiro positivo.")
            try:
                quantity = int(raw_quantity)
            except (TypeError, ValueError, OverflowError):
                raise ValidationError(
                    "A quantidade de cada item deve ser um inteiro positivo."
                ) from None
            if str(quantity) != str(raw_quantity).strip() or quantity <= 0:
                raise ValidationError("A quantidade de cada item deve ser um inteiro positivo.")
            quantities[product_id] = quantities.get(product_id, 0) + quantity
            if quantities[product_id] > MAX_SQLITE_INTEGER:
                raise ValidationError("A quantidade solicitada é muito grande.")

        order = _model().create_order(
            customer_name, customer_phone, delivery_address, quantities
        )
        return api_response(True, "Pedido confirmado com sucesso.", order, 201)
    except (ValidationError, ValueError) as error:
        return _validation_error(error)


@cafeteria_api.get("/pedidos")
def list_orders():
    return api_response(True, "Pedidos carregados.", _model().list_orders())


@cafeteria_api.get("/dashboard")
def get_dashboard():
    return api_response(True, "Indicadores carregados.", _model().get_dashboard())
