// Testa integração no Chromium. Não envia mensagens nem faz navegação ao WhatsApp.
const { chromium } = require('/opt/codex/cua_node/lib/node_modules/playwright-core');
const { spawn } = require('child_process');
const fs = require('fs');
const assert = require('assert/strict');
(async () => {
 const root = process.argv[2]; const report = process.argv[3];
 const server = spawn('/workspace/lx-mantos/.venv/bin/python', ['-m','http.server','8766','--bind','127.0.0.1','--directory',root], {stdio:'ignore'});
 let browser;
 try {
  browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
  const page=await browser.newPage({viewport:{width:1280,height:900}});
  const errors=[]; page.on('pageerror',e=>errors.push(e.message));
  const res=await page.goto('http://127.0.0.1:8766/'); assert.equal(res.status(),200);
  assert.equal(await page.locator('html').getAttribute('lang'),'pt-BR');
  assert.equal(await page.locator('#grade article').count(),12);
  assert.match(await page.locator('#contagem').textContent(),/30 produto/);
  await page.locator('#proxima').click(); assert.match(await page.locator('#contagem').textContent(),/Página 2/);
  await page.locator('#categoria').selectOption('Infantil'); assert.equal(await page.locator('#grade article').count(),5);
  await page.locator('#categoria').selectOption('');
  await page.locator('#busca').fill('Argentina');
  assert.ok(await page.locator('#grade article').count()>0);
  await page.locator('#grade article a').first().click();
  assert.match(new URL(page.url()).pathname,/^\/produtos\/\d+\/$/);
  assert.equal(await page.locator('input[name=tamanho]').count(),4);
  assert.equal(await page.locator('#whatsapp').getAttribute('aria-disabled'),'true');
  for (const size of ['P','M','G','GG']) {
   await page.locator(`input[value="${size}"]`).check();
   const href=await page.locator('#whatsapp').getAttribute('href');
   const url=new URL(href); assert.equal(url.hostname,'wa.me'); assert.equal(url.pathname,'/559491272126');
   assert.match(url.searchParams.get('text'),new RegExp(`tamanho ${size}\\.`));
   assert.match(url.searchParams.get('text'),/referência \d+/); assert.ok(!href.includes('yupoo'));
  }
  assert.equal(await page.locator('.galeria img').count(),0);
  assert.match(await page.locator('.galeria').textContent(),/pendente/);
  await page.screenshot({path:report.replace('.json','.png'),fullPage:true});
  assert.deepEqual(errors,[]);
  fs.writeFileSync(report,JSON.stringify({resultado:'passou',dados:'30 produtos reais dos CSVs; nenhuma fotografia real disponível',checks:['HTTP 200','12 itens por página','paginação','filtro Infantil 5 itens','busca','rota própria do produto','4 tamanhos','mensagem WhatsApp com número informado, nome, ID e tamanho','estado de fotografia pendente','sem erros JS'],mensagem_enviada:false},null,2));
  console.log('Chromium: integração com metadados reais passou; fotos reais indisponíveis.');
 } finally {if(browser) await browser.close(); server.kill();}
})().catch(e=>{console.error(e);process.exit(1)});
