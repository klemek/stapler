# Stapler

```txt
usage: stapler [-h] [-p PORT] [--host HOST] [-d DATA_DIR] -t TOKEN [--max-size-bytes MAX_SIZE] [-b BIND] [--certbot-conf CERTBOT_CONF] [--certbot-www CERTBOT_WWW]

Static pages as simple as a gzip file

options:
  -h, --help            show this help message and exit
  -p, --port PORT       server port (default: 8080)
  --host HOST           server default host (default: localhost)
  -d, --data-dir DATA_DIR
                        directory where pages are/will be stored (default: ./data)
  -t, --token TOKEN     secret token for update requests
  --max-size-bytes MAX_SIZE
                        max size of accepted archives (in bytes) (default: 2000000)
  -b, --bind BIND       server bind address (default: 0.0.0.0)
  --certbot-conf CERTBOT_CONF
                        Certbot config dir (default: /etc/letsencrypt)
  --certbot-www CERTBOT_WWW
                        Certbot www dir (default: ./data/.certbot)

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
  http://stapler-host/my-project/

# create archive from 'dist' dir and upload to /my-project/ and myproject.example.com
tar -czC dist . | curl -X PUT \
  --data-binary @- \
  -H 'X-Token: <TOKEN>' \
  -H 'X-Host: myproject.example.com' \
  http://stapler-host/my-project/
```

### Delete page

```txt
DELETE /{page}/
```

```bash
# delete /my-project/
curl -X DELETE \
  -H 'X-Token: <TOKEN>' \
  http://stapler-host/my-project/
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
- [ ] renew command
- [x] https mode w/ multiple hosts
- [ ] restart command (on new/deleted host)
- [ ] proper doc
- [ ] log visits (and store accross sessions)
- [ ] deliver visits in /page/visits
- [x] better error page
- [ ] add favicon.ico + special path
- [ ] [http.server security](https://docs.python.org/3/library/http.server.html#http-server-security)

### Makefile targets

```txt
Usage: make [target1] (target2) ...

Commands/Targets:
help                 show this message
ruff                 ruff check
ruff-fix             ruff check (and fix)
ruff-format          ruff format
ruff-format-check    ruff format (check only)
ty                   ty check
docker-build         docker build
docker-run           docker run
format               format project
lint                 lint project
start                start server in localhost

Environment:
UV = uv
RUFF = uv run --active ruff
TY = uv run --active ty
DOCKER = docker
DOCKER_TAG = localhost/stapler:latest
TOKEN = secret
PORT = 8080
```
