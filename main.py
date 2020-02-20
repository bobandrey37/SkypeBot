import logging
import os
from collections import namedtuple
from typing import List, Type

from tinydb import TinyDB
from tinydb_serialization import SerializationMiddleware

from Core.PluginBase import PluginBase
from Core.PluginsLoader import PluginsLoader
from Core.SkypeClient import SkypeClient
from Core.TinyDb.Serializers.DateTimeSerializer import DateTimeSerializer
from Core.TinyDb.Serializers.SkypeUserNameSerializer import SkypeUserNameSerializer

logging.basicConfig(
    format='%(asctime)s %(module)s %(levelname)-8s %(message)s',
    level=os.environ.get('SKYPE_LOGGING_LEVEL', 'INFO'),
    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)

Environment = namedtuple("Environment", ["username", "password", "database_file"])


def read_environment() -> Environment:
    logger.debug("Reading environment variables...")
    username = os.environ.get('SKYPE_BOT_USERNAME', None)
    password = os.environ.get('SKYPE_BOT_PASSWORD', None)
    database_file = os.environ.get('SKYPE_BOT_DATABASE_FILE', os.path.join(os.getcwd(), 'db.json'))

    if username is None or password is None:
        logger.critical('You must define following environment variables: SKYPE_BOT_USERNAME, SKYPE_BOT_PASSWORD')
        exit(-1)

    logger.info("All required environment variables are set")
    return Environment(username, password, database_file)


def serialization_config() -> SerializationMiddleware:
    def full_name(t: Type):
        return "%s.%s" % (t.__module__, t.__qualname__)

    serializers = [
        DateTimeSerializer,
        SkypeUserNameSerializer,
    ]

    middleware = SerializationMiddleware()

    for serializer in serializers:
        logger.debug("Registering serializer '%s' for type '%s'...", full_name(serializer), full_name(serializer.OBJ_CLASS))
        middleware.register_serializer(serializer(), full_name(serializer))
        logger.debug("Serializer '%s' registered", full_name(serializer))

    return middleware


def init_database(env: Environment) -> TinyDB:
    logger.debug("Initializing TinyDB...")
    db = TinyDB(env.database_file, storage=serialization_config())
    logger.info("TinyDB initialized at path %s", env.database_file)
    return db


def init_client(env: Environment) -> SkypeClient:
    logger.debug("Initializing SkypeClient...")
    client = SkypeClient(username=env.username, password=env.password)
    logger.info("SkypeClient initialized for user %s", env.username)
    return client


def init_plugins(client: SkypeClient, database: TinyDB) -> List[PluginBase]:
    logger.debug("Detecting available plugins...")
    plugins_types = PluginsLoader.load()
    logger.debug("%d plugins detected", len(plugins_types))
    logger.debug("Initializing plugins...")
    plugins = [plugin(client, database) for plugin in plugins_types]
    plugins_names = ', '.join(list(map(lambda plugin: ("'%s'" % plugin.friendly_name()), plugins)))
    logger.info("Plugins initialized: %s", plugins_names)
    return plugins


def register_plugins(plugins: List[PluginBase], client: SkypeClient):
    logger.debug("Registering plugins at client...")
    client.register_plugins(plugins)
    logger.info("Plugins registered")


def run():
    env = read_environment()
    database = init_database(env)
    client = init_client(env)
    plugins = init_plugins(client=client, database=database)
    register_plugins(plugins=plugins, client=client)

    # logger.debug("Setting presence...")
    # client.setPresence()
    logger.info("SkypeBot started")
    client.loop()


if __name__ == '__main__':
    run()
