# Dashboard do projeto Jade

Frontend em **Python e Streamlit** para acompanhar o uso da prancha de Comunicação
Alternativa (CAA) do projeto Jade, desenvolvido no Laboratório Digital II.

A prancha física terá dez mensagens, distribuídas em três níveis de urgência.
O acompanhante registra o atendimento em um botão, encerrando a chamada.
O dashboard relaciona cada solicitação ao respectivo registro de atendimento.

## Executar localmente

Requer Python **3.11 ou superior**. Na raiz do repositório:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run frontend/app.py
```

No Windows, use `python -m venv .venv` e ative com
`.venv\Scripts\Activate.ps1` no PowerShell. Os demais comandos são iguais.

Abra **http://localhost:8501**. Execute o comando na raiz para que o Streamlit
carregue o tema de `.streamlit/config.toml`.

O modo padrão é **demonstração**: gera trinta dias de dados fictícios e funciona
sem backend. O aviso fica visível no painel. As mensagens e as urgências de
`frontend/jade/catalog.py` são **exemplos provisórios**, a confirmar com a equipe.

## Aplicativo executável para Windows

O executável inicia a API local e o dashboard, que abre no navegador padrão. A
persistência continua no PostgreSQL do Supabase. O computador precisa de acesso
à internet e de `JADE_DATABASE_URL` configurada no ambiente do Windows antes de
abrir o aplicativo.

O `.exe` **não contém** a senha do banco. Para testar no PowerShell, copie a URI
de conexão PostgreSQL do painel Supabase (preferencialmente o pooler em modo
Session) e configure a variável apenas na sessão atual:

```powershell
$env:JADE_DATABASE_URL = "postgresql+psycopg://postgres.<project-ref>:SUA_SENHA@HOST:PORT/postgres?sslmode=require"
```

Se a URI copiada começar com `postgres://` ou `postgresql://`, o backend a
converte automaticamente para o driver `psycopg`. Caracteres especiais na senha
precisam estar codificados para URL. Não publique nem envie essa URI: ela contém
credenciais de acesso ao banco. Para uso permanente, configure a variável de
ambiente do usuário pelo Windows e reinicie a sessão antes de abrir o app.
No PowerShell, a configuração permanente pode ser feita assim:

```powershell
[Environment]::SetEnvironmentVariable(
  "JADE_DATABASE_URL",
  "postgresql+psycopg://postgres.<project-ref>:SUA_SENHA@HOST:PORT/postgres?sslmode=require",
  "User"
)
```

Para gerar o pacote, em um **Windows com Python 3.11 instalado**, na raiz do
projeto, execute:

```powershell
.\build_windows.ps1
```

O executável será gerado em `dist\JadeDashboard\JadeDashboard.exe`. Distribua a
pasta `dist\JadeDashboard` inteira, não apenas o `.exe`. O build precisa ocorrer
no Windows; gerar em Linux não produz um executável Windows.

**Segurança:** não coloque a URI do banco no código, no `.spec` ou no pacote.
Quem tiver uma cópia da URI terá acesso ao banco conforme as permissões daquele
usuário. Para distribuir o aplicativo a várias pessoas, a arquitetura recomendada
é hospedar a API separadamente e manter a credencial do Supabase somente no
servidor; o aplicativo desktop deve chamar essa API autenticada, e não conectar
diretamente ao PostgreSQL.

## O que está implementado

- Filtro global por período de solicitação, como único controle na barra lateral.
- Total de solicitações, atendidas, sem atendimento e tempo médio de atendimento.
- Gráfico com uma linha por mensagem, somando solicitações por horário do dia,
  com dropdown de checkboxes e busca por mensagem (aceita termos sem acentos).
  Esse filtro afeta apenas o gráfico e preserva a seleção durante a busca.
- Quantidade de uso de cada mensagem em um gráfico de bolhas: posição e área
  representam a quantidade de solicitações; as cores indicam a urgência.
- Mini ranking com as dez mensagens e as quantidades de uso no período.
- Distribuição de solicitações entre os três níveis de urgência.
- Histórico com botão de exportação ao lado do título e modal para baixar CSV
  ou XLSX dos registros do período. A planilha mantém datas com fuso horário,
  cabeçalho fixo e filtros nas colunas.
- Estados de carregamento, ausência de dados, período incompleto e falha de API.
- Logo `jadeLogos/principal.png` exibida na proporção original e tema inspirado
  no seu fundo creme, com detalhes em azul, amarelo e coral. Gráficos com largura
  adaptável e colunas empilhadas em telas menores. A barra lateral é recolhível no celular.

### Regras dos indicadores

- Os filtros usam a **data da solicitação**, incluindo o início e o fim do período,
  no fuso `America/Sao_Paulo`.
- Solicitação atendida tem `attended_at` preenchido; uma pendente tem valor `null`.
- O tempo médio é a média de `attended_at - requested_at` **apenas dos atendimentos
  concluídos**. Sem atendimentos, o painel mostra `—`; atendimento imediato vale zero.
- Se uma solicitação foi feita dentro do período e atendida depois dele, o atendimento
  e seu tempo continuam incluídos. O painel acompanha o conjunto de solicitações
  feitas no período, e não apenas os atendimentos ocorridos nele.
- “Sem atendimento” conta os registros pendentes **dentro do filtro atual**.
- O gráfico por horário soma todos os dias do período, sem calcular média diária,
  e inclui as 24 horas e as mensagens selecionadas sem uso.
- Indicadores, bolhas, urgências, ranking e histórico consideram todas as mensagens
  no período, independentemente da seleção no gráfico por horário. O ranking inclui
  mensagens sem uso com quantidade zero; empates seguem a ordem do catálogo.
- Os dados são mantidos em cache por até 60 segundos. **Atualizar dados**, no painel principal, invalida
  o cache e faz uma nova leitura; não há atualização automática em segundo plano.

## Estrutura do repositório

```text
.
├── .streamlit/config.toml   # Tema do Streamlit
├── .env.example            # Exemplo das variáveis de configuração
├── frontend/
│   ├── app.py              # Entrada da aplicação e composição da interface
│   ├── styles.css          # Ajustes visuais e responsividade
│   └── jade/
│       ├── catalog.py      # Dez mensagens, urgências e cores
│       ├── data.py         # Simulador, validação e adaptador HTTP
│       ├── metrics.py      # Filtros, cálculos e preparação do CSV
│       └── charts.py       # Gráficos Plotly
├── backend/
│   ├── main.py             # API FastAPI: GET /events e /health
│   ├── database.py         # Inicialização do PostgreSQL
│   ├── events.py           # Persistência e regras de seleção/atendimento
│   ├── serial_listener.py  # Leitura contínua da porta serial
│   └── serial_protocol.py  # Parser dos quadros recebidos pela serial
├── app_launcher.py         # Inicializador da versão empacotada para Windows
├── JadeDashboard.spec      # Configuração do PyInstaller
├── build_windows.ps1       # Script de build no Windows
├── jadeLogos/              # Logo principal e identidade visual fornecidas
├── tests/                  # Testes de métricas, protocolo, contrato e interface
├── requirements.txt
├── requirements-dev.txt
└── pyproject.toml          # Configuração dos testes
```

## Backend e integração serial

O backend usa **FastAPI**, **PostgreSQL** (incluindo Supabase) e um leitor serial
opcional. Para iniciá-lo, instale as dependências e configure `JADE_DATABASE_URL`
com a URI PostgreSQL do seu banco:

```text
JADE_DATABASE_URL=postgresql+psycopg://usuario:senha@localhost:5432/jade
```

O banco PostgreSQL deve estar criado e acessível. Na primeira inicialização, o
backend cria a tabela de eventos. Inicie o serviço a partir da raiz:

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

O endpoint `GET /events` retorna todos os eventos no contrato consumido pelo
dashboard; `GET /health` verifica se a API está respondendo.

### Protocolo serial

O leitor serial é desabilitado por padrão. Para habilitá-lo, configure a porta e
o baud rate exatos do dispositivo, além de `JADE_SERIAL_ENABLED=true`:

```bash
export JADE_DATABASE_URL=postgresql+psycopg://usuario:senha@localhost:5432/jade
export JADE_SERIAL_ENABLED=true
export JADE_SERIAL_PORT=/dev/ttyUSB0
# Configure JADE_SERIAL_BAUDRATE com o valor definido pelo fabricante.
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

No Windows, configure as mesmas variáveis com `$env:JADE_DATABASE_URL`,
`$env:JADE_SERIAL_ENABLED`, `$env:JADE_SERIAL_PORT` (por exemplo, `COM3`) e
`$env:JADE_SERIAL_BAUDRATE`. Sem o hardware conectado, mantenha a serial
desabilitada e ainda é possível executar a API e testar `/events`.

Os quadros seguem `tipo,código,urgência` e terminam em CRLF, por exemplo
`S,01,1\r\n`. `S` registra uma solicitação e `A` registra um atendimento.
Os códigos `01` a `10` correspondem à ordem atual de `frontend/jade/catalog.py`;
urgências `1`, `2` e `3` correspondem a Baixa, Média e Alta. Uma divergência
entre a urgência serial e a do catálogo é rejeitada e registrada no log.

Como o quadro `A` não leva um identificador de solicitação, o backend encerra a
solicitação pendente mais antiga (`FIFO`) daquela mensagem. Um atendimento sem
solicitação pendente também é rejeitado e registrado. As datas são registradas
em UTC; o dashboard as converte para `America/Sao_Paulo`.

O endpoint e o catálogo ainda precisam ser conferidos com a equipe antes do uso
com a prancha real. A tabela é criada automaticamente nesta versão inicial; não
há ainda gestão de migrações, autenticação, identificação de múltiplas pranchas
ou atualização em tempo real.

Para selecionar a API, configure as variáveis no terminal antes de iniciar:

```bash
export JADE_DATA_SOURCE=api
export JADE_API_URL=http://localhost:8000
streamlit run frontend/app.py
```

No PowerShell, use `$env:JADE_DATA_SOURCE="api"` e
`$env:JADE_API_URL="http://localhost:8000"`.
O arquivo `.env.example` documenta as opções; arquivos `.env` **não são
carregados automaticamente**. Use `JADE_DATA_SOURCE=demo` para voltar à demonstração.

### Contrato da API: `GET /events`

Resposta HTTP 200 com uma lista JSON:

```json
[
  {
    "id": "solicitacao-001",
    "message_id": "agua",
    "requested_at": "2026-10-27T10:00:00-03:00",
    "attended_at": "2026-10-27T10:02:15-03:00"
  },
  {
    "id": "solicitacao-002",
    "message_id": "ajuda",
    "requested_at": "2026-10-27T10:05:00-03:00",
    "attended_at": null
  }
]
```

| Campo | Regra |
| --- | --- |
| `id` | Texto não vazio e único por solicitação. |
| `message_id` | Identificador presente em `frontend/jade/catalog.py`. |
| `requested_at` | Data ISO 8601 com fuso explícito (`Z` ou offset). |
| `attended_at` | Data ISO 8601 com fuso, ou `null` para pendente. Campo obrigatório. |

Uma lista vazia é válida. IDs duplicados, mensagens desconhecidas, datas inválidas
ou sem fuso e atendimentos anteriores à solicitação são rejeitados com erro visível.
Falhas da API **não acionam o modo demonstração**. Textos e urgências vêm do catálogo
local; altere-o em conjunto com o backend.

Nesta primeira versão, a API devolve a lista completa, sem paginação, e os
filtros são aplicados no frontend. O atendimento FIFO por mensagem é necessário
porque o quadro serial não inclui o ID da solicitação.

## Validação

Com o ambiente virtual ativo:

```bash
python -m pip install -r requirements-dev.txt
export JADE_TEST_DATABASE_URL=postgresql+psycopg://usuario:senha@localhost:5432/jade_test
python -m pytest
```

`requirements.txt` lista as dependências necessárias para executar o frontend e
o backend. `requirements-dev.txt` inclui essas dependências e acrescenta as
ferramentas de teste; por isso, no desenvolvimento, instale apenas o segundo.
`JADE_TEST_DATABASE_URL` deve apontar para um banco PostgreSQL dedicado a testes.
Cada teste cria um schema isolado nesse banco e o remove ao terminar; não use a URL
do banco com dados reais.

Os testes verificam as regras das métricas, limites de datas e fuso horário,
validação dos eventos, falhas HTTP, exportação XLSX, gráfico de bolhas, ranking,
seleção e busca de mensagens, processamento serial, persistência PostgreSQL e
contrato HTTP do backend, além da execução da interface com `AppTest` do Streamlit.
Para conferir a apresentação, abra o dashboard em um navegador de computador e
em uma tela de celular.

Referências: [gráficos no Streamlit](https://docs.streamlit.io/develop/api-reference/charts/st.plotly_chart)
e [configuração de temas](https://docs.streamlit.io/develop/concepts/configuration/theming).

## Próximos passos

1. Confirmar os códigos, mensagens e urgências com a equipe da prancha.
2. Validar o baud rate e o formato de saída no hardware real.
3. Definir migrações, autenticação e identificação caso haja mais de uma prancha.

## Licença

MIT. Consulte [LICENSE](LICENSE).
