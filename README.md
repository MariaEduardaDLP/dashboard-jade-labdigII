# Projeto Jade — dashboard web e coletor serial

O dashboard é publicado no Streamlit Community Cloud. Um coletor Python roda
em um computador Windows conectado à prancha, lê a porta COM e grava eventos
no Supabase. O dashboard busca esses registros do Supabase e atualiza a tela
automaticamente a cada minuto.

> **Atenção à privacidade:** você escolheu disponibilizar dados reais em um
> dashboard público. A política configurada abaixo permite que qualquer pessoa
> com acesso ao projeto consulte a tabela `events` usando a API pública do
> Supabase; ela inclui mensagem e horários de solicitação/atendimento. Não grave
> nomes, identificadores pessoais ou observações livres nessa tabela. Confirme
> com a equipe/responsável que a publicação desses registros está autorizada.
> Para restringir o acesso, é necessário trocar o modelo por autenticação antes
> de publicar dados reais.

## 1. Preparar o Supabase

1. Abra o SQL Editor do seu projeto Supabase.
2. Copie e execute todo o conteúdo de [`database/schema.sql`](database/schema.sql).
   Se já executou uma versão anterior do script, execute esta versão atualizada
   também: ela habilita leitura pública somente para o papel `anon`.
3. Na seção **Connect**, copie a **Project URL** e a chave **publishable**
   (`sb_publishable_...`). Nunca use uma chave `secret`/`service_role` no
   dashboard publicado.

A chave publishable pode ser usada no navegador; a segurança da leitura é
definida pela policy de Row Level Security criada pelo SQL. Escritas anônimas
não são concedidas. O coletor usa uma conexão PostgreSQL guardada somente no
computador da prancha.

## 2. Publicar o dashboard no Streamlit

1. Envie o código do projeto para um repositório GitHub acessível pela sua conta
   do Streamlit. Não inclua `.env`, `secrets.toml`, senhas ou chaves secretas.
2. Entre em [share.streamlit.io](https://share.streamlit.io), escolha **Create
   app** e selecione o repositório, branch e arquivo principal
   `frontend/app.py`.
3. Nas **Advanced settings / Secrets**, cole (com os valores do seu Supabase):

   ```toml
   SUPABASE_URL = "https://SEU-PROJETO.supabase.co"
   SUPABASE_KEY = "SUA_CHAVE_sb_publishable"
   JADE_DATA_SOURCE = "supabase"
   ```

4. Clique em **Deploy**. O Streamlit instala as dependências de
   [`requirements.txt`](requirements.txt). Sem secrets, o painel abre em modo
   demonstração; com os três valores acima, busca os dados reais.

A senha PostgreSQL **não** vai para o Streamlit: a interface usa somente a URL
do projeto e a chave publishable. A busca pagina os resultados e a tela consulta
novamente o Supabase aproximadamente a cada 60 segundos. O botão **Atualizar
dados** força uma nova leitura.

## 3. Preparar o computador conectado à prancha (Windows)

O computador precisa permanecer ligado e com internet enquanto coleta. O
Streamlit Cloud não acessa diretamente a porta COM/USB do seu computador.

1. Instale Python 3.11 ou superior. Ao instalar pelo python.org, marque **Add
   Python to PATH**.
2. No Windows Explorer, copie `.env.example` e renomeie a cópia para `.env`.
3. Abra `.env` com o Bloco de Notas e preencha `JADE_DATABASE_URL` com a URI
   PostgreSQL do Supabase. Na tela **Connect**, use a URI PostgreSQL do
   **Session pooler** ou conexão adequada à sua rede. A senha fica neste arquivo
   local; `.env` é ignorado pelo Git e não deve ser compartilhado.
4. Se a senha contiver `#`, escreva `%23` no lugar dele dentro da URI. Codifique
   também outros caracteres reservados da URI.
5. Execute `setup_windows.bat` uma vez; ele cria `.venv` e instala dependências.
6. Conecte a prancha, encontre a porta em **Gerenciador de Dispositivos →
   Portas (COM e LPT)** e execute `run_backend.bat`. Digite a porta se o
   programa solicitar. Deixe a janela aberta durante a apresentação. `Ctrl+C`
   encerra a coleta.

O coletor grava diretamente no PostgreSQL do Supabase; não é necessário
publicar a API FastAPI. O padrão atual da serial é `115200`, `7E1`. Confirme
esses parâmetros e o catálogo de códigos/mensagens em
[`shared/catalog.py`](shared/catalog.py) com a equipe do hardware antes da
coleta real. O coletor rejeita quadros inválidos e atendimentos sem solicitação
pendente correspondente.

## 4. Testar sem placa ou Supabase

Para testar a interface local sem dados reais, abra o terminal na pasta do
projeto e execute:

```powershell
.\.venv\Scripts\Activate.ps1
$env:JADE_DATA_SOURCE = "demo"
streamlit run frontend\app.py
```

O endereço local será mostrado no terminal (normalmente
`http://localhost:8501`). Esse modo usa dados fictícios e não grava no banco.

## Configurações

- **Streamlit Secrets:** `SUPABASE_URL`, `SUPABASE_KEY` publishable e
  `JADE_DATA_SOURCE="supabase"`; configurar no painel do Streamlit, não no Git.
- **Arquivo local `.env`:** `JADE_DATABASE_URL` (URI PostgreSQL),
  `JADE_SERIAL_PORT` (opcional; se vazia, pergunta ao iniciar) e
  `JADE_SERIAL_BAUDRATE` (padrão `115200`).
- O modelo de secrets do Streamlit está em
  [`.streamlit/secrets.toml.example`](.streamlit/secrets.toml.example).
- O modelo local está em [`.env.example`](.env.example). O programa não carrega
  `.env` no dashboard; somente o coletor local lê esse arquivo.

## Estrutura principal

```text
backend/serial_worker.py   # Coletor local de dados da porta serial
backend/serial_listener.py # Protocolo e persistência de eventos
database/schema.sql        # Tabela, índices, RLS e policy Supabase
frontend/app.py            # Interface Streamlit hospedada
frontend/jade/data.py      # Demo, validação e cliente Supabase REST
shared/catalog.py          # Catálogo compartilhado da prancha
setup_windows.bat          # Instalação local de dependências
run_backend.bat            # Inicialização do coletor
```

## Testes

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest
```

Os testes que persistem eventos precisam de um PostgreSQL exclusivo configurado
em `JADE_TEST_DATABASE_URL`. Nunca aponte os testes para o banco com dados reais.

## Licença

MIT. Consulte [`LICENSE`](LICENSE).
