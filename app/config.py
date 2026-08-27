import os


class BaseConfig:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-insecure-key")

    # meta_p (the cross-wiki metadata DB listing every wiki) lives on a
    # fixed shard, not at meta.<cluster>.db.svc.wikimedia.cloud like a
    # regular per-wiki replica -- confirmed straight from the Toolforge
    # `sql` CLI's own source (/usr/bin/sql): "server = f's7.{domain}'" is
    # special-cased for db == "meta_p", with a comment warning not to
    # confuse it with metawiki_p (a normal per-wiki db, reachable the usual
    # way via wiki_db_host("metawiki")).
    META_DB_HOST = os.environ.get("META_DB_HOST", "s7.analytics.db.svc.wikimedia.cloud")


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class TestingConfig(BaseConfig):
    TESTING = True


class ProductionConfig(BaseConfig):
    DEBUG = False


CONFIG_BY_NAME = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
