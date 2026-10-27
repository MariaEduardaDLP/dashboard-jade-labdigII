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

## O que está implementado

- Filtros por período, níveis de urgência e mensagens.
- Total de solicitações, atendidas, sem atendimento e tempo médio de atendimento.
- Gráfico com uma linha por mensagem, somando solicitações por horário do dia.
- Quantidade de uso de cada mensagem em barras horizontais, para facilitar a leitura.
- Distribuição de solicitações entre os três níveis de urgência.
- Histórico e exportação CSV dos registros filtrados.
- Estados de carregamento, ausência de dados, período incompleto e falha de API.
- Tema baseado nas logos existentes, gráficos com largura adaptável e colunas
  empilhadas em telas menores. Os filtros ficam na barra lateral, recolhível no celular.

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
- Os dados são mantidos em cache por até 60 segundos. **Atualizar dados** invalida
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
├── jadeLogos/              # Identidade visual fornecida pelo projeto
├── tests/                  # Testes de métricas, contrato e interface
├── requirements.txt
├── requirements-dev.txt
└── pyproject.toml          # Configuração dos testes
```

## Integração com o backend

O frontend está separado do backend, previsto em **FastAPI**. Este repositório
não implementa o serviço nem a comunicação com o hardware.

O adaptador usa o **contrato inicial proposto** abaixo; o endpoint e o catálogo
devem ser confirmados com a equipe do backend antes de usar dados reais.

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

### Contrato proposto: `GET /events`

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

Nesta primeira versão, a API deve devolver a lista completa, sem paginação, e os
filtros são aplicados no frontend. O backend deve associar o botão de atendimento
à solicitação correta, mesmo quando houver várias chamadas pendentes. Paginação,
autenticação, identificação de pranchas e atualização em tempo real ficam para
quando os contratos dessas funcionalidades forem definidos.

## Validação

Com o ambiente virtual ativo:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest
```

Os testes verificam as regras das métricas, limites de datas e fuso horário,
validação dos eventos, falhas HTTP e execução da interface com `AppTest` do Streamlit.
Para conferir a apresentação, abra o dashboard em um navegador de computador e
em uma tela de celular.

Referências: [gráficos no Streamlit](https://docs.streamlit.io/develop/api-reference/charts/st.plotly_chart)
e [configuração de temas](https://docs.streamlit.io/develop/concepts/configuration/theming).

## Próximos passos

1. Confirmar as dez mensagens e sua classificação de urgência com a equipe da prancha.
2. Acordar o contrato de eventos e a associação entre solicitação e atendimento.
3. Conectar a API real e definir a identificação da prancha e os filtros necessários.

## Licença

MIT. Consulte [LICENSE](LICENSE).
