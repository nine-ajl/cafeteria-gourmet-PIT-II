/* Client-side navigation, rendering, cart, checkout, and inventory management. */

const state = {
  categories: [],
  products: [],
  cart: new Map(),
  activeCategory: null,
  editingProductId: null
};

const currency = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL"
});

const elements = {
  shopView: document.querySelector("#shop-view"),
  adminView: document.querySelector("#admin-view"),
  categoryList: document.querySelector("#category-list"),
  productGrid: document.querySelector("#product-grid"),
  cartCount: document.querySelector("#cart-count"),
  cartDialog: document.querySelector("#cart-dialog"),
  cartItems: document.querySelector("#cart-items"),
  cartTotal: document.querySelector("#cart-total"),
  checkoutForm: document.querySelector("#checkout-form"),
  checkoutButton: document.querySelector("#checkout-button"),
  productDialog: document.querySelector("#product-dialog"),
  productForm: document.querySelector("#product-form"),
  productCategory: document.querySelector("#product-category"),
  dashboardCards: document.querySelector("#dashboard-cards"),
  adminProductList: document.querySelector("#admin-product-list"),
  orderList: document.querySelector("#order-list")
};

function notify(message, isError = false) {
  if (typeof Toastify !== "function") {
    console[isError ? "error" : "info"](message);
    return;
  }
  Toastify({
    text: message,
    duration: 3500,
    gravity: "top",
    position: "right",
    style: { background: isError ? "#9b3a2f" : "#513321" }
  }).showToast();
}

async function apiRequest(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...options.headers
    }
  });
  let result;
  try {
    result = await response.json();
  } catch {
    throw new Error("O servidor retornou uma resposta inválida.");
  }
  if (!response.ok || !result.success) {
    throw new Error(result.message || "Não foi possível concluir a operação.");
  }
  return result.data;
}

function makeElement(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined && text !== null) element.textContent = String(text);
  return element;
}

function showView(view) {
  const showShop = view === "shop";
  elements.shopView.classList.toggle("hidden", !showShop);
  elements.adminView.classList.toggle("hidden", showShop);
  if (!showShop) loadAdmin();
  else loadProducts();
}

function renderCategories() {
  elements.categoryList.replaceChildren();
  const allButton = makeCategoryButton("Todos", null);
  elements.categoryList.append(allButton);
  for (const category of state.categories) {
    elements.categoryList.append(makeCategoryButton(category.nome, category.id));
  }
}

function makeCategoryButton(label, categoryId) {
  const active = state.activeCategory === categoryId;
  const button = makeElement(
    "button",
    `rounded-full border px-4 py-2 text-sm font-semibold transition ${
      active
        ? "border-[#513321] bg-[#513321] text-white"
        : "border-[#e6ddd3] bg-white text-[#6e5544] hover:border-[#9a6039]"
    }`,
    label
  );
  button.type = "button";
  button.addEventListener("click", () => {
    state.activeCategory = categoryId;
    renderCategories();
    loadProducts();
  });
  return button;
}

async function loadCategories() {
  state.categories = await apiRequest("/api/categorias");
  renderCategories();
  populateCategorySelect();
}

function populateCategorySelect() {
  const options = state.categories.map((category) => {
    const option = makeElement("option", "", category.nome);
    option.value = String(category.id);
    return option;
  });
  elements.productCategory.replaceChildren(...options);
}

async function loadProducts() {
  try {
    const query = state.activeCategory
      ? `?categoria_id=${encodeURIComponent(state.activeCategory)}`
      : "";
    state.products = await apiRequest(`/api/produtos${query}`);
    renderProducts();
  } catch (error) {
    notify(error.message, true);
  }
}

function renderProducts() {
  elements.productGrid.replaceChildren();
  if (state.products.length === 0) {
    elements.productGrid.append(
      makeElement("p", "col-span-full rounded-2xl bg-white p-8 text-center text-[#806d60]", "Nenhum produto nesta categoria.")
    );
    return;
  }
  for (const product of state.products) {
    const card = makeElement("article", "overflow-hidden rounded-2xl border border-[#eee4d9] bg-white shadow-sm transition hover:-translate-y-1 hover:shadow-md");
    const art = makeElement("div", "flex h-36 items-center justify-center bg-[#f4ece3] text-6xl", product.imagem_emoji);
    art.setAttribute("aria-hidden", "true");
    const body = makeElement("div", "p-5");
    body.append(makeElement("p", "text-xs font-bold uppercase tracking-wider text-[#987052]", product.categoria_nome));
    body.append(makeElement("h3", "serif mt-2 text-xl font-bold", product.nome));
    body.append(makeElement("p", "mt-2 min-h-10 text-sm leading-6 text-[#806d60]", product.descricao));
    const footer = makeElement("div", "mt-5 flex items-center justify-between gap-3");
    footer.append(makeElement("span", "font-bold text-[#513321]", currency.format(product.preco)));
    const addButton = makeElement(
      "button",
      "rounded-xl px-4 py-2 text-sm font-bold text-white transition disabled:cursor-not-allowed disabled:bg-[#b9afa8] enabled:bg-[#513321] enabled:hover:bg-[#70492e]",
      product.quantidade_estoque > 0 ? "Adicionar" : "Esgotado"
    );
    addButton.type = "button";
    addButton.disabled = product.quantidade_estoque <= 0;
    addButton.addEventListener("click", () => addToCart(product));
    footer.append(addButton);
    body.append(footer);
    card.append(art, body);
    elements.productGrid.append(card);
  }
}

function addToCart(product) {
  const current = state.cart.get(product.id);
  if ((current?.quantity ?? 0) >= product.quantidade_estoque) {
    notify("Você já adicionou todo o estoque disponível.", true);
    return;
  }
  state.cart.set(product.id, {
    product,
    quantity: (current?.quantity ?? 0) + 1
  });
  updateCartCount();
  notify(`${product.nome} adicionado à sacola.`);
}

function updateCartCount() {
  const count = [...state.cart.values()].reduce((sum, item) => sum + item.quantity, 0);
  elements.cartCount.textContent = String(count);
}

function renderCart() {
  elements.cartItems.replaceChildren();
  let total = 0;
  for (const [productId, item] of state.cart) {
    total += item.product.preco * item.quantity;
    const row = makeElement("div", "flex items-center justify-between gap-3 rounded-xl bg-[#fbf8f4] p-3");
    const details = makeElement("div", "min-w-0");
    details.append(makeElement("p", "truncate font-semibold", item.product.nome));
    details.append(makeElement("p", "text-sm text-[#806d60]", `${item.quantity} × ${currency.format(item.product.preco)}`));
    const controls = makeElement("div", "flex shrink-0 items-center gap-2");
    const minus = makeElement("button", "h-8 w-8 rounded-full border border-[#e6ddd3] font-bold hover:bg-white", "−");
    minus.type = "button";
    minus.setAttribute("aria-label", `Remover uma unidade de ${item.product.nome}`);
    minus.addEventListener("click", () => changeCartQuantity(productId, -1));
    const plus = makeElement("button", "h-8 w-8 rounded-full border border-[#e6ddd3] font-bold hover:bg-white", "+");
    plus.type = "button";
    plus.setAttribute("aria-label", `Adicionar uma unidade de ${item.product.nome}`);
    plus.addEventListener("click", () => changeCartQuantity(productId, 1));
    controls.append(minus, plus);
    row.append(details, controls);
    elements.cartItems.append(row);
  }
  elements.cartTotal.textContent = currency.format(total);
  elements.checkoutButton.disabled = state.cart.size === 0;
}

function changeCartQuantity(productId, delta) {
  const item = state.cart.get(productId);
  if (!item) return;
  const next = item.quantity + delta;
  if (next <= 0) state.cart.delete(productId);
  else if (next > item.product.quantidade_estoque) {
    notify("Não há mais unidades disponíveis em estoque.", true);
    return;
  } else item.quantity = next;
  updateCartCount();
  renderCart();
}

function makeMetric(label, value, symbol) {
  const card = makeElement("article", "rounded-2xl border border-[#eee4d9] bg-white p-5 shadow-sm");
  const top = makeElement("div", "flex items-center justify-between");
  top.append(makeElement("p", "text-sm font-semibold text-[#806d60]", label));
  top.append(makeElement("span", "text-2xl", symbol));
  card.append(top, makeElement("p", "serif mt-4 text-2xl font-bold text-[#513321]", value));
  return card;
}

async function loadAdmin() {
  try {
    const [dashboard, products, orders] = await Promise.all([
      apiRequest("/api/dashboard"),
      apiRequest("/api/produtos"),
      apiRequest("/api/pedidos")
    ]);
    renderDashboard(dashboard);
    renderAdminProducts(products);
    renderOrders(orders);
  } catch (error) {
    notify(error.message, true);
  }
}

function renderDashboard(dashboard) {
  elements.dashboardCards.replaceChildren(
    makeMetric("Faturamento acumulado", currency.format(dashboard.faturamento_total), "💰"),
    makeMetric("Pedidos realizados", dashboard.total_pedidos, "🧾"),
    makeMetric("Valor em estoque", currency.format(dashboard.valor_estoque), "📦"),
    makeMetric("Produtos esgotados", dashboard.itens_esgotados, "⚠️")
  );
}

function renderAdminProducts(products) {
  elements.adminProductList.replaceChildren();
  if (products.length === 0) {
    elements.adminProductList.append(makeElement("p", "py-6 text-center text-sm text-[#806d60]", "Nenhum produto cadastrado."));
    return;
  }
  for (const product of products) {
    const row = makeElement("div", "flex flex-col gap-3 rounded-xl border border-[#eee4d9] p-4 sm:flex-row sm:items-center sm:justify-between");
    const info = makeElement("div", "flex min-w-0 items-start gap-3");
    info.append(makeElement("span", "text-2xl", product.imagem_emoji));
    const text = makeElement("div", "min-w-0");
    text.append(makeElement("h3", "truncate font-bold", product.nome));
    text.append(makeElement("p", "mt-1 text-sm text-[#806d60]", `${product.categoria_nome} · ${currency.format(product.preco)} · Estoque: ${product.quantidade_estoque}`));
    info.append(text);
    const actions = makeElement("div", "flex shrink-0 gap-2");
    const edit = makeElement("button", "rounded-lg border border-[#e6ddd3] px-3 py-2 text-sm font-semibold hover:bg-[#f8f3ed]", "Editar");
    edit.type = "button";
    edit.addEventListener("click", () => openProductDialog(product));
    const remove = makeElement("button", "rounded-lg border border-red-200 px-3 py-2 text-sm font-semibold text-red-700 hover:bg-red-50", "Excluir");
    remove.type = "button";
    remove.addEventListener("click", () => deleteProduct(product));
    actions.append(edit, remove);
    row.append(info, actions);
    elements.adminProductList.append(row);
  }
}

function renderOrders(orders) {
  elements.orderList.replaceChildren();
  if (orders.length === 0) {
    elements.orderList.append(makeElement("p", "py-6 text-center text-sm text-[#806d60]", "Os pedidos confirmados aparecerão aqui."));
    return;
  }
  for (const order of orders) {
    const card = makeElement("article", "rounded-xl border border-[#eee4d9] p-4");
    const heading = makeElement("div", "flex flex-wrap items-start justify-between gap-2");
    heading.append(makeElement("h3", "font-bold", `Pedido #${order.id} · ${order.cliente_nome}`));
    heading.append(makeElement("span", "rounded-full bg-[#f4ece3] px-3 py-1 text-xs font-bold capitalize text-[#70492e]", order.status.replaceAll("_", " ")));
    card.append(heading);
    card.append(makeElement("p", "mt-1 text-xs text-[#806d60]", new Date(`${order.data_pedido.replace(" ", "T")}Z`).toLocaleString("pt-BR")));
    const orderItems = order.itens.map((item) => `${item.quantidade}× ${item.produto_nome}`).join(", ");
    card.append(makeElement("p", "mt-3 text-sm leading-5 text-[#6e5544]", orderItems));
    card.append(makeElement("p", "mt-3 text-sm text-[#806d60]", `Entrega: ${order.endereco_entrega} · ${order.cliente_telefone}`));
    card.append(makeElement("p", "mt-3 text-right font-bold", currency.format(order.valor_total)));
    elements.orderList.append(card);
  }
}

function openProductDialog(product = null) {
  state.editingProductId = product ? product.id : null;
  document.querySelector("#product-dialog-heading").textContent = product ? "Editar produto" : "Novo produto";
  document.querySelector("#product-name").value = product?.nome ?? "";
  document.querySelector("#product-description").value = product?.descricao ?? "";
  document.querySelector("#product-price").value = product?.preco ?? "";
  document.querySelector("#product-stock").value = product?.quantidade_estoque ?? 0;
  document.querySelector("#product-category").value = String(product?.categoria_id ?? state.categories[0]?.id ?? "");
  document.querySelector("#product-emoji").value = product?.imagem_emoji ?? "☕";
  elements.productDialog.showModal();
}

async function saveProduct(event) {
  event.preventDefault();
  const payload = {
    nome: document.querySelector("#product-name").value.trim(),
    descricao: document.querySelector("#product-description").value.trim(),
    preco: document.querySelector("#product-price").value,
    quantidade_estoque: document.querySelector("#product-stock").value,
    categoria_id: document.querySelector("#product-category").value,
    imagem_emoji: document.querySelector("#product-emoji").value.trim() || "☕"
  };
  const editing = state.editingProductId !== null;
  try {
    await apiRequest(
      editing ? `/api/produtos/${state.editingProductId}` : "/api/produtos",
      { method: editing ? "PUT" : "POST", body: JSON.stringify(payload) }
    );
    elements.productDialog.close();
    notify(editing ? "Produto atualizado." : "Produto cadastrado.");
    await Promise.all([loadProducts(), loadAdmin()]);
  } catch (error) {
    notify(error.message, true);
  }
}

async function deleteProduct(product) {
  if (!window.confirm(`Deseja excluir "${product.nome}" do cardápio?`)) return;
  try {
    await apiRequest(`/api/produtos/${product.id}`, { method: "DELETE" });
    notify("Produto excluído.");
    await Promise.all([loadProducts(), loadAdmin()]);
  } catch (error) {
    notify(error.message, true);
  }
}

async function submitOrder(event) {
  event.preventDefault();
  if (state.cart.size === 0) {
    notify("Adicione ao menos um produto à sacola.", true);
    return;
  }
  const formData = new FormData(elements.checkoutForm);
  const payload = {
    cliente_nome: formData.get("cliente_nome"),
    cliente_telefone: formData.get("cliente_telefone"),
    endereco_entrega: formData.get("endereco_entrega"),
    itens: [...state.cart.entries()].map(([productId, item]) => ({
      produto_id: productId,
      quantidade: item.quantity
    }))
  };
  elements.checkoutButton.disabled = true;
  try {
    const order = await apiRequest("/api/pedidos", {
      method: "POST",
      body: JSON.stringify(payload)
    });
    state.cart.clear();
    updateCartCount();
    elements.checkoutForm.reset();
    elements.cartDialog.close();
    notify(`Pedido #${order.id} confirmado. Obrigado!`);
    await Promise.all([loadProducts(), loadAdmin()]);
  } catch (error) {
    notify(error.message, true);
  } finally {
    elements.checkoutButton.disabled = state.cart.size === 0;
  }
}

document.querySelector("#shop-nav").addEventListener("click", () => showView("shop"));
document.querySelector("#admin-nav").addEventListener("click", () => showView("admin"));
document.querySelector("#cart-nav").addEventListener("click", () => {
  renderCart();
  elements.cartDialog.showModal();
});
document.querySelector("#new-product-button").addEventListener("click", () => openProductDialog());
document.querySelector("#refresh-admin").addEventListener("click", loadAdmin);
elements.productForm.addEventListener("submit", saveProduct);
elements.checkoutForm.addEventListener("submit", submitOrder);
document.querySelectorAll(".dialog-close").forEach((button) => {
  button.addEventListener("click", () => button.closest("dialog").close());
});
document.querySelectorAll("dialog").forEach((dialog) => {
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) dialog.close();
  });
});
document.querySelector("#current-year").textContent = String(new Date().getFullYear());

async function initialize() {
  try {
    await loadCategories();
    await loadProducts();
  } catch (error) {
    notify(error.message, true);
  }
}

initialize();
