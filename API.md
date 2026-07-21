# Gerador de QR Code Dinâmico — Documentação das rotas

> Para instalação e deploy, veja o `README.md`. Este arquivo documenta as
> rotas HTTP da aplicação: parâmetros, retorno e erros.

## O que é

Aplicação web (Flask) que gera QR Codes personalizáveis com destinos diferentes
para Android/iOS e redireciona quem escaneia conforme o dispositivo.

## Como rodar (mínimo pra testar)

```bash
pip install -r requirements.txt
cp .env.example .env
python app.py
```

Abre em `http://localhost:5000`. Todas as rotas abaixo assumem esse endereço.

## Autenticação

A aplicação usa sessão via cookie (Flask-Login), não token/API key. Para
chamar qualquer rota autenticada fora do navegador (ex: `curl`), é preciso:

1. Fazer login e guardar o cookie de sessão.
2. Enviar o campo `csrf_token` em todo `POST` — ele vem escondido no HTML de
   cada formulário (`<input name="csrf_token" ... value="...">`) e muda a
   cada carregamento de página.

Rotas sem `@login_required` são públicas: `/registrar`, `/login`, `/r/<slug>`.
Todas as outras exigem sessão autenticada e retornam **302** (redirecionamento
para `/login`) se não houver login.

### Papéis: master x padrão

Todo usuário tem um campo `role`: `"master"` ou `"padrao"`. O primeiro
usuário cadastrado no sistema vira `master` automaticamente; os demais
nascem `padrao`. Isso afeta as rotas assim:

| Ação | padrão | master |
|---|---|---|
| Ver `/dashboard` e `/qr/<slug>` de qualquer usuário | sim | sim |
| Editar/excluir **o próprio** QR Code | sim | sim |
| Editar/excluir QR Code **de outro usuário** | não (`403`) | sim |
| `GET /qr/<slug>/pagina-netlify` | não (`403`) | sim |
| `GET /usuarios`, `POST /usuarios/<id>/papel` | não (`403`) | sim |

---

## `POST /registrar`

Cria uma conta. Limite: **10 requisições por hora por IP**.

**Parâmetros (form, `application/x-www-form-urlencoded`):**

| Campo | Tipo | Obrigatório | Validação |
|---|---|---|---|
| `csrf_token` | string | sim | token da página `/registrar` |
| `username` | string | sim | 3–30 caracteres, apenas letras/números/`.`/`-`/`_` |
| `password` | string | sim | mínimo 8 caracteres, com pelo menos 1 letra e 1 número |
| `confirm_password` | string | sim | precisa ser igual a `password` |

**Retorno:**
- Sucesso: `302` → redireciona para `/login`.
- Falha de validação ou usuário já existente: `200` (reexibe o
  formulário com a mensagem de erro no HTML, não usa JSON).

**Erros possíveis:**
- `429 Too Many Requests` — mais de 10 tentativas na mesma hora, do mesmo IP.

---

## `POST /login`

Autentica e cria a sessão. Limite: **15 requisições por 5 minutos por IP**.

**Parâmetros:**

| Campo | Tipo | Obrigatório |
|---|---|---|
| `csrf_token` | string | sim |
| `username` | string | sim |
| `password` | string | sim |
| `remember` | checkbox (`on`) | não — mantém a sessão após fechar o navegador |

**Retorno:**
- Sucesso: `302` → `/dashboard`, mais cookie de sessão.
- Credenciais erradas ou conta bloqueada: `200` (formulário reexibido com erro).

**Erros possíveis:**
- `429` — excedeu o limite de tentativas por IP.
- Conta bloqueada por 15 minutos após **5 senhas erradas seguidas** para o
  mesmo usuário (independe do IP).

---

## `GET /logout`

Encerra a sessão. Requer login. Retorna `302` → `/login`.

---

## `GET /dashboard`

Lista **todos** os QR Codes do sistema (de qualquer usuário) — painel
compartilhado. Sem parâmetros. Retorna `200` com a página HTML. Os botões de
editar/excluir só aparecem, por QR Code, para o dono dele ou para o master.
Sem QR Codes cadastrados, mostra estado vazio (não é erro).

---

## `POST /qr/novo`

Cria um QR Code. Requer login.

**Parâmetros (form, `multipart/form-data` — obrigatório por causa do campo `logo`):**

| Campo | Tipo | Obrigatório | Validação |
|---|---|---|---|
| `csrf_token` | string | sim | |
| `name` | string | sim | até 120 caracteres |
| `android_url` | string (URL) | não* | precisa ser URL válida, até 500 caracteres |
| `ios_url` | string (URL) | não* | idem |
| `desktop_url` | string (URL) | não* | idem — é a URL gravada dentro do QR Code quando preenchida (ex: página no Netlify) |
| `color_start` | string | sim | cor hex, ex: `#4F46E5` (padrão) |
| `color_end` | string | sim | cor hex, ex: `#06B6D4` (padrão) |
| `gradient_direction` | string | sim | um de: `horizontal`, `vertical`, `radial`, `square` (padrão `horizontal`) |
| `border_color` | string | sim | cor hex, padrão `#FFFFFF` |
| `caption_text` | string | não | até 160 caracteres, padrão `"Aponte a câmera para o QR Code"` |
| `logo` | arquivo | não | PNG ou JPG, até 3 MB — redimensionado automaticamente para 300x300 |
| `remove_logo` | checkbox | não | ignorado na criação (só faz sentido em edição) |

\* pelo menos **um** entre `android_url`, `ios_url` e `desktop_url` é obrigatório —
essa checagem não é feita pelo WTForms, é manual no `app.py`.

**Retorno:**
- Sucesso: `302` → `/qr/<slug>` (slug gerado automaticamente, 8 caracteres).
- Falha de validação, ou nenhuma das 3 URLs preenchida: `200` (form reexibido
  com erro).

**Erros possíveis:**
- `400` — token CSRF ausente/inválido.

---

## `GET /qr/<slug>`

Detalhe de um QR Code (destinos configurados, aparência, botões de download).
Requer login; qualquer usuário logado pode ver (painel compartilhado). Os
botões "Editar"/"Excluir" só aparecem se for o dono do QR Code ou master, e o
botão "Baixar página p/ Netlify" só aparece para master.

**Retorno:** `200` com a página HTML.

**Erros possíveis:**
- `404` — slug não existe.

---

## `GET|POST /qr/<slug>/editar`

Mesmos campos e regras de `POST /qr/novo`, mais:

| Campo extra | Tipo | Efeito |
|---|---|---|
| `remove_logo` | checkbox | se marcado e nenhum novo `logo` for enviado, remove o logo atual |

Se `logo` vier preenchido, ele substitui o logo atual (tem prioridade sobre `remove_logo`).

Requer ser o dono do QR Code **ou** ser master.

**Retorno:** `302` → `/qr/<slug>` em caso de sucesso; `200` (form com erro) em caso de falha.
**Erros:**
- `404` — slug não existe.
- `403` — usuário padrão tentando editar QR Code de outra pessoa.

---

## `POST /qr/<slug>/excluir`

Exclui o QR Code. Requer login e ser o dono do QR Code **ou** ser master.

**Parâmetros:** só `csrf_token`.

**Retorno:** `302` → `/dashboard`.

**Erros possíveis:**
- `400` — token CSRF ausente/inválido.
- `404` — QR Code não encontrado.
- `403` — usuário padrão tentando excluir QR Code de outra pessoa.

---

## `GET /qr/<slug>/pagina-netlify`

Baixa um `index.html` autocontido (HTML+CSS+JS, sem dependências) já
preenchido com `android_url`/`ios_url` do QR Code, pronto para publicar em
qualquer host estático (Netlify, GitHub Pages etc). **Restrito ao usuário
master.**

**Retorno:** `200`, `Content-Type: text/html`, `Content-Disposition: attachment; filename=index.html`.

**Erros possíveis:**
- `403` — usuário logado não é master.
- `404` — slug não existe.

---

## `GET /qr/<slug>/preview.png`

Gera a imagem do QR Code (com degradê, borda, logo e legenda atuais) e retorna
inline — é o `src` usado nos `<img>` do painel e da tela de detalhe. Requer
login (qualquer usuário logado, não só o dono — painel compartilhado). **Não
tem cache**: reprocessa a imagem a cada chamada.

**Retorno:** `200`, `Content-Type: image/png`.
**Erros:** `404` — slug não existe.

---

## `GET /qr/<slug>/download/<fmt>`

Mesma imagem de `preview.png`, mas como anexo para download.

**Parâmetro de caminho:**

| Parâmetro | Valores aceitos |
|---|---|
| `fmt` | `png`, `jpg` ou `pdf` — qualquer outro valor dá erro |

**Retorno:** `200`, `Content-Disposition: attachment`, nome do arquivo derivado
de `name` (caracteres não alfanuméricos removidos).

**Erros possíveis:**
- `400` — `fmt` fora de `png`/`jpg`/`pdf`.
- `404` — QR Code não encontrado.

---

## `GET /usuarios`

Lista todos os usuários cadastrados e o papel de cada um. **Restrito ao
usuário master.**

**Retorno:** `200` com a página HTML.
**Erros possíveis:** `403` — usuário logado não é master.

---

## `POST /usuarios/<id>/papel`

Alterna o papel do usuário `<id>`: se ele era `padrao` vira `master`, se era
`master` vira `padrao`. **Restrito ao usuário master.**

**Parâmetros:** só `csrf_token`.

**Retorno:** `302` → `/usuarios`.

**Erros possíveis:**
- `400` — token CSRF ausente/inválido.
- `403` — usuário logado não é master.
- `404` — `<id>` não corresponde a nenhum usuário.
- Rebaixar o **último** usuário master do sistema é bloqueado (fica como
  master, com uma mensagem flash explicando — não retorna erro HTTP, só não
  aplica a mudança).

---

## `GET /r/<slug>` (rota pública, sem login)

O link que fica gravado dentro do QR Code quando o campo `desktop_url` está
vazio. Detecta o dispositivo pelo cabeçalho `User-Agent` e redireciona.

**Retorno:** `302` para:
- `android_url`, se o `User-Agent` contiver `"android"`;
- `ios_url`, se contiver `"iphone"`, `"ipad"` ou `"ipod"`;
- senão, `desktop_url` → `android_url` → `ios_url`, na primeira que existir.

**Erros possíveis:**
- `404` — slug não existe, ou nenhuma das três URLs está preenchida para esse QR Code.

---

## Exemplo real de uso (via `curl`, ponta a ponta)

```bash
# 1) pega o formulário de cadastro e extrai o token CSRF
curl -c cookies.txt -s http://localhost:5000/registrar -o registrar.html
TOKEN=$(grep -oE 'name="csrf_token"[^>]*value="[^"]+"' registrar.html | grep -oE 'value="[^"]+"' | cut -d'"' -f2)

# 2) cria a conta
curl -b cookies.txt -c cookies.txt -s -o /dev/null -w "%{http_code}\n" \
  -X POST http://localhost:5000/registrar \
  -d "csrf_token=$TOKEN" \
  -d "username=empresa_teste" \
  -d "password=SenhaForte123" \
  -d "confirm_password=SenhaForte123"
# saída esperada: 302

# 3) login
curl -b cookies.txt -c cookies.txt -s http://localhost:5000/login -o login.html
TOKEN=$(grep -oE 'name="csrf_token"[^>]*value="[^"]+"' login.html | grep -oE 'value="[^"]+"' | cut -d'"' -f2)
curl -b cookies.txt -c cookies.txt -s -o /dev/null -w "%{http_code}\n" \
  -X POST http://localhost:5000/login \
  -d "csrf_token=$TOKEN" -d "username=empresa_teste" -d "password=SenhaForte123"
# saída esperada: 302

# 4) cria um QR Code (sem logo, via x-www-form-urlencoded — só funciona
#    porque não estamos enviando o campo "logo"; com logo, precisa ser
#    multipart/form-data, ex: curl -F)
curl -b cookies.txt -c cookies.txt -s http://localhost:5000/qr/novo -o novo.html
TOKEN=$(grep -oE 'name="csrf_token"[^>]*value="[^"]+"' novo.html | grep -oE 'value="[^"]+"' | cut -d'"' -f2)
curl -b cookies.txt -c cookies.txt -s -i \
  -X POST http://localhost:5000/qr/novo \
  -d "csrf_token=$TOKEN" \
  -d "name=App da Empresa" \
  -d "android_url=https://play.google.com/store/apps/details?id=com.empresa.app" \
  -d "ios_url=https://apps.apple.com/app/empresa/id123456789" \
  -d "desktop_url=" \
  -d "color_start=%234F46E5" -d "color_end=%2306B6D4" \
  -d "gradient_direction=radial" -d "border_color=%23111827" \
  -d "caption_text=Aponte a câmera para o QR Code"
```

**Saída (cabeçalho da resposta):**

```
HTTP/1.1 302 FOUND
Location: /qr/9tiErpnF
```

`9tiErpnF` é o slug gerado. A partir daí:

- `GET /qr/9tiErpnF` → página com o QR Code e os botões de download.
- `GET /qr/9tiErpnF/download/png` → arquivo `App_da_Empresa.png`.
- `GET /r/9tiErpnF` (sem estar logado, de um celular) → `302` para a URL da
  Google Play ou da App Store, conforme o aparelho.

---

## Modelos de dados (para referência)

**`User`** (`models.py`): `id`, `username`, `password_hash`, `role`
(`"master"` ou `"padrao"`), `created_at`, `failed_login_attempts`, `locked_until`.

**`QRCode`** (`models.py`): `id`, `user_id`, `name`, `slug`, `android_url`,
`ios_url`, `desktop_url`, `color_start`, `color_end`, `gradient_direction`,
`border_color`, `caption_text`, `logo_filename`, `created_at`, `updated_at`.

Não existe endpoint que devolva esses dados em JSON — toda a "API" é
HTML renderizado no servidor (SSR), exceto as rotas de imagem/arquivo listadas
acima.
