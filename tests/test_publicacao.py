"""Apenas fixtures de pipeline; não são fotografias de produto do fornecedor."""
import io,json,tempfile,unittest
from pathlib import Path
from PIL import Image
from sincronizar import read_manifest,merge,verify_and_approve
from gerar_site import build

class PublicationTests(unittest.TestCase):
 def test_largest_local_variant_and_production_page(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td); out=root/'catalogo';out.mkdir()
   for name,size in [('small',(120,180)),('big',(800,1200))]:
    b=io.BytesIO();Image.new('RGB',size,'red').save(b,'JPEG');(root/(name+'.jpg')).write_bytes(b.getvalue())
   manifest={'origem':'FIXTURE TESTE, não fornecedor','produtos':[{'album_id':'1','album_url':'https://minkang.x.yupoo.com/albums/1','nome_original':'Fixture Jersey','categorias':['Teste'],'imagens':[{'foto_id':'fixture-photo','arquivo':'small.jpg'},{'foto_id':'fixture-photo','arquivo':'big.jpg'}]}]}
   path=root/'m.json';path.write_text(json.dumps(manifest));products,events=read_manifest(path,out)
   self.assertEqual(len(products[0]['imagens']),1);self.assertEqual(products[0]['imagens'][0]['largura'],800)
   state,_=merge({},products,{'1':{'ativo':True}})
   approval={'1':{'revisor':'TESTE FIXTURE','sha256':[state['1']['imagens'][0]['sha256']]}}
   (out/'produtos.json').write_text(json.dumps(list(state.values())))
   self.assertEqual(build(out,root/'site',{'whatsapp':'559491272126','base_url':'https://lx.example'},False,approval),1)
   page=(root/'site/produtos/1/index.html').read_text();self.assertIn('<img src="/imagens/',page)
   self.assertNotIn('yupoo',page);self.assertNotIn('Fotografia pendente',page)
   self.assertTrue(list((root/'site/imagens').glob('*.jpg')))

if __name__=='__main__':unittest.main()
