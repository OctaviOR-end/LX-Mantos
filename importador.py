#!/usr/bin/env python3
"""Importação conservadora: CSVs não são prova de associação nem de validade HTTP."""
import argparse, csv, hashlib, html, io, json, re, time, warnings
from collections import Counter, defaultdict
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError, URLError
from PIL import Image

ALBUM_HOST = 'minkang.x.yupoo.com'
IMAGE_HOST = 'photo.yupoo.com'
NOTICE = 'Disponibilidade e medidas serão confirmadas pelo WhatsApp.'
UA = 'LXMantosCatalogAudit/1.0 (authorized sample; no bypass)'

def canonical(url, host):
    url = html.unescape(url.strip())
    if url.startswith('//'): url = 'https:' + url
    if url.startswith('/'): url = 'https://' + host + url
    p = urlsplit(url)
    if p.scheme != 'https' or p.hostname != host or p.username or p.password or p.port not in (None,443):
        raise ValueError('URL fora do domínio HTTPS autorizado')
    if host == ALBUM_HOST and not re.fullmatch(r'/albums/\d+/?',p.path):
        raise ValueError('Link não é álbum individual')
    if host == IMAGE_HOST and not re.fullmatch(r'/minkang/[^/]+/[^/]+',p.path):
        raise ValueError('Imagem fora do fornecedor autorizado')
    return urlunsplit(('https',host,p.path.rstrip('/'),'', ''))

def photo_id(url): return urlsplit(url).path.rsplit('/',1)[0]
def urls(text):
    return list(dict.fromkeys(re.findall(r'(?:https?:)?//[^\s|<>"\']+|/minkang/[^\s|<>"\']+', html.unescape(text or ''))))

def title_pt(name):
    name = re.sub(r'(?:\s*(?:Size|SIZE)\s*\d+-\d+|\s*S-(?:[234]?XL|XXL))\s*$','',name).strip()
    terms = [('Special Commemorative Edition','Edição Especial Comemorativa'),('Retirement Edition','Edição de Aposentadoria'),('Anniversary Edition','Edição de Aniversário'),('Centenary Commemorative','Comemorativa do Centenário'),('Special Edition','Edição Especial'),('Player Version','Versão Jogador'),('Long-Sleeved','Manga Longa'),('Long-Sleeve','Manga Longa'),('Third Away','Terceiro Uniforme'),('Pre-Match','Pré-Jogo'),('Kids Kit','Conjunto Infantil'),('Baby Jersey','Camisa para Bebê'),('Dark Blue','Azul-Escuro'),('Dark Green','Verde-Escuro'),('White and Blue','Branca e Azul'),('Red and White','Vermelha e Branca'),('Yellow and Red','Amarela e Vermelha'),('Goalkeeper','Goleiro'),('Germany','Alemanha'),('Spain','Espanha'),('Norway','Noruega'),('Gremio','Grêmio'),('Retro','Retrô'),('Home','Titular'),('Away','Visitante'),('Black','Preta'),('White','Branca'),('Blue','Azul'),('Red','Vermelha'),('Gold','Dourada'),('Jersey','Camisa'),('Special','Especial')]
    for a,b in terms: name = re.sub(r'\b'+re.escape(a)+r'\b',b,name,flags=re.I)
    for kind in ('Conjunto Infantil','Camisa para Bebê','Polo','Camisa'):
        if kind in name:
            name=name.replace(kind,'').replace('Camisa','')
            return kind+' '+re.sub(r'\s+',' ',name).strip()
    return name

def category(name):
    if re.search('Kids|Baby',name,re.I): return 'Infantil'
    if 'Polo' in name: return 'Polo'
    if 'Retro' in name or re.search(r'\b(?:19\d\d|200[0-9])\b',name): return 'Retrô'
    if 'Player Version' in name: return 'Jogador'
    return 'A confirmar'  # Ausência de Player Version não comprova Torcedor.

def load_inputs(folder):
    products, rejected, diagnostics, ownership = {}, [], [], defaultdict(set)
    for path in sorted(Path(folder).glob('*.csv')):
        with path.open(encoding='utf-8-sig',newline='') as f:
            sample=f.read(8192); f.seek(0)
            try: dialect=csv.Sniffer().sniff(sample,delimiters=',;\t')
            except csv.Error: dialect=csv.excel
            reader=csv.DictReader(f,dialect=dialect); rows=list(reader); fields=reader.fieldnames
        diag={'arquivo':path.name,'linhas':len(rows),'colunas':fields,'sem_album':0,'html_no_titulo':0,'variantes_grandes_parciais':0,'duplicatas_de_fotos':0,'conflitos':[]}
        for line,row in enumerate(rows,2):
            if '<' in row.get('item_page_title',''): diag['html_no_titulo']+=1
            source=row.get('link_album_yupoo') or row.get('item_page_link','')
            try:
                if not source.strip(): raise ValueError('Link do álbum ausente')
                album=canonical(source,ALBUM_HOST)
            except ValueError as e:
                diag['sem_album']+=1; rejected.append({'arquivo':path.name,'linha':line,'nome':row.get('title',''),'motivo':str(e)}); continue
            aid=album.rsplit('/',1)[1]
            name=html.unescape(row.get('nome_original') or row.get('title','')).strip()
            if '<' in name: name=re.sub('<[^>]+>','',name).strip()
            raw=urls(row.get('imagens_album') or row.get('image_0',''))
            raw+=urls(row.get('imagem_capa') or row.get('image',''))
            photos=[]
            for u in raw:
                try: u=canonical(u,IMAGE_HOST)
                except ValueError: continue
                if u in photos: diag['duplicatas_de_fotos']+=1
                else: photos.append(u)
                ownership[photo_id(u)].add(aid)
            tested=urls(row.get('imagens_album_grandes_teste',''))
            if tested and any('/small.' in u for u in tested) and any('/big.' in u for u in tested): diag['variantes_grandes_parciais']+=1
            if aid not in products:
                products[aid]={'album_id':aid,'nome_original':name,'nome_pt':title_pt(name),'categoria':category(name),'album_url':album,'pagina_produto':'/produtos/'+aid,'tamanhos':['P','M','G','GG'],'aviso':NOTICE,'preco':None,'imagens_origem_csv':[],'imagens':[],'imagem_capa':None,'fontes':[],'revisao':[]}
            p=products[aid]
            if p['nome_original']!=name: diag['conflitos'].append({'album_id':aid,'nome':name}); p['revisao'].append('Títulos divergentes entre CSVs')
            p['imagens_origem_csv']=list(dict.fromkeys(p['imagens_origem_csv']+photos))
            p['fontes'].append(path.name)
        diagnostics.append(diag)
    for p in products.values():
        if p['categoria']=='Infantil': p['revisao'].append('Tamanhos P/M/G/GG são opções de consulta; conferir grade infantil do fornecedor')
        if p['categoria']=='A confirmar': p['revisao'].append('Confirmar categoria Torcedor com fornecedor')
        p['revisao'].append('Tradução por glossário; revisar denominação comercial antes de publicar')
    conflicts={k:sorted(v) for k,v in ownership.items() if len(v)>1}
    return list(products.values()), {'arquivos':diagnostics,'rejeitados':rejected,'fotos_compartilhadas_entre_albuns':conflicts}

class SafeRedirect(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        if urlsplit(req.full_url).hostname!=urlsplit(newurl).hostname: raise ValueError('Redirecionamento entre domínios recusado')
        target=urlsplit(newurl)
        if target.scheme!='https' or target.username or target.password or target.port not in (None,443): raise ValueError('Redirecionamento inseguro')
        if target.path!='/robots.txt':
            if target.hostname==ALBUM_HOST and re.fullmatch(r'/categories/\d+/?',target.path):
                from urllib.parse import parse_qs
                query=parse_qs(target.query)
                if set(query)-{'page'} or any(not value.isdigit() for values in query.values() for value in values): raise ValueError('Paginação inválida no redirecionamento')
            else: canonical(newurl,target.hostname)
        return super().redirect_request(req,fp,code,msg,headers,newurl)

class Fetcher:
    def __init__(self,delay=0.7): self.delay=delay; self.denied=set(); self.opener=build_opener(SafeRedirect()); self.last=0
    def get(self,url,limit=20*1024*1024):
        host=urlsplit(url).hostname
        if host not in (ALBUM_HOST,IMAGE_HOST): return {'estado':'dominio_recusado'},b''
        if host in self.denied: return {'estado':'nao_tentado_bloqueio_previo'},b''
        time.sleep(max(0,self.delay-(time.monotonic()-self.last))); self.last=time.monotonic()
        try:
            with self.opener.open(Request(url,headers={'User-Agent':UA}),timeout=25) as r:
                data=r.read(limit+1)
                if len(data)>limit: return {'estado':'limite_de_bytes','http':r.status},b''
                return {'estado':'recebido','http':r.status,'content_type':r.headers.get_content_type(),'bytes':len(data)},data
        except HTTPError as e:
            if e.code in (401,403,429): self.denied.add(host)
            return {'estado':'acesso_restrito' if e.code in (401,403,429) else 'http_invalido','http':e.code,'erro':str(e)},b''
        except (URLError,TimeoutError,ValueError,OSError) as e:
            if '403' in str(e): self.denied.add(host)
            return {'estado':'bloqueio_proxy' if 'Tunnel connection failed: 403' in str(e) else 'erro_rede','erro':str(e)},b''

class AlbumHTML(HTMLParser):
    """Extrai somente elementos com marcadores de galeria; não inclui avatares/logos."""
    def __init__(self): super().__init__(); self.photos=defaultdict(list); self.title=''; self.in_title=False; self.attrs_seen=Counter()
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='title': self.in_title=True
        marker=' '.join([a.get('class',''),a.get('id','')]).lower()
        gallery=any(x in marker for x in ('image__img','image__main','showalbum__image','album__photo')) or any(k in a for k in ('data-origin-src','data-original'))
        if tag not in ('img','a','source') or not gallery: return
        for key in ('src','data-src','srcset','data-srcset','data-origin-src','data-original','data-big','href'):
            if key not in a: continue
            self.attrs_seen[key]+=1
            for u in urls(a[key]):
                try: u=canonical(u,IMAGE_HOST)
                except ValueError: continue
                if u not in self.photos[photo_id(u)]: self.photos[photo_id(u)].append(u)
    def handle_endtag(self,tag):
        if tag=='title': self.in_title=False
    def handle_data(self,data):
        if self.in_title: self.title+=data

def validate_image(meta,data):
    meta=dict(meta)
    if meta['estado']!='recebido': return meta
    if not meta.get('content_type','').startswith('image/'):
        return dict(meta,estado='tipo_nao_imagem')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error',Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as im:
                width,height=im.size; im.verify()
            with Image.open(io.BytesIO(data)) as im: im.load()
        meta.update(largura=width,altura=height,sha256=hashlib.sha256(data).hexdigest())
        meta['estado']='valida' if min(width,height)>=100 else 'miniatura_insuficiente'
    except Exception as e: meta.update(estado='imagem_invalida',erro=str(e))
    return meta

def candidates(originals):
    out=[(u,'observada') for u in dict.fromkeys(originals)]
    for u in originals:
        base=u.rsplit('/',1)[0]
        for size in ('small.jpg','medium.jpg','big.jpg'):
            v=base+'/'+size
            if v not in [x[0] for x in out]: out.append((v,'hipotese_nao_documentada'))
    return out

def audit_sample(products,fetch,out,limit):
    from urllib.robotparser import RobotFileParser
    robots_meta,body=fetch.get('https://'+ALBUM_HOST+'/robots.txt',1024*1024)
    permission=True
    if robots_meta.get('http')==200:
        parser=RobotFileParser(); parser.parse(body.decode('utf-8',errors='replace').splitlines()); permission=parser
    elif robots_meta.get('http')!=404: permission=False
    image_rows=[]; album_rows=[]
    for p in products[:limit]:
        allowed=permission is True or (permission and permission.can_fetch(UA,p['album_url']))
        if allowed: meta,body=fetch.get(p['album_url'],5*1024*1024)
        else: meta,body={'estado':'nao_consultado_robots_indisponivel_ou_negado'},b''
        parsed=AlbumHTML()
        if meta.get('http')==200 and meta.get('content_type')=='text/html':
            parsed.feed(body.decode('utf-8',errors='replace'))
        actual=dict(parsed.photos)
        source={photo_id(u):[u] for u in p['imagens_origem_csv']}
        for key,values in actual.items(): source[key]=values+source.get(key,[])
        p['status_album']=meta['estado']; p['associacao_album_verificada']=bool(actual)
        p['titulo_album_observado']=parsed.title
        album_rows.append(dict(album_id=p['album_id'],url=p['album_url'],titulo=parsed.title,atributos=dict(parsed.attrs_seen),fotos_observadas=len(actual),**meta))
        selected=[]; hashes=set()
        for identity,origins in source.items():
            variants=[]
            for u,kind in candidates(origins):
                m,data=fetch.get(u); m=validate_image(m,data)
                record=dict(album_id=p['album_id'],foto_id=identity,url=u,origem_variante=kind,associacao_observada=identity in actual,**m)
                image_rows.append(record)
                if m['estado']=='valida': variants.append((m['largura']*m['altura'],m['bytes'],u,m,data))
            if variants:
                _,_,u,m,data=max(variants,key=lambda v:(v[0],v[1]))
                if identity in actual and m['sha256'] not in hashes:
                    hashes.add(m['sha256']); local=Path('imagens')/(m['sha256']+'.img'); (out/local).parent.mkdir(exist_ok=True); (out/local).write_bytes(data)
                    selected.append({'url':u,'arquivo_local':str(local),'largura':m['largura'],'altura':m['altura'],'sha256':m['sha256'],'foto_id':identity})
        p['imagens']=selected; p['imagem_capa']=selected[0]['url'] if selected else None
        p['status']='validado_tecnicamente_revisao_visual_pendente' if selected else 'pendente_validacao'
        observed_fingerprint=json.dumps({'title':parsed.title,'photos':actual},sort_keys=True)
        p['fingerprint_album']=hashlib.sha256(observed_fingerprint.encode()).hexdigest() if actual else None
    return {'robots':robots_meta,'albuns':album_rows,'imagens':image_rows,'contagem_estados':dict(Counter(r['estado'] for r in image_rows))}

def csv_write(path,rows):
    if not rows: path.write_text('',encoding='utf-8'); return
    fields=list(dict.fromkeys(k for r in rows for k in r))
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
        for row in rows:
            clean={k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in row.items()}
            w.writerow({k:"'"+v if isinstance(v,str) and v.startswith(('=','+','-','@')) else v for k,v in clean.items()})

def main():
    """Compatibilidade com o comando original, agora usando estado incremental v2."""
    import sys
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs',default='inputs'); parser.add_argument('--out',default='saida')
    parser.add_argument('--online',action='store_true'); parser.add_argument('--limit',type=int,default=10)
    parser.add_argument('--overrides',default='edicoes_manuais.json')
    args=parser.parse_args()
    argv=['sincronizar.py','online' if args.online else 'arquivos','--inputs',args.inputs,'--out',args.out,'--limit',str(args.limit),'--edits',args.overrides]
    from sincronizar import main as synchronize
    original=sys.argv
    try:
        sys.argv=argv
        return synchronize()
    finally: sys.argv=original

if __name__=='__main__': raise SystemExit(main())
