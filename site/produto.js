const button = document.querySelector('#whatsapp');
const config = window.lxConfig;
for (const input of document.querySelectorAll('input[name=tamanho]')) {
  input.addEventListener('change', () => {
    const size = document.querySelector('input[name=tamanho]:checked').value;
    if (!config.whatsapp) return;
    const url = config.base_url ? new URL(`/produtos/${window.produto.album_id}/`, config.base_url).href : ''; 
    const text = `Olá! Tenho interesse em ${window.produto.nome_pt} (referência ${window.produto.album_id}), tamanho ${size}. Gostaria de confirmar disponibilidade e valor. ${url}`;
    button.href = `https://wa.me/${config.whatsapp}?text=${encodeURIComponent(text)}`;
    button.removeAttribute('aria-disabled'); button.tabIndex = 0;
  });
}
button.addEventListener('click', event => { if (button.getAttribute('aria-disabled') === 'true') event.preventDefault(); });
