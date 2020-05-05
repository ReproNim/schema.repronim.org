import uuid
import os
import subprocess as sp

from sanic import Sanic
from sanic.log import logger
from sanic.response import json
from sanic_cors import CORS

production = 'DEV4d2966bb4488' not in os.environ
basedir = os.environ["HOME"] if production else os.getcwd()
logdir = os.path.join(basedir, "controller")
if not os.path.exists(logdir):
    os.makedirs(logdir, exist_ok=True)
TOKEN = None
handler_dict = {"class": "logging.handlers.TimedRotatingFileHandler",
                "when": 'D',
                "interval": 7,
                "backupCount": 10,
                "formatter": "generic",
                }
LOG_SETTINGS = dict(
    version=1,
    disable_existing_loggers=False,
    loggers={
        "sanic.root": {"level": "INFO", "handlers": ["consolefile"]},
        "sanic.error": {
            "level": "INFO",
            "handlers": ["error_consolefile"],
            "propagate": True,
            "qualname": "sanic.error",
        },
        "sanic.access": {
            "level": "INFO",
            "handlers": ["access_consolefile"],
            "propagate": True,
            "qualname": "sanic.access",
        },
    },
    handlers={
        "consolefile": {**handler_dict,
                        **{'filename': os.path.join(logdir, "console.log")}},
        "error_consolefile": {**handler_dict,
                              **{'filename': os.path.join(logdir, "error.log")}},
        "access_consolefile": {**handler_dict,
                               **{'filename': os.path.join(logdir, "access.log")}},
    },
    formatters={
        "generic": {
            "format": "%(asctime)s [%(process)d] [%(levelname)s] %(message)s",
            "datefmt": "[%Y-%m-%d %H:%M:%S %z]",
            "class": "logging.Formatter",
        },
        "access": {
            "format": "%(asctime)s - (%(name)s)[%(levelname)s][%(host)s]: "
                      + "%(request)s %(message)s %(status)d %(byte)d",
            "datefmt": "[%Y-%m-%d %H:%M:%S %z]",
            "class": "logging.Formatter",
        },
    },
)

if production:
    app = Sanic("controller", log_config=LOG_SETTINGS)
else:
    app = Sanic("controller")
CORS(app)


@app.route("/")
async def main(request):
    return json({"hello": "world"})


async def restart_docker_compose(service=None):
    dc_cmd = ["docker-compose",
              "-f",
              "docker-compose.yml"]
    down_cmd = dc_cmd + ["down",
                         "--rmi",
                         "all"]
    build_cmd = dc_cmd + ["build",
                          "--no-cache"]
    up_cmd = dc_cmd + ["up",
                       "-d"]
    if service is not None:
        build_cmd += [service]
        up_cmd += [service]
    else:
        logger.info('Recreating all containers.')
    try:
        if service is None:
            logger.info('Downing all services')
            cproc = sp.run(down_cmd, stdout=sp.PIPE, stderr=sp.PIPE)
        else:
            logger.info('Rebuilding services: {}.'.format(service))
            cproc = sp.run(build_cmd, stdout=sp.PIPE, stderr=sp.PIPE)
        logger.info('Bringing up services.')
        cproc = sp.run(up_cmd, stdout=sp.PIPE, stderr=sp.PIPE)
    except sp.SubprocessError as e:
        return 1
    logger.info('Completed reset: {}'.format(cproc))
    prune_cmd = ["docker", "system", "prune", "-af"]
    try:
        logger.info("Pruning docker")
        cproc = sp.run(prune_cmd, stdout=sp.PIPE, stderr=sp.PIPE)
    except sp.SubprocessError as e:
        return 1
    logger.info('Completed prune: {}'.format(cproc))
    return 0


@app.route("/status", methods=["GET", ])
async def get_status(request):
    cproc = sp.run(['docker', 'ps', '-a'], stdout=sp.PIPE, stderr=sp.PIPE)
    return json({"status": cproc})


@app.route("/reset", methods=["POST", ])
async def post_reset(request):
    if 'token' not in request.json:
        return json({"error": 128})
    if request.json['token'] != TOKEN:
        return json({"error": 127})
    service_names = None
    if 'services' in request.json:
        service_names = request.json['services'] # list of services to recreate
    errorcode = await restart_docker_compose(service_names)
    return json({"error": errorcode})


if __name__ == "__main__":
    logger.info("Starting backend")
    if TOKEN is None:
        TOKEN = uuid.uuid4().hex
        logger.info(f"TOKEN={TOKEN}")
    app.run(host="0.0.0.0", port=8003)
