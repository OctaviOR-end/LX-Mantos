import io, json, tempfile, unittest
from pathlib import Path
from PIL import Image
from importador import (AlbumHTML, canonical, candidates, validate_image, load_inputs,
                       audit_sample, ALBUM_HOST, IMAGE_HOST, title_pt)


def image(size=(600,800)):
    b=io.BytesIO(); Image.new('RGB',size,'red').save(b,format='JPEG'); return b.getvalue()

class ImportTests(unittest.TestCase):
    def test_input_merge_rejects_five_missing_links(self):
        products,d=load_inputs(Path(__file__).resolve().parents[1]/'inputs')
        self.assertEqual(len(products),30)
        self.assertEqual(len({p['album_id'] for p in products}),30)
        self.assertEqual(len(d['rejeitados']),5)
        self.assertEqual(sum(x['variantes_grandes_parciais'] for x in d['arquivos']),29)
        self.assertTrue(all(not p['imagens'] for p in products))

    def test_untrusted_urls_and_cross_supplier_rejected(self):
        for u in ['http://photo.yupoo.com/minkang/a/small.jpg','https://evil.test/x.jpg','https://photo.yupoo.com/other/a/small.jpg','https://user@photo.yupoo.com/minkang/a/small.jpg']:
            with self.assertRaises(ValueError): canonical(u,IMAGE_HOST)
        self.assertEqual(canonical('//photo.yupoo.com/minkang/a/small.jpg',IMAGE_HOST),'https://photo.yupoo.com/minkang/a/small.jpg')

    def test_html_and_truncated_images_rejected(self):
        self.assertEqual(validate_image({'estado':'recebido','content_type':'text/html'},b'<html>Error</html>')['estado'],'tipo_nao_imagem')
        self.assertEqual(validate_image({'estado':'recebido','content_type':'image/jpeg'},b'<html>Error</html>')['estado'],'imagem_invalida')
        self.assertEqual(validate_image({'estado':'recebido','content_type':'image/jpeg'},image()[:100])['estado'],'imagem_invalida')

    def test_dimensions_decode_and_tiny_thumbnail(self):
        m=validate_image({'estado':'recebido','content_type':'image/jpeg'},image())
        self.assertEqual((m['largura'],m['altura']),(600,800)); self.assertEqual(m['estado'],'valida')
        self.assertEqual(validate_image({'estado':'recebido','content_type':'image/jpeg'},image((30,30)))['estado'],'miniatura_insuficiente')

    def test_all_photos_get_candidates(self):
        for key in ('a','b','c'):
            c=candidates(['https://photo.yupoo.com/minkang/'+key+'/small.jpg'])
            self.assertEqual(len(c),3); self.assertTrue(any(u.endswith('/big.jpg') for u,_ in c))

    def test_gallery_attributes_exclude_avatar(self):
        p=AlbumHTML(); p.feed('<img src="https://photo.yupoo.com/minkang/avatar/small.jpg"><img class="image__img" src="//photo.yupoo.com/minkang/a/small.jpg" data-origin-src="//photo.yupoo.com/minkang/a/big.jpg" srcset="//photo.yupoo.com/minkang/a/medium.jpg 600w, //photo.yupoo.com/minkang/a/big.jpg 1200w">')
        self.assertEqual(len(p.photos),1); self.assertEqual(len(next(iter(p.photos.values()))),3)

    def test_live_pipeline_contract_with_fixture_not_network(self):
        # Fixture only: proves selection/fallback and association, never supplier availability.
        class Fixture:
            def get(self,url,limit=None):
                if url.endswith('robots.txt'): return {'estado':'recebido','http':200},b'User-agent: *\nAllow: /'
                if '/albums/' in url:
                    body=b'<title>Fixture</title><img class="image__img" src="//photo.yupoo.com/minkang/a/small.jpg"><img class="image__img" src="//photo.yupoo.com/minkang/b/small.jpg">'
                    return {'estado':'recebido','http':200,'content_type':'text/html'},body
                if '/a/big.jpg' in url: return {'estado':'http_invalido','http':404},b''
                size=(800,1200) if url.endswith('big.jpg') else (400,600) if url.endswith('medium.jpg') else (120,180)
                data=image(size); return {'estado':'recebido','http':200,'content_type':'image/jpeg','bytes':len(data)},data
        p={'album_id':'1','album_url':'https://'+ALBUM_HOST+'/albums/1','imagens_origem_csv':['https://photo.yupoo.com/minkang/a/small.jpg','https://photo.yupoo.com/minkang/b/small.jpg','https://photo.yupoo.com/minkang/wrong/small.jpg']}
        with tempfile.TemporaryDirectory() as folder:
            audit=audit_sample([p],Fixture(),Path(folder),1)
            self.assertEqual(len(p['imagens']),2)
            self.assertTrue(p['imagens'][0]['url'].endswith('/a/medium.jpg'))
            self.assertTrue(p['imagens'][1]['url'].endswith('/b/big.jpg'))
            self.assertTrue(all('/wrong/' not in x['url'] for x in p['imagens']))
            self.assertEqual(len(audit['imagens']),9)

    def test_portuguese_glossary(self):
        name=title_pt('Argentina 2026 White and Blue Polo JerseyS-XXL')
        self.assertNotIn('XXL',name); self.assertIn('Branca e Azul',name)

if __name__=='__main__': unittest.main()
