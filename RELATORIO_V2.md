# LX Mantos — evidências da continuação

## Resultado

A v2 entrega importação incremental e alternativa por arquivos, mais um adaptador de site próprio. **Não é uma integração pronta para produção: continuam faltando fotografias reais validadas e domínio LX.** O pacote v1 foi reaproveitado, mantido e corrigido; Gran Medical não foi modificada.

## O que foi observado de verdade

- Os três CSVs consolidam 30 IDs de álbum, 90 referências de fotos e 5 registros rejeitados por ausência de álbum. Original, diagnóstico e rejeitados v1 permanecem no pacote.
- Categoria `https://minkang.x.yupoo.com/categories/712891`, robots.txt e uma referência real de `photo.yupoo.com` falharam com `URLError: Tunnel connection failed: 403 Forbidden`.
- O mesmo processo acessou `https://registry.npmjs.org/bun/latest` e recebeu HTTP 200. Portanto, existe Internet externa e o impedimento está no CONNECT do proxy para os domínios Yupoo, antes de resposta da origem. O proxy não informa a causa administrativa exata: allowlist não aplicada, política ou outro bloqueio de egress. Não é possível atribuir a recusa ao fornecedor com essa evidência.
- Nenhuma tentativa de acesso direto, proxy alternativo ou contorno foi realizada.
- A execução online v2 retornou 2. O estado continua com 30 produtos e zero imagens utilizáveis/publicáveis. Veja `catalogo/ultima_execucao.json` e o histórico.
- Chromium abriu o catálogo com dados reais dos CSVs e verificou HTTP 200, 12 itens por página, segunda página, filtro Infantil com 5 itens, busca, rota interna e mensagem de cada tamanho para o telefone informado. Não enviou mensagens. Não carregou fotografias reais; mostrou a pendência explicitamente.

## Mudanças implementadas e verificadas localmente

- Estado persistente por álbum, histórico, detecção de mudanças de metadados e de hashes de fotos. Produto ausente de uma atualização permanece no estado. Falha ou ausência de novas fotos não apaga o conjunto anterior.
- Edições comerciais separadas e persistidas. Arquivos são revalidados antes de usá-los. Aprovação visual vinculada aos hashes exatos, invalidada quando o conteúdo muda.
- Manifesto do fornecedor com arquivos locais, identificação da procedência e vínculo declarado álbum/foto. Bloqueia caminhos fora da entrega, IDs inconsistentes, duplicação de álbuns e referências de uma mesma foto em camisas diferentes. Decodifica variantes e seleciona maior resolução válida.
- Descoberta de múltiplas categorias e links de paginação no mesmo domínio, com deduplicação de álbuns, limite de páginas e amostra global de 10. Categorias são acumuladas; amostra não é declarada catálogo completo. Seletores e paginação ainda dependem de confirmação em HTML real do Yupoo.
- Site estático independente da Gran Medical: português brasileiro, categorias, busca, paginação, galeria local e páginas próprias `/produtos/{id}/`; P/M/G/GG preenchem WhatsApp. Número `559491272126` fornecido pelo usuário; nenhum dígito foi acrescentado. Falta domínio. A mensagem do rascunho funciona sem inventar URL, e produção exige domínio real.
- Exportação de produção requer fotos revisadas, produto explicitamente ativo e dados de contato configurados. Não há estoque, checkout, preço inferido ou deploy automático.

**14 testes Python passaram.** Testes com fotos geradas validam comportamento do código, não produtos reais. A integração no Chromium passou com metadados reais e ausência explicitamente sinalizada de fotografias. O manifesto de 30 produtos gerado é mapa de referência, não evidência de associação validada. A inspeção visual e os direitos de uso dependem dos arquivos do fornecedor e da LX.

## Procedimento mínimo restante

Em uma máquina com acesso autorizado: instalar `requirements.txt` e executar a amostra online indicada no README. Se o Yupoo restringir acesso, parar. Alternativamente, obter do fornecedor um manifesto e as fotos reais de um produto, importar com `sincronizar.py arquivos --manifest ...`, conferir o vínculo visual e verificar as dimensões no JSON. Depois ampliar para até 10 produtos, aprovar hashes, configurar domínio e gerar a saída de produção. O README traz todos os comandos.

A entrega não depende de mexer no site Gran Medical. O repositório original da LX ainda não foi disponibilizado; a base independente e o contrato JSON estão preparados para futura incorporação sem reconstruir seu Hero ou suas animações. Nenhum conteúdo foi publicado.
