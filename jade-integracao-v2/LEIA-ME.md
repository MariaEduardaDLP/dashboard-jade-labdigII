# Jade UART — aplicador v2

Este pacote adapta o backend à UART do QAR (115200, 7E1) sem depender da versão exata do arquivo de origem.

## Instalar

1. Extraia `jade-integracao-v2/` **na raiz do repositório** (junto de `backend/`).
2. Execute `python jade-integracao-v2/aplicar.py` para **ver alterações sem modificar nada**.
3. Se o resumo estiver correto: `python jade-integracao-v2/aplicar.py --apply`.
4. Execute `git diff --check` e `python -m pytest tests/test_serial_protocol.py tests/test_uart_jade.py -q`.
5. Faça o commit na branch de integração quando os testes passarem.

O aplicador examina os métodos e campos de Python para identificar os pontos de alteração. Se não reconhecer a estrutura atual, recusa modificar qualquer arquivo e informa o problema. Não use `git apply --force` nem `git reset --hard` para tentar fazer o patch antigo funcionar.

## Escopo

- Define 7 bits, paridade par e 1 stop bit na abertura da serial (`serial_listener.py`), mantendo o baud rate já configurável.
- Ajusta `requested_at` e `attended_at` para PostgreSQL com timezone no modelo (`events.py`), normalizando dados UTC antigos durante comparação.
- Acrescenta monitor de UART e teste da configuração serial.
- Atualiza o exemplo de baud rate na `.env.example` quando encontra o comentário previsto.

O aplicador **não modifica o banco de dados**. Se `events` já existir, será necessária migração específica dos campos timestamp após confirmar o fuso dos valores armazenados. O QAR também exige adaptador USB–UART de nível lógico 3,3 V e compartilhamento de GND.
