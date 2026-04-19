# Stapler

![logo.svg](logo.svg)

```txt
usage: stapler [-h] [--debug | --no-debug] [-d DATA_DIR] [--certificates | --no-certificates] [--certbot | --no-certbot]
               [--self-signed-path SELF_SIGNED_PATH] [--certbot-conf CERTBOT_CONF] [--certbot-www CERTBOT_WWW]
               [--host HOST] [--http-port HTTP_PORT] [--https-port HTTPS_PORT] [--https | --no-https] [-t TOKEN_SALT]
               [--max-size-bytes MAX_SIZE] [-b BIND]
               COMMAND ...

Static pages as simple as a gzip file

positional arguments:
  COMMAND
    run                 Run Stapler server
    renew               Renew certificates
    token               Generate a new token

options:
  -h, --help            show this help message and exit
  --debug, --no-debug
  -d, --data-dir DATA_DIR
                        directory where pages are/will be stored (default: ./data)
  --certificates, --no-certificates
                        Handle certificates (default: true)
  --certbot, --no-certbot
                        Use Certbot (default: true)
  --self-signed-path SELF_SIGNED_PATH
                        Self-signed certificates dir (default: ./data/.certificates)
  --certbot-conf CERTBOT_CONF
                        Certbot config dir (default: /etc/letsencrypt)
  --certbot-www CERTBOT_WWW
                        Certbot www dir (default: ./data/.certbot)
  --host HOST           server default host (default: localhost)
  --http-port HTTP_PORT
                        server http port (default: 80)
  --https-port HTTPS_PORT
                        server https port (default: 443)
  --https, --no-https   Use https (implies --certificates) (default: true)
  -t, --token-salt TOKEN_SALT
                        salt for tokens generation
  --max-size-bytes MAX_SIZE
                        max size of accepted archives (in bytes) (default: 2000000)
  -b, --bind BIND       server bind address (default: 0.0.0.0)

(Each option can be supplied with equivalent environment variable.)
```

## Endpoints

### Create/update page

```txt
PUT /{page}/
```

```bash
# create archive from 'dist' dir and upload to /my-project/
tar -czC dist . | curl -X PUT \
  --data-binary @- \
  -H 'X-Token: <TOKEN>' \
  https://stapler-host/my-project/

# create archive from 'dist' dir and upload to /my-project/ and myproject.example.com
tar -czC dist . | curl -X PUT \
  --data-binary @- \
  -H 'X-Token: <TOKEN>' \
  -H 'X-Host: myproject.example.com' \
  https://stapler-host/my-project/
```

### Delete page

```txt
DELETE /{page}/
```

```bash
# delete /my-project/
curl -X DELETE \
  -H 'X-Token: <TOKEN>' \
  https://stapler-host/my-project/
```

## Development

### TODO

- [x] basic http server
- [x] docker container
- [x] env instead of args when available
- [x] PUT gzip data into /data/xxx
- [x] DELETE request
- [x] max file size
- [x] .host in /data/xxx can be translated as host in GET /
- [x] header to setup .host file instead of in archive
- [x] ignore .gitignore/.host etc at root
- [x] cerbot install in container + path env/arg
- [x] redirect /.well-known/acme-challenge to specific path
- [x] certbot/self-signed create/renew in specific dir
- [x] better logger
- [x] renew command
- [x] https mode w/ multiple hosts
- [x] create certificate on request
- [x] certbot copy certificates for unique path
- [x] better error page
- [x] add favicon.ico + special path
- [x] [http.server security](https://docs.python.org/3/library/http.server.html#http-server-security)
- [x] launch separate upgrade 80->443 server when https
- [x] token management with "generate" command and bind path to specific token
- [x] docker compose example + .env
- [x] 404 GET on host not found
- [x] 403 PUT on host already taken
- [x] remove dot files after file extract
- [x] unit tests
- [x] github actions
- [ ] X-Redirect
- [ ] X-Proxy
- [ ] proper doc

### Makefile targets

```txt
Usage: make [target1] [target2] ...

Commands/Targets:
help                 show this message
install              install project
update               update project dependencies
format               format project
lint                 lint project
build                build project
start                start server in localhost
test                 test project
test-%               test project with specific test
coverage             test project with coverage
uv-sync              uv sync
uv-upgrade           uv sync upgrade
ruff                 ruff check
ruff-fix             ruff check (and fix)
ruff-format          ruff format
ruff-format-check    ruff format (check only)
ty                   ty check
unittest             unittest
unittest-%           unittest -k [filter]
coverage-unittest    coverage run -m unittest
coverage-report      coverage report
coverage-html        coverage html
coverage-xml         coverage xml
docker-build         docker build
docker-run           docker run
```
