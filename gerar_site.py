#!/usr/bin/env python3
"""Adaptador estático independente; páginas e imagens servidas pelo domínio LX."""
import argparse, html, json, re, shutil, tempfile, os
from pathlib import Path
from urllib.parse import urlsplit
from sincronizar import local_file, verify_and_approve

def esc(s): return html.escape(str(s),quote=True)
def js(value): return json.dumps(value,ensure_ascii=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
def config_validate(config,preview):
    config={'whatsapp':config.get('whatsapp',''),'base_url':config.get('base_url','')}
    if config['whatsapp'] and not re.fullmatch(r'[1-9]\d{9,14}',config['whatsapp']): raise ValueError('WhatsApp deve conter DDI e DDD, somente dígitos')
    if config['base_url']:
        p=urlsplit(config['base_url'])
        if p.scheme!='https' or not p.hostname or p.username or p.password or p.query or p.fragment or p.path not in ('','/') or p.port not in (None,443): raise ValueError('base_url deve ser origem HTTPS do domínio LX')
        if p.hostname=='yupoo.com' or p.hostname.endswith('.yupoo.com'): raise ValueError('O domínio do site deve pertencer à LX')
    if not preview and not all(config.values()): raise ValueError('Produção exige WhatsApp real e domínio LX')
    return config

def page(title,body,preview):
    banner='<p class="aviso">Rascunho para revisão — não é um catálogo publicado. Dados pendentes estão identificados.</p>' if preview else ''
    return '<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'+('<meta name="robots" content="noindex,nofollow">' if preview else '')+'<title>'+esc(title)+' | LX Mantos</title><link rel="stylesheet" href="/estilo.css"></head><body><header><a href="/">LX MANTOS</a><nav aria-label="Navegação principal"><a href="/">Catálogo</a></nav></header><main>'+banner+body+'</main><footer>LX Mantos · Consulte disponibilidade, medidas e valores pelo WhatsApp.</footer></body></html>'

def _build(data,out,config,preview,approvals):
    config=config_validate(config,preview)
    products=json.loads((data/'produtos.json').read_text())
    byid={p['album_id']:p for p in products}
    verify_and_approve(byid,approvals,data)  # revalida conteúdo e hashes; não confia no booleano serializado.
    products=[p for p in products if preview or p['publicavel']]
    if not preview and not products: raise ValueError('Nenhum produto com fotos revisadas e ativo')
    # Geração em diretório novo: não mantém páginas de produtos desativados.
    if out.exists(): raise ValueError('Destino já existe; use outro diretório para revisão e troca atômica no deploy')
    out.mkdir(parents=True)
    source=Path(__file__).parent/'site'
    for file in source.iterdir(): shutil.copy2(file,out/file.name)
    catalog=[]
    for p in products:
        if not re.fullmatch(r'\d+',str(p['album_id'])): raise ValueError('ID inválido para rota')
        images=[]
        for i in p['imagens_utilizaveis']:
            src=local_file(data,i['arquivo_local']); dest=out/i['arquivo_local']; dest.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(src,dest); images.append(i['arquivo_local'])
        cats=p.get('categorias') or [p['categoria']]
        catalog.append({'album_id':p['album_id'],'nome_pt':p['nome_pt'],'categorias':cats,'capa':images[0] if images else None,'validado':bool(images)})
        gallery=''.join('<img src="/'+esc(src)+'" alt="'+esc(p['nome_pt'])+'">' for src in images) or '<div class="sem-foto">Fotografia pendente de validação</div>'
        sizes='<fieldset><legend>Escolha o tamanho para consultar</legend>'+''.join('<label><input type="radio" name="tamanho" value="'+s+'"> '+s+'</label>' for s in ('P','M','G','GG'))+'</fieldset>'
        status=('<p class="aviso">'+('Fotos decodificadas; associação '+esc(p['imagens_utilizaveis'][0].get('evidencia_associacao','não documentada'))+'. Revisão visual '+('aprovada' if p['revisao_visual_aprovada'] else 'pendente') if images else 'Fotos não validadas; não publicar este produto.')+'</p>') if preview else ''
        body='<p><a href="/">← Voltar ao catálogo</a></p><div class="detalhe"><div class="galeria">'+gallery+'</div><section><p>'+esc(' · '.join(cats))+'</p><h1>'+esc(p['nome_pt'])+'</h1><p>Referência '+p['album_id']+'</p>'+status+'<p>'+esc(p.get('descricao',''))+'</p><p>'+esc(p.get('aviso','Disponibilidade confirmada pelo WhatsApp.'))+'</p>'+sizes+'<a id="whatsapp" class="cta" aria-disabled="true" tabindex="-1" target="_blank" rel="noopener noreferrer">Consultar pelo WhatsApp</a><p>'+('Selecione um tamanho para consultar.' if config['whatsapp'] else 'Canal de atendimento aguardando configuração da LX Mantos.')+'</p></section></div><script>window.lxConfig='+js(config)+';window.produto='+js({'album_id':p['album_id'],'nome_pt':p['nome_pt']})+';</script><script src="/produto.js"></script>'
        path=out/'produtos'/p['album_id']; path.mkdir(parents=True); (path/'index.html').write_text(page(p['nome_pt'],body,preview),encoding='utf8')
    options=''.join('<option value="'+esc(c)+'">'+esc(c)+'</option>' for c in sorted({c for p in catalog for c in p['categorias']}))
    body='<p>VISTA SUA PAIXÃO</p><h1>Seu time. Sua história. Seu manto.</h1><p>Escolha uma camisa e fale com a LX Mantos.</p><div class="filtros"><label>Buscar camisa <input id="busca" type="search" placeholder="Time ou modelo"></label><label>Categoria <select id="categoria"><option value="">Todas as categorias</option>'+options+'</select></label></div><p id="contagem" aria-live="polite"></p><div id="grade"></div><div id="paginacao"><button id="anterior">Anterior</button><button id="proxima">Próxima</button></div><noscript>Ative o JavaScript para filtrar o catálogo.</noscript><script>window.catalogo='+js(catalog)+';window.rascunho='+js(preview)+';</script><script src="/catalogo.js"></script>'
    (out/'index.html').write_text(page('Catálogo',body,preview),encoding='utf8')
    (out/'manifesto_site.json').write_text(json.dumps({'modo':'rascunho' if preview else 'producao','produtos':len(products),'dominio':config['base_url']},indent=2),encoding='utf8')
    return len(products)

def build(data,out,config,preview,approvals):
    if out.exists(): raise ValueError('Destino já existe; use outro diretório')
    out.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=out.parent,prefix='.site-') as tmp:
        staging=Path(tmp)/'site'
        count=_build(data,staging,config,preview,approvals)
        os.replace(staging,out)
        return count

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--data',default='catalogo'); p.add_argument('--out',required=True); p.add_argument('--config',default='config_site.json'); p.add_argument('--preview',action='store_true'); p.add_argument('--approvals',default='aprovacoes.json'); args=p.parse_args()
    config=json.loads(Path(args.config).read_text()) if Path(args.config).exists() else {}
    approvals=json.loads(Path(args.approvals).read_text()) if Path(args.approvals).exists() else {}
    print('Páginas geradas:',build(Path(args.data),Path(args.out),config,args.preview,approvals))
if __name__=='__main__': main()
