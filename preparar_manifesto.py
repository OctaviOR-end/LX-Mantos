#!/usr/bin/env python3
"""Gera mapa de referência; não baixa fotos nem declara associação verificada."""
import argparse,json
from pathlib import Path
from urllib.parse import urlsplit
from importador import load_inputs
p=argparse.ArgumentParser();p.add_argument('--inputs',default='inputs');p.add_argument('--out',default='manifesto_pendente.json');a=p.parse_args()
products,_=load_inputs(a.inputs)
rows=[]
for product in products:
 images=[]
 for u in product['imagens_origem_csv']:
  photo=urlsplit(u).path.rsplit('/',1)[0]
  images.append({'foto_id':photo,'url_origem':u,'arquivo':f"fotos/{product['album_id']}/{photo.rsplit('/',1)[1]}.jpg"})
 rows.append({'album_id':product['album_id'],'album_url':product['album_url'],'nome_original':product['nome_original'],'categorias':[product['categoria']],'imagens':images})
path=Path(a.out)
if path.exists():p.error('Arquivo já existe; escolha outro destino')
path.write_text(json.dumps({'origem':'PENDENTE: fornecedor deve confirmar vínculos e fornecer arquivos reais','produtos':rows},ensure_ascii=False,indent=2),encoding='utf8')
print(f'{len(rows)} álbuns mapeados; arquivos de imagem ainda não fornecidos')
