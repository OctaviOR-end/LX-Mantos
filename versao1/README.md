# LX Mantos — importador independente

Entrega em rascunho: 30 álbuns organizados. **A validação real das imagens está bloqueada pelo proxy do ambiente (403).** Não há imagens comprovadamente válidas nem catálogo liberado para publicação. Veja `RELATORIO.md` e `saida/auditoria.json`.

## Atualizar

Python 3.11 ou superior e Pillow. Apenas bibliotecas gratuitas; não usa API paga de tradução.

```sh
cd /workspace/lx-mantos
python -m venv .venv
.venv/bin/python -m pip install --cache-dir /workspace/.pip-cache -r requirements.txt
.venv/bin/python -m unittest discover -s tests -v
# Limpeza local: nenhuma consulta ao fornecedor.
.venv/bin/python importador.py --out saida_offline
# Amostra online (máximo 10; exige acesso autorizado aos dois domínios).
.venv/bin/python importador.py --online --limit 10 --out saida
```

Retorno 0: exportação local concluída, ou amostra com ao menos uma foto associada por produto. Retorno 2 na execução online: algum produto continua sem foto validada/associada. Mesmo retorno 0 não substitui inspeção visual, confirmação de completude da galeria e revisão comercial.

Coloque novos CSVs com as mesmas colunas em `inputs/`. Mantenha somente as versões de entrada desejadas; títulos divergentes são reportados e a primeira versão em ordem alfabética prevalece. Não inventamos vínculos para linhas sem álbum. Todas as entradas são consolidadas por ID numérico original. Não há importação em massa pela rede.

Para preservar decisões comerciais, copie `edicoes_manuais.exemplo.json` para `edicoes_manuais.json` e edite esse arquivo. Pode substituir nome_pt, categoria, preco, descricao e ativo por ID. Esse arquivo nunca é regravado pelo importador. Não edite os arquivos gerados: eles são reconstruídos em cada execução. Preços continuam nulos até a LX informá-los. Não foi criado número de WhatsApp ou domínio fictício.

## Arquivos gerados

- `produtos.csv` (UTF-8 com BOM) e `produtos.json`: 30 produtos; listas e objetos são JSON dentro das células CSV.
- `amostra.csv` e `amostra.json`: primeiros 10 produtos, na ordem de entrada.
- `diagnostico.json` e `rejeitados.csv`: análise dos três originais e linhas sem álbum.
- `imagens_auditoria.csv` e `auditoria.json`: resultados por variante/foto/álbum, HTTP, tipo, bytes, dimensões e hash quando disponíveis.
- `resumo.json`: contagens da execução e data em UTC.
- `inspecao.html`: abra o arquivo no navegador. Usa somente cópias locais de fotos validadas e associadas; por isso está sem fotografias enquanto a rede estiver bloqueada.

`imagens_origem_csv` preserva referências não verificadas. `imagens` só recebe fotos decodificadas e encontradas no álbum consultado. Não use o primeiro campo para publicar. `publicavel` permanece falso: inspeção humana ainda é necessária. A categoria Torcedor não é inferida apenas pela ausência de “Player Version”. Produtos infantis mantêm P/M/G/GG como opções de consulta, com aviso para conferir a grade original.

## Como a validação funciona

Consulta robots.txt antes dos álbuns; se indisponível ou negado, não prossegue com scraping dos álbuns. Extrai `src`, `data-src`, `srcset`, `data-srcset`, `data-origin-src`, `data-original`, `data-big` e `href` somente de elementos reconhecidos como galeria. Marcadores suportados: image__img, image__main, showalbum__image, album__photo e atributos de imagem original. O seletor ainda precisa ser confirmado contra o HTML real do fornecedor. Nenhuma galeria reconhecida significa validação pendente, não sucesso.

Para **cada** identidade de foto, inclui URLs observadas e hipóteses small.jpg, medium.jpg e big.jpg; não presume que existam. Variantes experimentais estão identificadas no relatório. Escolhe a maior área decodificada entre as respostas válidas, com fallback para versões menores. Exige Content-Type image/*, decodificação completa e ambos os lados de ao menos 100 pixels. Rejeita HTML e arquivos corrompidos; limita bytes e usa proteção do Pillow contra imagens excessivas. Elimina URLs repetidas e conteúdo idêntico por hash. TLS permanece habilitado.

Após 401/403/429, suspende novas requisições ao domínio. Não utiliza proxies alternativos, cookies de terceiros ou contorno de bloqueios. Uma recusa do proxy não prova que a imagem esteja quebrada. O HTML é uma evidência de associação técnica; a correspondência visual da camisa e os direitos de uso exigem conferência humana.

`fingerprint_album` detecta mudanças no título e URLs reconhecidas; `ultimo_fingerprint_confirmado` preserva a última evidência quando uma consulta futura falha. Isso não identifica todos os tipos de alteração no fornecedor. Cada execução revalida as imagens da amostra, registra SHA-256 e recria a seleção. Não descarta arquivos de fotos antigas automaticamente. Não mantém fotos antigas como se tivessem sido validadas na execução atual.

## Integração proposta

O único repositório disponível é da Gran Medical, não da LX Mantos; seu design não foi alterado. Quando o repositório correto estiver disponível, trabalhar em branch separada e conectar um adaptador de leitura ao JSON, preservando Hero, vídeo e animações. Usar `/produtos/{album_id}` como rota estável; galeria deve ler somente imagens aprovadas, com cópias em armazenamento autorizado da LX para evitar dependência de hotlink.

Na página do produto: nome, categoria, fotos, tamanhos P/M/G/GG, aviso de disponibilidade e botão de consulta. Com o número real configurado pela LX, montar o link WhatsApp com `encodeURIComponent` de nome, ID, tamanho e URL absoluta do produto. Não criar checkout ou estoque. Mostrar preço somente quando cadastrado pela LX. Revisão comercial e publicação continuam manuais; `ativo` sozinho não libera fotos pendentes. Nenhuma mudança foi publicada.
