"""Testes com fixtures, sem representar disponibilidade real do fornecedor."""
import copy, io, json, tempfile, unittest
from pathlib import Path
from PIL import Image
from sincronizar import (base_product, merge, read_manifest, verify_and_approve,
                         discover, category_url, local_file, atomic)
from gerar_site import build, config_validate

def jpeg(color='red'):
    b=io.BytesIO(); Image.new('RGB',(600,800),color).save(b,'JPEG'); return b.getvalue()

class IncrementalTests(unittest.TestCase):
    def test_retains_unseen_products_and_failed_photos_and_edits(self):
        a=base_product('1','Argentina Jersey'); a['imagens']=[{'sha256':'abc','arquivo_local':'imagens/a.jpg'}]
        old,changes=merge({},[a,base_product('2','Spain Jersey')],{'1':{'nome_pt':'Nome do lojista','preco':100}})
        current,changes=merge(old,[base_product('1','Argentina Jersey')],{})
        self.assertEqual(len(current),2); self.assertEqual(current['1']['imagens'],a['imagens'])
        self.assertEqual(current['1']['nome_pt'],'Nome do lojista'); self.assertEqual(current['1']['preco'],100)
        self.assertIn('preservadas',current['1']['validacao_atual'])
        again,_=merge(current,[],{}); self.assertEqual(set(again),{'1','2'})

    def test_manifest_real_decode_and_hash_approval_revoked_on_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); output=root/'output'; output.mkdir(); (root/'foto.jpg').write_bytes(jpeg())
            manifest={'origem':'FIXTURE: não é produto real','produtos':[{'album_id':'1','album_url':'https://minkang.x.yupoo.com/albums/1','nome_original':'Argentina Jersey','categorias':['Argentina','Torcedor'],'imagens':[{'arquivo':'foto.jpg','foto_id':'a'}]}]}
            path=root/'manifesto.json'; path.write_text(json.dumps(manifest))
            products,events=read_manifest(path,output); self.assertEqual(events[0]['estado'],'valida')
            state,_=merge({},products,{'1':{'ativo':True}}); sha=state['1']['imagens'][0]['sha256']
            verify_and_approve(state,{'1':{'revisor':'Teste','sha256':[sha]}},output); self.assertTrue(state['1']['publicavel'])
            file=output/state['1']['imagens'][0]['arquivo_local']; file.write_bytes(jpeg('blue'))
            errors=verify_and_approve(state,{'1':{'revisor':'Teste','sha256':[sha]}},output)
            self.assertFalse(state['1']['publicavel']); self.assertTrue(errors)

    def test_manifest_rejects_traversal_duplicates_and_wrong_album(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); (root/'foto.jpg').write_bytes(jpeg()); out=root/'out'; out.mkdir()
            row={'album_id':'1','album_url':'https://minkang.x.yupoo.com/albums/1','nome_original':'Fixture','imagens':[{'arquivo':'foto.jpg','foto_id':'a'}]}
            path=root/'m.json'
            for products in ([row,row],[dict(row,album_url='https://minkang.x.yupoo.com/albums/2')],[dict(row,imagens=[{'arquivo':'../outside.jpg'}])],[row,dict(row,album_id='2',album_url='https://minkang.x.yupoo.com/albums/2')]):
                path.write_text(json.dumps({'origem':'Fixture','produtos':products}))
                with self.assertRaises(ValueError): read_manifest(path,out)

    def test_category_pagination_dedup_memberships_and_robots(self):
        class Fixture:
            def get(self,url,limit=None):
                if url.endswith('robots.txt'): return {'http':200,'estado':'recebido','content_type':'text/plain'},b'User-agent: *\nAllow: /'
                if 'page=2' in url: body='<a href="/albums/2"><img alt="Germany Jersey"></a><a href="?page=1">1</a>'
                else: body='<a href="/albums/1"><img alt="Argentina Jersey"></a><a href="?page=2">2</a><a href="https://evil.test/categories/1?page=3">fora</a>'
                return {'http':200,'estado':'recebido','content_type':'text/html'},body.encode()
        products,events=discover(['https://minkang.x.yupoo.com/categories/712891','https://minkang.x.yupoo.com/categories/99'],Fixture(),3,10)
        self.assertEqual(len(products),2)
        self.assertEqual(products[0]['categorias_fornecedor'],['712891','99'])
        self.assertLessEqual(sum('url' in e for e in events),7)
        with self.assertRaises(ValueError): category_url('https://evil.test/categories/1')
        class Denied(Fixture):
            def get(self,url,limit=None):
                if not url.endswith('robots.txt'): self.fail('Não consultar quando robots nega')
                return {'http':200,'estado':'recebido','content_type':'text/plain'},b'User-agent: *\nDisallow: /'
        self.assertEqual(discover(['https://minkang.x.yupoo.com/categories/712891'],Denied())[0],[])

    def test_site_requires_real_config_and_reviewed_photos(self):
        with self.assertRaises(ValueError): config_validate({},False)
        with self.assertRaises(ValueError): config_validate({'whatsapp':'559491272126','base_url':'https://minkang.x.yupoo.com'},False)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); data=root/'data'; data.mkdir(); p=base_product('1','Fixture')
            p['publicavel']=True; p['ativo']=True; (data/'produtos.json').write_text(json.dumps([p]))
            with self.assertRaises(ValueError): build(data,root/'site',{'whatsapp':'559491272126','base_url':'https://lx.example'},False,{})
            self.assertFalse((root/'site').exists())
            self.assertEqual(build(data,root/'preview',{},True,{}),1)
            page=(root/'preview/produtos/1/index.html').read_text()
            self.assertIn('Fotografia pendente',page); self.assertNotIn('href="https://minkang',page)

if __name__=='__main__': unittest.main()
