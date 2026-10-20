# Migração para OctaviOR-end/LX-Mantos

O pacote LX Mantos v2 foi copiado integralmente para uma cópia de trabalho Git independente, sem alterações no checkout da Gran Medical ou na pasta original `/workspace/lx-mantos`.

Inclui código, frontend, testes, CSVs originais, JSON/CSV gerados, estado incremental, históricos, documentação e evidências de testes. O relatório `testes_python.log` foi preservado como `relatorios/testes_python.txt`. Dependências instaladas, caches e arquivos transitórios foram excluídos. O WhatsApp em `config_site.json` é o contato comercial informado pelo usuário; não é uma credencial. O domínio permanece sem configuração.

Para um novo ambiente:

```sh
git clone https://github.com/OctaviOR-end/LX-Mantos.git
cd LX-Mantos
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python gerar_site.py --preview --data catalogo --out site-revisao-local
```

Os caminhos absolutos de evidências e comandos do ambiente anterior são históricos. Use a raiz do clone atual nos comandos. O teste de navegador exige adaptar os caminhos locais do Python, Chromium e playwright-core, conforme README.md.

Estado de validação preservado: 30 produtos provenientes dos CSVs; nenhuma foto real do fornecedor validada, devido à recusa CONNECT 403 do proxy anterior. A migração para GitHub não valida o acesso ao Yupoo nem publica um site. Consulte RELATORIO_V2.md antes de usar os dados em produção.
