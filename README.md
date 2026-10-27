# Dashboard do projeto Jade

Implementação do dashboard com as métricas de uso da Prancha de Comunicação Alternativa (CAA)

## Ferramentas a serem usadas na implementação

- Frontend: Python - Streamlit 
- Backend: Python (FAST-API)
- Frontend: Streamlit
- Backend: a decidir

## Contexto do projeto Jade (Prancha de Comunicação Alternativa)

O projeto Jade trata-se de um prancha física que conterá 10 mensagens diferentes que o usuário poderá escolher. Cada mensagem será agrupada em 1 dos três níveis de urgência, conforme a gravidade da mensagem escolhida pelo usuário. Além das mensagens, o projeto também conta com um botão que sinaliza que o usuário foi atendido por alguém (um acompanhante do usuário viu a necessidade solicitada na prancha e foi atender o usuário, cancelando a chamada pelo botão).

## Dados que deverão ser visualizados no Dashboard

### Mensagens por horário do dia

Um gráfico em que cada linha represente a quantidade de vezes com que uma mensagem foi enviada ao longo do dia. No geral, o gráfico terá 10 linhas, sendo que cada representará uma mensagem individual (finalidade de obter o tráfego de mensagens)

### Quantidade de uso das mensagens

Um gráfico que mostre o uso das mensagens, pode ser um bubble chart

### Tempo médio de atendimento

Um campo que mostre o tempo médio que leva entre uma solicitação e um atendimento (a seleção de uma mensagem e seu cancelamento no botão do acompanhante)

### Outros gráficos

Caso sejam observados novas oportunidade de obtenção de demais métricas (ou outras relações entre dados relevantes), novos gráficos deverão ser adicionados

## Responsividade

Espera-se que o dashboard seja visualizável tanto no computador quanto no celular. Dito isso, deve-se ter cuidado com o uso dos componentes do Streamlit para que a interface fique visualmente agradável. Além disso, a estética deverá ser compatível com a temática do projeto (evitando sobrecargas visuais): uso das logos disponíveis e cores compatíveis.
