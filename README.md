# LX Mantos — importador e integração v2

**Estado: desenvolvimento e integração local testados; validação real das fotografias bloqueada. Não está pronto para alimentar produção.** Os 30 produtos vêm dos CSVs fornecidos; não há fotos reais disponíveis localmente. O número informado está em `config_site.json`: `559491272126`, preservado exatamente sem acrescentar dígitos. Falta configurar o domínio da LX.

O pacote anterior está preservado: entradas originais em `inputs/`, resultados v1 em `saida/` e código/relatório v1 em `versao1/`. Funções de limpeza, validação de imagens e auditoria do importador anterior são reutilizadas pela v2. O comando antigo `importador.py` agora encaminha à sincronização incremental. A Gran Medical não é usada como site da LX nem foi modificada.

## Instalação portátil

Python 3.11+:

```sh
cd lx-mantos
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests -v
```

No Windows use `.venv\Scripts\python.exe`. Não há API paga ou credenciais obrigatórias para processar exportações.

## Importar os CSVs existentes

```sh
.venv/bin/python sincronizar.py arquivos --inputs inputs --out catalogo
```

`catalogo/estado.json` guarda o estado por ID de álbum. `produtos.json` e `produtos.csv` são saídas para integração. `ultima_execucao.json` e `historico/` guardam evidências e alterações. Preserve a pasta inteira, especialmente `imagens/` e `estado.json`, ao migrar o ambiente. Os CSVs de origem e os dados anteriores são mantidos; ausência numa atualização nunca remove um produto. Somente uma sincronização por pasta é permitida; não remova `.sync.lock` de um processo ativo.

Sem imagens novas válidas, mantém as referências e os arquivos anteriores e registra que a atualização não teve evidência nova. Arquivos locais são novamente decodificados e comparados por hash antes do uso. Imagens inexistentes/corrompidas não aparecem no site. Categorias de origem são acumuladas em consultas parciais; remoções precisam de decisão explícita futura. Não há exclusão automática, estoque ou preços inferidos.

Decisões comerciais devem ficar em `edicoes_manuais.json`, por ID, como no arquivo de exemplo. Campos permitidos: nome_pt, categoria, preco, descricao, ativo. São guardadas no estado e preservadas quando o arquivo de edições não aparece numa atualização futura. Para alterar uma decisão persistida, informe novo valor explicitamente. Não edite campos gerados diretamente.

## Alternativa autorizada: arquivos do fornecedor

O formato está em `manifesto_fornecedor.exemplo.json`. `manifesto_pendente.json` já mapeia os 30 álbuns e as 90 referências para nomes de arquivos esperados. **É apenas um mapa pendente, não uma exportação validada do fornecedor.**

1. Solicite ao fornecedor uma exportação autorizada com fotos originais e o mapa álbum → arquivos, ou faça uma exportação manual permitida no ambiente em que você já tem acesso. Não use cookies de terceiros nem contorne bloqueios.
2. Coloque fotos numa pasta ao lado do manifesto. Confirme o ID e o nome de cada camisa, as categorias e os caminhos dos arquivos; ajuste extensões reais. Preencha `origem` com identificação e data da exportação. Não associe fotografias apenas por posição numa lista ou semelhança de nomes.
3. Execute:

```sh
.venv/bin/python sincronizar.py arquivos --inputs inputs --manifest entrega_fornecedor/manifesto.json --out catalogo
```

Todos os arquivos são decodificados, medidos e registrados por SHA-256. Arquivos inválidos são reportados; caminhos fora da pasta da entrega e IDs divergentes são recusados. Fotos repetidas são deduplicadas, e um mesmo hash ou foto_id em álbuns diferentes exige revisão e interrompe a importação. Variantes da mesma foto são comparadas por área e bytes; a maior válida prevalece. A associação é marcada `manifesto_fornecedor_declarado`, distinta de `html_album`. Decodificar a foto não prova que ela é a camisa correta: a conferência visual continua necessária.

É possível começar com um manifesto contendo somente um produto real e expandir após conferir a amostra. Não há necessidade de acesso ao Yupoo para processar arquivos locais. Futuras consultas online usam o mesmo album_id, preservando as decisões do lojista.

## Teste mínimo em outro ambiente autorizado

O proxy deste ambiente retorna `Tunnel connection failed: 403 Forbidden` para a categoria e as fotos; o controle npm respondeu 200. Veja `conectividade.json`. O erro ocorre no CONNECT antes da resposta do Yupoo; não é evidência de bloqueio emitido pelo fornecedor, imagem quebrada ou falta de Internet geral.

Copie este pacote para uma máquina que tenha acesso autorizado, instale as dependências e execute:

```sh
.venv/bin/python sincronizar.py online --inputs inputs --out catalogo --category https://minkang.x.yupoo.com/categories/712891 --limit 10 --max-pages 3
```

Para múltiplas categorias, repita `--category` com cada URL autorizada. A paginação segue links observados somente na mesma categoria e domínio. Há limite global de 10 álbuns e limite de páginas por categoria: é uma amostra, não uma sincronização completa do fornecedor. O suporte a paginação e seletores foi testado com fixtures; precisa ser conferido contra o HTML real. Se a página exigir JavaScript, autenticação ou usar outro markup, registrar a limitação e adaptar com base em HTML autorizado, sem presumir completude.

O importador consulta robots.txt, respeita suas regras e para por domínio em 401/403/429. Não utiliza outra rota para escapar ao proxy. O coletor de categorias herda o limitador e o bloqueio do mesmo cliente. Salva evidências em `catalogo/ultima_execucao.json`. Fotos dos álbuns são verificadas por HTTP, Content-Type, bytes, decodificação e dimensões; hipóteses small/medium/big ficam identificadas e não são tratadas como observadas.

**Retorno 2 no modo online significa validação incompleta.** Retorno 0 no modo arquivos significa apenas processamento local concluído; consulte as contagens e os estados. Nenhum retorno libera publicação automaticamente. O seletor de galeria ainda precisa de confirmação ao acessar o HTML real. Confira os 10 produtos visualmente, dimensões e vínculo com os álbuns. Se houver restrição do fornecedor, pare e use a exportação autorizada.

## Site próprio e revisão

```sh
.venv/bin/python gerar_site.py --preview --data catalogo --out site-revisao-novo
.venv/bin/python -m http.server 8000 --directory site-revisao-novo
```

Acesse pelo navegador na máquina que está executando o servidor. O diretório de saída deve ser novo; isso evita sobrescrever revisão anterior e manter páginas antigas. A base LX usa interface própria em português, independente da Gran Medical. Há busca, filtros por múltiplas categorias, paginação de 12 itens e páginas `/produtos/{album_id}/`. Não redireciona ao Yupoo; fotos, quando válidas, são copiadas para o próprio site. Se o site LX original for fornecido no futuro, integrar estes dados e as rotas preservando seu design, Hero, vídeo e animações em branch separada. A interface deste pacote não pretende reproduzir um design ao qual não tivemos acesso.

P/M/G/GG preenchem a mensagem com nome, ID e tamanho para `559491272126`. O domínio configurado acrescenta a URL própria do produto. Enquanto o domínio estiver vazio, o rascunho gera mensagem sem URL, sem inventar um domínio. Não foi enviado WhatsApp durante os testes. Produtos infantis exigem conferência da grade antes de oferecer equivalência comercial dos tamanhos.

## Liberar produção após validação real

1. Revise visualmente cada foto. Crie `aprovacoes.json` com o ID, nome do revisor e **a lista exata de hashes** das fotos aprovadas. Exemplo de formato, sem aprovação real:

```json
{"257728051":{"revisor":"NOME DO RESPONSÁVEL","sha256":["HASH REAL COPIADO DE catalogo/produtos.json"]}}
```

2. Em `edicoes_manuais.json`, marque `ativo: true` somente para o produto aprovado. Confirme categorias, nome e grade infantil. Preços permanecem nulos até serem administrados pela LX; o adaptador atual não exibe preços.
3. Preencha `base_url` em `config_site.json` com a origem HTTPS real da LX. Mantenha o WhatsApp fornecido ou corrija-o explicitamente, se necessário.
4. Reexecute a sincronização local sem novos dados para aplicar decisões ao estado. Isso não remove produtos:

```sh
.venv/bin/python sincronizar.py arquivos --out catalogo
.venv/bin/python gerar_site.py --data catalogo --out site-producao-novo
```

O gerador exige domínio e WhatsApp válidos e só inclui produtos ativos com fotos decodificadas e hashes aprovados. Revalida os arquivos; não confia num `publicavel: true` escrito manualmente no JSON. Fotos alteradas perdem aprovação. Falhas de rede preservam fotos locais anteriormente verificadas e sua evidência histórica; isso não significa nova confirmação no fornecedor. Não há deploy automático. Publique os arquivos somente após revisão da LX.

## Testes e limitações

`testes_python.log`: 14 testes locais, incluindo seleção de resolução, preservação incremental, múltiplas categorias, paginação com ciclos, duplicados, caminhos indevidos e gate de publicação. As imagens desses testes são fixtures geradas e não entram no catálogo entregue.

`teste_navegador.json`: Chromium executou busca, filtro Infantil, paginação, rotas próprias e as quatro mensagens de tamanho com os 30 produtos dos CSVs. A página mostrou fotografia pendente, pois não há foto real validada. O teste é repetível com Node, Chromium e playwright-core. No ambiente atual:

```sh
node tests/navegador.cjs /workspace/lx-mantos/site-revisao-v3 /workspace/lx-mantos/teste_navegador.json
```

O script usa ferramentas de navegador instaladas neste ambiente; em outra máquina adapte o caminho de playwright-core, Chromium e Python. Os 14 testes Python e a importação são portáteis. A consulta real ao fornecedor não foi substituída por teste simulado. Falta receber fotos reais ou liberar acesso autorizado, concluir revisão visual e configurar o domínio para atingir o critério de produção.
