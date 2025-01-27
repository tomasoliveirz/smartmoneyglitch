# README (Configuração e Execução)

Este README descreve os passos essenciais para configurar e executar o script de monitorização de CA (sem incluir o código-fonte completo).

---

## 1. Pré-Requisitos

1. **Conta Telegram** válida.  
2. **Python 3.7+** instalado.
3. **Biblioteca [Telethon](https://pypi.org/project/Telethon/)** (instalada posteriormente no ambiente virtual).
4. **Acesso à API do Telegram**:
   - Aceder a: [my.telegram.org](https://my.telegram.org/)
   - Clicar em **API Development Tools** e criar uma nova aplicação.
   - Copiar o **App api_id** e o **App api_hash**. Utilize os **seus valores** (não utilize valores de exemplo).

---

## 2. Criar e Activar um Ambiente Virtual (venv)

Para evitar conflitos de versões e garantir uma instalação limpa, recomendamos a criação de um **ambiente virtual** em Python (venv). Siga estes passos no directório do projecto:

```bash
# Cria o ambiente virtual:
python -m venv venv

# Activa o ambiente virtual (Windows):
.\venv\Scripts\activate

# Activa o ambiente virtual (Linux/Mac):
source venv/bin/activate
```

Uma vez activado, qualquer pacote instalado ficará contido neste ambiente, evitando problemas com outras instalações Python do seu sistema.

---

## 3. Instalação de Dependências

Com o ambiente virtual **activado**, instale as dependências necessárias (por exemplo, **Telethon**). Caso tenha um ficheiro `requirements.txt`, use o comando:

```bash
pip install -r requirements.txt
```

Se não tiver um `requirements.txt`, instale manualmente:
```bash
pip install telethon
```

---

## 4. Configuração do Script

Dentro do script principal (o ficheiro `.py` que contém o código de monitorização), localize as seguintes variáveis e **substitua** pelos **seus** valores:

```python
api_id = O_SEU_API_ID             # Ex: 1234567 (não use valores de exemplo)
api_hash = 'O_SEU_API_HASH'       # Ex: 'abcdef1234567890'
phone_number = '+351 O_SEU_NUMERO'
group_id = 4639774418             # ID do grupo onde quer monitorizar
bot_username = 'CashCash_trade_bot'
```

> **Nota**: O `group_id` já está definido no exemplo, mas certifique-se de que corresponde ao grupo onde deseja ler as mensagens.  
> **Importante**: Terá de **entrar no grupo** que deseja monitorizar para que o script consiga aceder às mensagens.  
> Exemplo de convite: [https://t.me/+uUfkO6V2L-NkNjQ0](https://t.me/+uUfkO6V2L-NkNjQ0)

---

## 5. Configurar o `CashCash_trade_bot`

1. Procure no Telegram pelo utilizador: **@CashCash_trade_bot**.
2. Ajuste as preferências de venda no próprio bot (ex.: vender 50% quando valor sobe X%, vender 100% quando valor sobe Y%, etc.).
3. O script **não** faz a venda directamente, apenas inicia a compra ao detectar CA (identificado como `ca_xxx`) e clica em botões de “Buy 0.25 SOL”. A estratégia de venda fica ao seu critério no próprio bot.

---

## 6. Executar o Script

1. **Activar** o ambiente virtual (caso ainda não esteja activo).
2. **Executar** o script com Python:
   ```bash
   python bot.py
   ```
3. Ao correr pela primeira vez, o Telethon pode **pedir o código de confirmação** enviado pelo Telegram para o número que forneceu (`phone_number`). Introduza esse código no terminal quando for solicitado.

---

## 7. Como Funciona (Resumo)

1. O script **lê as mensagens** de um grupo específico (através de `group_id`).
2. **Extrai** os preços (ex.: `$0.0005`, `$0.0017`, etc.) e identifica o **menor preço** (`min_avg_price`).
3. Se estiver no intervalo definido (por exemplo, `0.00035` até `0.15`), **envia** um comando `/start ca_...` para o bot `CashCash_trade_bot`.
4. Quando o bot responder, o script **tenta clicar** no botão `'Buy 0.25 SOL'`.
5. Regista o CA comprado num ficheiro (`purchased_cas.txt`) para não comprar novamente o mesmo CA.

---

## 8. Observações Importantes

- **Conexão**: O script deve permanecer em execução para **monitorizar em tempo real**.
- **Registo de CA**: O ficheiro `purchased_cas.txt` guarda os CAs já adquiridos, evitando compras duplicadas.
- **Segurança**: Os valores `api_id`, `api_hash` e o número de telefone devem ser **mantidos em segurança**.
- **Erros**: Se ocorrerem problemas de versão ou bibliotecas em falta, garanta que o ambiente virtual está correctamente activado e que instalou todas as dependências.

---

## 9. Suporte

- Dúvidas sobre Python, consulte o [site oficial](https://www.python.org/).
- Sobre o Telethon, veja a [documentação oficial](https://docs.telethon.dev/).
- Caso surjam erros, verifique o log no terminal para identificar problemas de autenticação, bibliotecas em falta ou conexão ao Telegram.

---

**Agora tem uma visão geral de como configurar e executar o script. Bom uso e boas negociações!**
