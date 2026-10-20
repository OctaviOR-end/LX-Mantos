#!/usr/bin/env python3
"""Sincronização incremental LX. Sem remoção implícita; publicação exige revisão."""
import argparse, copy, hashlib, json, mimetypes, os, re, tempfile
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit, parse_qs, urlencode
from urllib.robotparser import RobotFileParser
from importador import (ALBUM_HOST, IMAGE_HOST, UA, Fetcher, canonical, load_inputs,
                        title_pt, category, validate_image, audit_sample, csv_write)

def now(): return datetime.now(timezone.utc).isoformat()
def digest(value): return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
def atomic(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(dir=path.parent,prefix='.tmp-')
    try:
        with os.fdopen(fd,'w',encoding='utf8') as f: json.dump(value,f,ensure_ascii=False,indent=2)
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)

def local_file(root,relative):
    p=(root/relative).resolve()
    if not p.is_relative_to(root.resolve()) or not p.is_file(): raise ValueError('Arquivo ausente ou fora da pasta autorizada: '+str(relative))
    return p

def store_image(data,meta,output):
    # Normaliza o formato efetivamente decodificado para um arquivo servido corretamente.
    from PIL import Image
    import io
    with Image.open(io.BytesIO(data)) as im: fmt=im.format
    ext={'JPEG':'.jpg','PNG':'.png','WEBP':'.webp','GIF':'.gif'}.get(fmt)
    if not ext: raise ValueError('Formato não suportado para catálogo: '+str(fmt))
    relative='imagens/'+meta['sha256']+ext
    destination=output/relative; destination.parent.mkdir(parents=True,exist_ok=True)
    if not destination.exists(): destination.write_bytes(data)
    return relative

def base_product(aid,name):
    return {'album_id':aid,'album_url':f'https://{ALBUM_HOST}/albums/{aid}','nome_original':name,
            'nome_pt':title_pt(name),'categoria':category(name),'categorias':[category(name)],
            'tamanhos':['P','M','G','GG'],'preco':None,'imagens':[],'publicavel':False,
            'aviso':'Disponibilidade e medidas serão confirmadas pelo WhatsApp.'}

def read_manifest(path,output):
    """Manifesto exportado pelo fornecedor: associação declarada, ainda requer revisão visual."""
    manifest=json.loads(path.read_text(encoding='utf-8-sig'))
    if not manifest.get('origem') or not isinstance(manifest.get('produtos'),list): raise ValueError('Manifesto exige origem e produtos')
    products={}; events=[]; seen_photo={}
    for row in manifest['produtos']:
        aid=str(row['album_id'])
        if not re.fullmatch(r'\d+',aid): raise ValueError('ID de álbum inválido')
        album=canonical(row['album_url'],ALBUM_HOST)
        if album.rsplit('/',1)[1]!=aid: raise ValueError('ID não corresponde ao álbum')
        if aid in products: raise ValueError('ID duplicado no manifesto: '+aid)
        p=base_product(aid,row['nome_original'])
        cats=row.get('categorias',[])
        if not isinstance(cats,list) or not all(isinstance(c,str) and c.strip() for c in cats): raise ValueError('categorias deve ser lista de textos')
        p['categorias']=list(dict.fromkeys(cats+[p['categoria']]))
        p['origem_manifesto']={'origem':manifest['origem'],'arquivo':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
        p['validacao_atual']='sem_fotos_validas'; ids=set(); sha=set()
        for image in row.get('imagens',[]):
            file=local_file(path.parent,image['arquivo']); data=file.read_bytes()
            if len(data)>20*1024*1024: raise ValueError('Imagem excede 20 MB')
            m=validate_image({'estado':'recebido','content_type':mimetypes.guess_type(file.name)[0] or 'application/octet-stream','bytes':len(data)},data)
            record={'album_id':aid,'arquivo':image['arquivo'],**m}; events.append(record)
            if m['estado']!='valida': continue
            photo=str(image.get('foto_id',m['sha256']))
            source=image.get('url_origem')
            if source:
                source=canonical(source,IMAGE_HOST)
                actual=urlsplit(source).path.rsplit('/',1)[0]
                if photo!=actual: raise ValueError('foto_id não corresponde a url_origem')
            for key in (('id',photo),('hash',m['sha256'])):
                if key in seen_photo and seen_photo[key]!=aid: raise ValueError('Foto compartilhada por álbuns distintos; revisar vínculo: '+photo)
                seen_photo[key]=aid
            previous=next((i for i in p['imagens'] if i['foto_id']==photo),None)
            if previous and (previous['largura']*previous['altura'],previous['bytes']) >= (m['largura']*m['altura'],m['bytes']): continue
            if any(i['sha256']==m['sha256'] and i['foto_id']!=photo for i in p['imagens']): continue
            p['imagens']=[i for i in p['imagens'] if i['foto_id']!=photo]
            relative=store_image(data,m,output)
            p['imagens'].append({'arquivo_local':relative,'sha256':m['sha256'],'foto_id':photo,'url':source,'largura':m['largura'],'altura':m['altura'],'bytes':m['bytes'],'validada_em':now(),'evidencia_associacao':'manifesto_fornecedor_declarado'})
        if p['imagens']: p['validacao_atual']='arquivos_decodificados_associacao_declarada'
        products[aid]=p
    return list(products.values()),events

def category_url(url):
    p=urlsplit(url)
    if p.scheme!='https' or p.netloc!=ALBUM_HOST or not re.fullmatch(r'/categories/\d+/?',p.path): raise ValueError('Categoria não autorizada')
    q=parse_qs(p.query)
    if set(q)-{'page'} or any(not re.fullmatch(r'\d+',v) for vs in q.values() for v in vs): raise ValueError('Paginação inválida')
    return f'https://{ALBUM_HOST}'+p.path.rstrip('/')+('?' + urlencode({'page':q['page'][0]}) if q else '')

class ListingHTML(HTMLParser):
    def __init__(self,base): super().__init__(); self.base=base; self.albums={}; self.pages=set(); self.current=None; self.depth=0
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='a':
            self.current=None
            u=urljoin(self.base,a.get('href',''))
            try:
                album=canonical(u,ALBUM_HOST); self.current=album; self.albums.setdefault(album,a.get('title',''))
            except ValueError:
                try:
                    page=category_url(u)
                    if urlsplit(page).path==urlsplit(self.base).path: self.pages.add(page)
                except ValueError: pass
        if tag=='img' and self.current and a.get('alt'): self.albums[self.current]=a['alt']
    def handle_data(self,text):
        if self.current and not self.albums[self.current] and text.strip(): self.albums[self.current]=text.strip()
    def handle_endtag(self,tag):
        if tag=='a': self.current=None

def discover(categories,fetch,max_pages=3,limit=10):
    meta,body=fetch.get(f'https://{ALBUM_HOST}/robots.txt',1024*1024)
    events=[{'url':f'https://{ALBUM_HOST}/robots.txt',**meta}]; result={}
    if meta.get('http')==404: robots=None
    elif meta.get('http')==200 and meta.get('content_type','text/plain') in ('text/plain','text/html'):
        robots=RobotFileParser(); robots.parse(body.decode(errors='replace').splitlines())
    else: return [],events
    for category in categories:
        first=category_url(category); pending=[first]; visited=set()
        while pending and len(visited)<max_pages and len(result)<limit:
            url=pending.pop(0)
            if url in visited: continue
            visited.add(url)
            if robots and not robots.can_fetch(UA,url): events.append({'url':url,'estado':'robots_negado'}); continue
            m,b=fetch.get(url,5*1024*1024); events.append({'url':url,**m})
            if m.get('http')!=200 or m.get('content_type')!='text/html': break
            parser=ListingHTML(url); parser.feed(b.decode('utf8',errors='replace'))
            for album,name in parser.albums.items():
                aid=album.rsplit('/',1)[1]
                if aid not in result:
                    if len(result)>=limit: break
                    result[aid]=base_product(aid,name or f'Álbum {aid} — nome pendente')
                    result[aid]['imagens_origem_csv']=[]
                result[aid].setdefault('categorias_fornecedor',[])
                cid=urlsplit(first).path.rsplit('/',1)[1]
                if cid not in result[aid]['categorias_fornecedor']: result[aid]['categorias_fornecedor'].append(cid)
            pending.extend(sorted(parser.pages-set(visited)-set(pending)))
        events.append({'categoria':first,'paginas_lidas':len(visited),'limite_paginas':max_pages,'limite_produtos':limit,'completude':'nao_garantida_amostra_limitada'})
    return list(result.values()),events

def merge(old,incoming,edits):
    result=copy.deepcopy(old); changes=[]
    for p in incoming:
        aid=p['album_id']; prev=result.get(aid,{})
        p=copy.deepcopy(p)
        p['categorias_fornecedor']=list(dict.fromkeys(prev.get('categorias_fornecedor',[])+p.get('categorias_fornecedor',[])))
        fingerprint=digest({k:p.get(k) for k in ('nome_original','categoria','categorias','categorias_fornecedor','imagens_origem_csv')})
        # Campos do fornecedor e decisões comerciais ficam separados.
        item={**prev,**p,'fingerprint_dados':fingerprint,'atualizado_em':now()}
        if not p.get('imagens') and prev.get('imagens'):
            item['imagens']=prev['imagens']; item['validacao_atual']='falha_ou_sem_nova_evidencia_fotos_preservadas'
        for k in ('nome_pt','categoria','preco','descricao','ativo'):
            if k in prev.get('edicoes_manuais',{}): item[k]=prev['edicoes_manuais'][k]
        item['edicoes_manuais']=prev.get('edicoes_manuais',{})
        changes.append({'album_id':aid,'dados':'novo' if not prev else 'alterado' if prev.get('fingerprint_dados')!=fingerprint else 'inalterado','imagens_alteradas':{i['sha256'] for i in prev.get('imagens',[])}!={i['sha256'] for i in item.get('imagens',[])}})
        result[aid]=item
    for aid,item in result.items():
        manual={**item.get('edicoes_manuais',{}),**edits.get(aid,{})}
        if set(manual)-{'nome_pt','categoria','preco','descricao','ativo'}: raise ValueError('Edição de campo protegido não permitida')
        item['edicoes_manuais']=manual; item.update(manual)
        item['categorias']=list(dict.fromkeys([item['categoria']]+item.get('categorias',[])))
        item['publicavel']=False
    return result,changes

def verify_and_approve(products,approvals,output):
    events=[]
    for aid,p in products.items():
        valid=[]
        for im in p.get('imagens',[]):
            try:
                file=local_file(output,im['arquivo_local']); data=file.read_bytes()
                meta=validate_image({'estado':'recebido','content_type':mimetypes.guess_type(file.name)[0] or 'application/octet-stream'},data)
                if meta['estado']!='valida' or meta['sha256']!=im['sha256']: raise ValueError('Hash ou conteúdo de imagem inválido')
                if im.get('evidencia_associacao') not in ('html_album','manifesto_fornecedor_declarado'): raise ValueError('Associação da foto sem evidência')
                valid.append(im)
            except (ValueError,KeyError) as e: events.append({'album_id':aid,'estado':'arquivo_preservado_indisponivel','erro':str(e)})
        p['imagens_utilizaveis']=valid
        approved=approvals.get(aid,{})
        p['revisao_visual_aprovada']=bool(valid) and set(approved.get('sha256',[]))=={i['sha256'] for i in valid} and bool(approved.get('revisor'))
        p['publicavel']=p['revisao_visual_aprovada'] and p.get('ativo') is True
    return events

def run(args):
    output=Path(args.out); output.mkdir(parents=True,exist_ok=True)
    state=output/'estado.json'
    old=json.loads(state.read_text()).get('produtos',{}) if state.exists() else {}
    incoming=[]; report={'executado_em':now(),'rede':[],'arquivos':[],'diagnostico_csv':{},'modo':args.command}
    if args.inputs:
        incoming,report['diagnostico_csv']=load_inputs(args.inputs)
    if args.manifest:
        local,report['arquivos']=read_manifest(Path(args.manifest),output)
        # Evidência local prevalece sobre os mesmos IDs do CSV.
        combined={p['album_id']:p for p in incoming}; combined.update({p['album_id']:p for p in local}); incoming=list(combined.values())
    if args.command=='online':
        fetch=Fetcher()
        found,report['rede']=discover(args.category or [f'https://{ALBUM_HOST}/categories/712891'],fetch,args.max_pages,args.limit)
        combined={p['album_id']:p for p in incoming}
        for p in found:
            if p['album_id'] in combined: combined[p['album_id']].update(categorias_fornecedor=p.get('categorias_fornecedor',[]))
            else: combined[p['album_id']]=p
        incoming=list(combined.values()); audited=copy.deepcopy(incoming[:args.limit])
        if audited:
            evidence=audit_sample(audited,fetch,output,args.limit); report['auditoria_online']=evidence
            for p in audited:
                for im in p['imagens']:
                    file=local_file(output,im['arquivo_local']); data=file.read_bytes()
                    im['arquivo_local']=store_image(data,im,output); im['evidencia_associacao']='html_album'; im['validada_em']=now()
                p['validacao_atual']='album_consultado' if p['imagens'] else 'rede_sem_validacao'
                combined[p['album_id']]=p
            incoming=list(combined.values())
    edits=json.loads(Path(args.edits).read_text()) if args.edits and Path(args.edits).exists() else {}
    products,changes=merge(old,incoming,edits)
    approvals=json.loads(Path(args.approvals).read_text()) if args.approvals and Path(args.approvals).exists() else {}
    report['integridade']=verify_and_approve(products,approvals,output)
    report.update(alteracoes=changes,produtos_preservados_sem_atualizacao=sorted(set(old)-{p['album_id'] for p in incoming}),total=len(products),com_imagens_utilizaveis=sum(bool(p['imagens_utilizaveis']) for p in products.values()),publicaveis=sum(p['publicavel'] for p in products.values()))
    # Histórico antes do commit: só um processo de escrita é permitido por vez.
    atomic(output/'historico'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')+'.json'),report)
    atomic(state,{'versao':2,'produtos':products})
    atomic(output/'produtos.json',list(products.values())); csv_write(output/'produtos.csv',list(products.values())); atomic(output/'ultima_execucao.json',report)
    print(json.dumps({k:report[k] for k in ('total','com_imagens_utilizaveis','publicaveis')},ensure_ascii=False))
    return 2 if args.command=='online' and (not incoming or any(not p.get('imagens') for p in incoming[:args.limit])) else 0

def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('command',choices=['arquivos','online'])
    parser.add_argument('--inputs'); parser.add_argument('--manifest'); parser.add_argument('--out',default='catalogo'); parser.add_argument('--edits',default='edicoes_manuais.json'); parser.add_argument('--approvals',default='aprovacoes.json')
    parser.add_argument('--category',action='append'); parser.add_argument('--limit',type=int,choices=range(1,11),default=10); parser.add_argument('--max-pages',type=int,choices=range(1,21),default=3)
    args=parser.parse_args()
    # Lock exclusivo evita lost updates; removido mesmo ao ocorrer erro.
    out=Path(args.out); out.mkdir(parents=True,exist_ok=True); lock=out/'.sync.lock'
    try: fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    except FileExistsError: parser.error('Sincronização já em execução; verificar .sync.lock')
    try:
        os.close(fd); return run(args)
    finally: lock.unlink(missing_ok=True)

if __name__=='__main__': raise SystemExit(main())
