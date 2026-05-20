# CV Tailor — Guia de Deploy

## Pré-requisitos

- Docker + Docker Compose instalados
- Nginx Proxy Manager rodando
- Domínio apontando para o IP do servidor (ex: `cvtailor.seudominio.com`)
- Chave de API da Anthropic: https://console.anthropic.com

---

## 1. Copiar os arquivos para o servidor

```bash
# Na sua máquina local, envie o projeto para o servidor
scp -r cv-tailor/ usuario@seu-servidor:/opt/cv-tailor

# Ou clone do seu repositório Git:
# ssh usuario@seu-servidor
# git clone https://github.com/voce/cv-tailor.git /opt/cv-tailor
```

---

## 2. Configurar variáveis de ambiente

```bash
cd /opt/cv-tailor

# Copie o exemplo e edite
cp .env.example .env
nano .env
```

Preencha no `.env`:

```env
# Gere com: python3 -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=sua-chave-gerada-aqui

ANTHROPIC_API_KEY=sk-ant-sua-chave-aqui

ADMIN_USERNAME=admin
ADMIN_PASSWORD=uma-senha-forte-aqui
```

---

## 3. Garantir que a network do NPM existe

O Nginx Proxy Manager usa uma rede Docker compartilhada. Verifique o nome da rede que seu NPM usa:

```bash
docker network ls
```

Procure algo como `npm_default`, `proxy`, ou `nginx-proxy-manager_default`.

Se a rede se chama diferente de `proxy`, edite o `docker-compose.yml`:

```yaml
networks:
  proxy:
    external: true
```

Troque `proxy` pelo nome real da sua rede. Ou crie a rede se não existir:

```bash
docker network create proxy
```

E adicione o container do NPM a ela, se necessário.

---

## 4. Build e start

```bash
cd /opt/cv-tailor

# Build da imagem e subir o container
docker compose up -d --build

# Verificar logs
docker compose logs -f cv-tailor
```

Na primeira execução, você verá:
```
[seed] Admin 'admin' criado.
INFO:     Application startup complete.
```

---

## 5. Configurar o Nginx Proxy Manager

1. Acesse o painel do NPM (geralmente `http://seu-servidor:81`)
2. Vá em **Proxy Hosts** → **Add Proxy Host**
3. Preencha:
   - **Domain Names**: `cvtailor.seudominio.com`
   - **Scheme**: `http`
   - **Forward Hostname/IP**: `cv-tailor` (nome do container) ou `127.0.0.1`
   - **Forward Port**: `8100`
   - Marque **Block Common Exploits**
4. Na aba **SSL**:
   - Selecione **Request a new SSL Certificate**
   - Marque **Force SSL** e **HTTP/2 Support**
   - Aceite os termos do Let's Encrypt
5. Salve.

> **Atenção**: Se usar o nome do container (`cv-tailor`), o container do NPM e o cv-tailor precisam estar na mesma rede Docker. Se usar `127.0.0.1`, o binding `127.0.0.1:8100:8000` no compose já garante isso.

---

## 6. Verificar

Acesse `https://cvtailor.seudominio.com` — deve aparecer a tela de login.

Login inicial:
- **Usuário**: `admin` (ou o que você definiu no `.env`)
- **Senha**: a senha que você colocou em `ADMIN_PASSWORD`

---

## 7. Criar o usuário para compartilhar

1. Faça login como admin
2. Clique em **Admin** no canto superior direito
3. Preencha os dados do novo usuário e clique em **Criar usuário**
4. Compartilhe as credenciais com a pessoa

---

## Operações comuns

### Atualizar o código

```bash
cd /opt/cv-tailor
git pull                          # se estiver usando Git
docker compose up -d --build      # rebuild e restart
```

### Ver logs em tempo real

```bash
docker compose logs -f cv-tailor
```

### Backup do banco de dados

```bash
cp /opt/cv-tailor/data/cv_tailor.db /opt/backups/cv_tailor_$(date +%Y%m%d).db
```

### Parar o serviço

```bash
docker compose down
```

### Reiniciar

```bash
docker compose restart cv-tailor
```

---

## Estrutura do projeto

```
cv-tailor/
├── backend/
│   ├── app/
│   │   ├── core/         # config, database, security
│   │   ├── models/       # SQLAlchemy models (User, CVProfile, GeneratedCV)
│   │   ├── routers/      # FastAPI routers (auth, users, profile, cv)
│   │   ├── schemas/      # Pydantic schemas
│   │   └── main.py       # Entrypoint
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   └── index.html        # SPA completo
├── data/                 # SQLite (criado automaticamente, mapeado como volume)
├── docker-compose.yml
├── .env                  # Não versionar!
├── .env.example
└── .gitignore
```

---

## API — Documentação automática

Com o container rodando, acesse:
- `https://cvtailor.seudominio.com/docs` — Swagger UI interativo
- `https://cvtailor.seudominio.com/redoc` — Redoc

Útil para testar endpoints e entender o contrato da API.
