# Gerador de QR Code Dinâmico

Aplicação web em Python (Flask) para gerar QR Codes personalizados: um único
código que pode redirecionar o visitante para uma URL diferente conforme o
dispositivo (Android → Google Play, iOS → App Store), com personalização
visual completa (degradê de cores, borda colorida, logo central e texto de
chamada) e exportação em PNG, JPG e PDF.

## Recursos

- Login/cadastro de usuário com senha em hash (nunca em texto puro), proteção
  CSRF, proteção contra SQL Injection (ORM com consultas parametrizadas),
  bloqueio temporário de conta após tentativas de login malsucedidas e limite
  de requisições (rate limiting) contra força bruta.
- Dois papéis de usuário: **master** (controle total: pode editar/excluir o
  QR Code de qualquer pessoa, gerenciar o papel de outros usuários e é o
  único que vê os recursos de publicação no Netlify) e **padrão** (só pode
  editar/excluir os próprios QR Codes). O primeiro usuário que se cadastra no
  sistema vira master automaticamente. Veja a seção **Papéis de usuário
  (master x padrão)** abaixo.
- Painel compartilhado: todo usuário logado vê os QR Codes criados por
  qualquer pessoa (não só os seus).
- Cada QR Code guarda a URL da Google Play (Android) e da App Store (iOS), e
  opcionalmente uma "URL de destino do QR Code" (ex: uma página publicada no
  Netlify). Veja a seção **Rodando só localmente x publicando no Netlify**
  abaixo para entender quando usar cada uma.
- Personalização visual completa: degradê de 2 cores (horizontal, vertical,
  radial ou quadrado), borda colorida ao redor do QR Code, logo central
  (imagem quadrada, redimensionada automaticamente para 300x300) e um texto
  de chamada impresso acima do QR Code (ex: "Aponte a câmera").
- Painel mostra a miniatura de cada QR Code (não apenas texto/cor).
- Exportação do QR Code em PNG, JPG e PDF, geradas sob demanda a partir das
  cores, borda, logo, texto e URLs atuais (então refletem sempre a última
  edição).
- Layout responsivo, funciona em celular e computador.

## Estrutura do projeto

```
qrcode_dinamico/
  app.py              # rotas da aplicação
  config.py           # configurações (lidas do .env)
  extensions.py       # instâncias do banco, login, csrf, rate limit
  models.py           # tabela: User, QRCode
  forms.py            # formulários e validação de entrada
  qr_utils.py         # geração da imagem do QR Code (degradê, logo, borda, texto)
  security_utils.py   # detecção de dispositivo e controle de tentativas de login
  templates/          # páginas HTML (Jinja2)
  static/css, static/js, static/logos (logos enviados)
  requirements.txt          # dependências principais (SQLite já incluso)
  requirements-postgres.txt # driver do PostgreSQL, instale só se for usar Postgres
  iniciar_servidor.bat # (Windows) atalho para ligar o servidor com 1 clique
  descobrir_ip.bat     # (Windows) mostra o IP desta máquina na rede local
  .env.example
```

## Rodando só localmente x publicando no Netlify (leia antes de usar)

Este app (Flask) é o painel onde você cadastra o QR Code e personaliza a
aparência (degradê, borda, logo, texto). Ele pode rodar **só no seu
computador**, sem precisar publicar em lugar nenhum. Só que, sendo local, ele
só está acessível enquanto o processo `python app.py` estiver ligado e na
mesma rede de quem escaneia — por isso existem dois jeitos de configurar cada
QR Code:

- **Campo "URL de destino do QR Code" vazio:** a imagem do QR aponta para o
  link interno deste app (`/r/<codigo>`). Bom para testar na mesma rede
  Wi-Fi, mas some se o app for desligado ou se o celular estiver em outra
  rede.
- **Campo "URL de destino do QR Code" preenchido** com a URL de uma página
  publicada no Netlify (ou qualquer outro host estático): a imagem do QR
  aponta direto para essa URL pública, que funciona sempre, mesmo com este
  app desligado. Na tela de detalhes do QR Code, o botão **"Baixar página p/
  Netlify (index.html)"** gera um arquivo HTML pronto — com as URLs de
  Android e iOS já preenchidas e a lógica de redirecionamento por
  dispositivo em JavaScript puro — para você publicar direto no Netlify.
  **Esse botão só aparece para o usuário master** (veja a seção **Papéis de
  usuário** abaixo).

## Papéis de usuário (master x padrão)

- **O primeiro usuário que se cadastrar no sistema vira master automaticamente.**
  Não existe tela para "escolher" isso — é sempre o primeiro cadastro.
- **Master:** pode editar e excluir o QR Code de qualquer usuário, tem uma
  página extra em "Usuários" (menu superior) para promover/rebaixar o papel
  de qualquer conta, e é o único que vê o botão **"Baixar página p/ Netlify"**
  na tela de detalhes do QR Code.
- **Padrão:** vê no painel os QR Codes de todo mundo, mas só pode editar ou
  excluir os que ele mesmo criou. Não vê o botão/textos relacionados ao
  Netlify.
- Se o sistema já estava em uso antes desta versão (banco de dados antigo,
  sem a coluna de papel), não é preciso apagar nada: ao iniciar, o app
  adiciona a coluna que falta sozinho e promove automaticamente o usuário
  mais antigo a master.
- Para promover manualmente outro usuário a master mais tarde, entre com uma
  conta master e acesse **Usuários** no menu superior.

## Rodando na rede local (acessar de outros computadores/celulares)

O servidor já fica disponível para qualquer dispositivo da mesma rede
Wi-Fi/cabeada, não só o computador onde ele está rodando (`app.run(host="0.0.0.0", ...)`
em `app.py`). Faltam só dois ajustes:

1. **Descubra o IP desta máquina na rede.** Dê duplo clique em
   `descobrir_ip.bat` (ou rode `ipconfig` no terminal) e procure a linha
   "IPv4 Address" — algo como `192.168.0.10`.
2. **Configure o `BASE_URL` no `.env`** para usar esse IP em vez de
   `localhost`:

   ```
   BASE_URL=http://192.168.0.10:5000
   ```

   Isso é importante para os QR Codes que usam o link interno
   (`/r/<codigo>`, quando o campo "URL de destino do QR Code" está vazio) —
   sem isso, o link gerado só funciona no próprio computador que roda o
   servidor.
3. **Libere a porta 5000 no Firewall do Windows**, se outros dispositivos não
   conseguirem acessar: Painel de Controle → Sistema e Segurança → Firewall
   do Windows Defender → Configurações Avançadas → Regras de Entrada → Nova
   Regra → Porta → TCP → `5000` → Permitir a conexão.
4. Nos outros dispositivos da mesma rede, acesse `http://192.168.0.10:5000`
   (troque pelo IP encontrado no passo 1).

> Isso só funciona enquanto o computador que roda o servidor estiver ligado
> e os outros dispositivos estiverem na mesma rede. Para acesso de qualquer
> lugar (internet), veja a seção **Publicando** mais abaixo.

## Atalho na área de trabalho (Windows)

Para não precisar abrir o terminal toda vez:

1. Dê duplo clique em `iniciar_servidor.bat` (dentro da pasta do projeto)
   para ligar o servidor — ele detecta sozinho o ambiente virtual (`.venv`
   ou `venv`) e mostra o endereço para acessar.
2. Para criar um atalho na área de trabalho: clique com o botão direito em
   `iniciar_servidor.bat` → **Enviar para** → **Área de trabalho (criar
   atalho)**.
3. (Opcional) Para trocar o ícone do atalho: clique com o botão direito no
   atalho → Propriedades → **Alterar Ícone**.
4. Para parar o servidor, feche a janela preta que abriu (ou pressione
   `CTRL+C` dentro dela).

## Como rodar localmente (passo a passo para iniciantes)

1. Instale o Python 3.11+ (se ainda não tiver).
2. Abra um terminal dentro da pasta `qrcode_dinamico` e crie um ambiente
   virtual:

   ```bash
   python -m venv venv
   source venv/bin/activate        # Windows: venv\Scripts\activate
   ```

3. Instale as dependências:

   ```bash
   pip install -r requirements.txt
   ```

   > **Windows / erro do `psycopg2-binary`:** o `requirements.txt` **não**
   > inclui o driver do PostgreSQL, justamente para este passo funcionar sem
   > precisar instalar nada além do Python (o app já usa SQLite por padrão).
   > Só instale `requirements-postgres.txt` (veja a seção "Usando
   > PostgreSQL" abaixo) quando for mesmo publicar com PostgreSQL.

4. Copie o arquivo de configuração de exemplo:

   ```bash
   cp .env.example .env
   ```

   Por padrão ele já usa um banco SQLite local (arquivo `instance/app.db`),
   então você **não precisa instalar PostgreSQL** só para testar.

5. Rode a aplicação:

   ```bash
   python app.py
   ```

6. Acesse `http://localhost:5000` no navegador, crie uma conta e gere seu
   primeiro QR Code.

Para testar o redirecionamento de verdade, abra a câmera do seu celular
apontando para o QR Code gerado — o celular precisa conseguir acessar o
endereço configurado em `BASE_URL` do `.env` (em produção, será o domínio
público da sua hospedagem).

## Usando PostgreSQL (recomendado em produção)

1. Instale o driver do PostgreSQL (separado do `requirements.txt` principal
   para não travar quem só quer testar com SQLite):

   ```bash
   pip install -r requirements-postgres.txt
   ```

   Se aparecer o erro `pg_config executable not found` ou `Microsoft Visual
   C++ 14.0 is required`, é porque o pip tentou compilar o `psycopg2` do
   zero. Normalmente isso não deveria acontecer, pois o PyPI tem pacotes
   prontos ("wheels") para Windows/Mac/Linux — geralmente esse erro some
   apenas atualizando o pip antes (`python -m pip install --upgrade pip`) e
   instalando de novo. Como alternativa mais simples, instale o pacote
   `psycopg2-binary` (sem compilar nada):

   ```bash
   pip install psycopg2-binary
   ```

2. Crie um banco, por exemplo `qrcode_dinamico`.
3. No `.env`, defina:

   ```
   DATABASE_URL=postgresql://usuario:senha@host:5432/qrcode_dinamico
   ```

4. Rode a aplicação normalmente — as tabelas são criadas automaticamente na
   primeira execução (`db.create_all()`).

## Publicando (hospedagem fácil e gratuita)

Qualquer serviço que rode aplicações Python/Flask com Gunicorn funciona. Duas
opções simples e com planos gratuitos:

### Opção A — Render.com
1. Suba este projeto para um repositório no GitHub.
2. Em Render, crie um **Web Service** apontando para o repositório.
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn app:app`
5. Adicione um banco PostgreSQL gratuito em Render e copie a
   `Internal Database URL` para a variável de ambiente `DATABASE_URL`.
6. Defina `SECRET_KEY`, `BASE_URL` (a URL pública que o Render atribuir) e
   `FORCE_HTTPS=1` nas variáveis de ambiente do serviço.

### Opção B — Railway.app
1. Mesma ideia: conecte o repositório, adicione um plugin PostgreSQL,
   configure as variáveis de ambiente (`SECRET_KEY`, `DATABASE_URL`,
   `BASE_URL`, `FORCE_HTTPS=1`) e defina o start command `gunicorn app:app`.

### Opção C — VPS próprio (Linux + Nginx + Gunicorn)
```bash
pip install -r requirements.txt
gunicorn --bind 0.0.0.0:8000 app:app
```
Configure o Nginx como proxy reverso para a porta 8000 e habilite HTTPS (ex:
com Certbot/Let's Encrypt). Depois defina `FORCE_HTTPS=1` no `.env`.

## Notas de segurança

- Gere uma `SECRET_KEY` própria antes de publicar (nunca use a de exemplo):
  `python -c "import secrets; print(secrets.token_hex(32))"`.
- Em produção, sempre rode atrás de HTTPS e com `FORCE_HTTPS=1`.
- O rate limiting usa armazenamento em memória por padrão
  (`memory://`), o que funciona para um único processo. Em produção com
  múltiplos workers, aponte `RATELIMIT_STORAGE_URI` para um Redis.
- O limite de upload geral (`MAX_CONTENT_LENGTH`, em `config.py`) evita que
  alguém tente subir arquivos gigantes no campo de logo.

## Limitações conhecidas / próximos passos possíveis

- Não há recuperação de senha por e-mail (poderia ser adicionada com
  Flask-Mail).
- Não há contador de leituras nem captura de localização — foram removidos
  a pedido, para manter o app simples e focado em gerar/gerenciar os QR
  Codes.
