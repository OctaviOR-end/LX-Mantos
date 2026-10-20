const grid = document.querySelector('#grade');
const search = document.querySelector('#busca');
const category = document.querySelector('#categoria');
const pager = document.querySelector('#paginacao');
let page = 1;
function render() {
  const query = search.value.toLocaleLowerCase('pt-BR');
  const items = window.catalogo.filter(p => p.nome_pt.toLocaleLowerCase('pt-BR').includes(query) && (!category.value || p.categorias.includes(category.value)));
  const total = Math.max(1, Math.ceil(items.length / 12));
  page = Math.min(page, total);
  grid.replaceChildren();
  for (const p of items.slice((page - 1) * 12, page * 12)) {
    const article = document.createElement('article'); article.className = 'produto';
    const link = document.createElement('a'); link.href = `/produtos/${p.album_id}/`;
    if (p.capa) { const img = document.createElement('img'); img.src = '/' + p.capa; img.alt = p.nome_pt; img.loading = 'lazy'; link.append(img); }
    else { const empty = document.createElement('div'); empty.className = 'sem-foto'; empty.textContent = 'Fotografia pendente'; link.append(empty); }
    const name = document.createElement('h2'); name.textContent = p.nome_pt; link.append(name);
    const cats = document.createElement('p'); cats.textContent = p.categorias.join(' · ');
    article.append(link, cats);
    if (window.rascunho) { const state = document.createElement('small'); state.textContent = p.validado ? 'Fotos verificadas · aguardando liberação' : 'Dados não validados para publicação'; article.append(state); }
    grid.append(article);
  }
  document.querySelector('#contagem').textContent = `${items.length} produto(s) · Página ${page} de ${total}`;
  document.querySelector('#anterior').disabled = page === 1;
  document.querySelector('#proxima').disabled = page === total;
}
search.addEventListener('input', () => { page = 1; render(); });
category.addEventListener('change', () => { page = 1; render(); });
document.querySelector('#anterior').addEventListener('click', () => { page--; render(); });
document.querySelector('#proxima').addEventListener('click', () => { page++; render(); });
render();
