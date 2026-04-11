# Stapler

```txt
usage: stapler [-h] [-p PORT] [--host HOST] [-d DATA_DIR] [-b BIND] [-t TOKEN]

Static pages as simple as a gzip file

options:
  -h, --help            show this help message and exit
  -p, --port PORT       server port (default: 8080) (env var: PORT)
  --host HOST           server default host (default: localhost) (env var: HOST)
  -d, --data-dir DATA_DIR
                        directory where files are/will be stored (default: ./data) (env var: DATA_DIR)
  -b, --bind BIND       server bind address (default: 0.0.0.0) (env var: BIND)
  -t, --token TOKEN     secret token for update requests (env var: TOKEN)
```

## Endpoints

### Create/update page

```txt
PUT /{page}/
```

```bash
# create archive from 'dist' dir and upload to /target/
tar -czC dist . | curl -X PUT \
  --data-binary @- \
  -H 'X-Token: <TOKEN>' \
  http://stapler-host/target/
```

## TODO

- [x] basic http server
- [x] docker container
- [x] env instead of args when available
- [x] PUT gzip data into /data/xxx
- [x] DELETE request
- [ ] max file size
- [ ] CNAME in /data/xxx can be translated as host in GET /
- [ ] header to setup CNAME file instead of in archive
- [ ] cerbot install in container + path env/arg
- [ ] redirect /.well-known/acme-challenge to specific path
- [ ] certbot/self-signed create/renew in specific dir
- [ ] renew command
- [ ] https mode w/ multiple hosts
- [ ] restart command (on new/deleted host)
- [ ] proper doc

## Makefile targets

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
RUFF = uv run ruff
TY = uv run ty
DOCKER = docker
DOCKER_TAG = localhost/stapler:latest
```
