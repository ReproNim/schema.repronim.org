import asyncio
from datetime import datetime
from datetime import timedelta
import math
import uuid
import sys
import os
import subprocess as sp

from sanic import Sanic
from sanic.log import logger, error_logger, access_logger
from sanic import response
from sanic.response import json, text
from sanic_cors import CORS, cross_origin

LOG_SETTINGS = dict(
    version=1,
    disable_existing_loggers=False,
    loggers={
        "sanic.root": {"level": "INFO", "handlers": ["console", "consolefile"]},
        "sanic.error": {
            "level": "INFO",
            "handlers": ["error_console", "error_consolefile"],
            "propagate": True,
            "qualname": "sanic.error",
        },
        "sanic.access": {
            "level": "INFO",
            "handlers": ["access_console", "access_consolefile"],
            "propagate": True,
            "qualname": "sanic.access",
        },
    },
    handlers={
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "generic",
            "stream": sys.stdout,
        },
        "error_console": {
            "class": "logging.StreamHandler",
            "formatter": "generic",
            "stream": sys.stderr,
        },
        "access_console": {
            "class": "logging.StreamHandler",
            "formatter": "access",
            "stream": sys.stdout,
        },
        "consolefile": {
            'class': 'logging.FileHandler',
            'filename': "/vagrant/controller/console.log",
            "formatter": "generic",
        },
        "error_consolefile": {
            'class': 'logging.FileHandler',
            'filename': "/vagrant/controller/error.log",
            "formatter": "generic",
        },
        "access_consolefile": {
            'class': 'logging.FileHandler',
            'filename': "/vagrant/controller/access.log",
            "formatter": "access",
        },
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

app = Sanic("controller", log_config=LOG_SETTINGS)
CORS(app)

@app.route("/")
async def main(request):
    return json({"hello": "world"})


async def restart_docker_compose(service=None):
    dc_cmd = ["docker-compose",
              "-f",
              "/home/ubuntu/src/docker-compose.yml"]
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
    return 0


@app.route("/status", methods=["GET", ])
async def get_status(request):
    cproc = sp.run(['docker', 'ps', '-a'], stdout=sp.PIPE, stderr=sp.PIPE)
    return json({"status": cproc})

TOKEN = None

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
        import uuid
        TOKEN = str(uuid.uuid4()).split('-')[-1]
        logger.info(f"TOKEN={TOKEN}")
    app.run(host="0.0.0.0", port=8003)
