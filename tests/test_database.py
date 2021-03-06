# coding: utf-8
from beaker._compat import u_

from beaker.cache import clsmap, Cache, util
from beaker.exceptions import InvalidCacheBackendError
from beaker.middleware import CacheMiddleware
from nose import SkipTest

try:
    from webtest import TestApp
except ImportError:
    TestApp = None


try:
    clsmap["ext:database"]._init_dependencies()
except InvalidCacheBackendError:
    raise SkipTest("an appropriate SQLAlchemy backend is not installed")

db_url = "sqlite:///test.db"


def simple_app(environ, start_response):
    extra_args = {}
    clear = False
    if environ.get("beaker.clear"):
        clear = True
    extra_args["type"] = "ext:database"
    extra_args["url"] = db_url
    extra_args["data_dir"] = "./cache"
    cache = environ["beaker.cache"].get_cache("testcache", **extra_args)
    if clear:
        cache.clear()
    try:
        value = cache.get_value("value")
    except:
        value = 0
    cache.set_value("value", value + 1)
    start_response("200 OK", [("Content-type", "text/plain")])
    return [("The current value is: %s" % cache.get_value("value")).encode("utf-8")]


def cache_manager_app(environ, start_response):
    cm = environ["beaker.cache"]
    cm.get_cache("test")["test_key"] = "test value"

    start_response("200 OK", [("Content-type", "text/plain")])
    yield ("test_key is: %s\n" % cm.get_cache("test")["test_key"]).encode("utf-8")
    cm.get_cache("test").clear()

    try:
        test_value = cm.get_cache("test")["test_key"]
    except KeyError:
        yield ("test_key cleared").encode("utf-8")
    else:
        yield ("test_key wasn't cleared, is: %s\n" % test_value).encode("utf-8")


def test_has_key():
    cache = Cache("test", data_dir="./cache", url=db_url, type="ext:database")
    o = object()
    cache.set_value("test", o)
    assert cache.has_key("test")
    assert "test" in cache
    assert not cache.has_key("foo")
    assert "foo" not in cache
    cache.remove_value("test")
    assert not cache.has_key("test")


def test_has_key_multicache():
    cache = Cache("test", data_dir="./cache", url=db_url, type="ext:database")
    o = object()
    cache.set_value("test", o)
    assert cache.has_key("test")
    assert "test" in cache
    cache = Cache("test", data_dir="./cache", url=db_url, type="ext:database")
    assert cache.has_key("test")
    cache.remove_value("test")


def test_clear():
    cache = Cache("test", data_dir="./cache", url=db_url, type="ext:database")
    o = object()
    cache.set_value("test", o)
    assert cache.has_key("test")
    cache.clear()
    assert not cache.has_key("test")


def test_unicode_keys():
    cache = Cache("test", data_dir="./cache", url=db_url, type="ext:database")
    o = object()
    cache.set_value(u_("hiŏ"), o)
    assert u_("hiŏ") in cache
    assert u_("hŏa") not in cache
    cache.remove_value(u_("hiŏ"))
    assert u_("hiŏ") not in cache


@util.skip_if(lambda: TestApp is None, "webtest not installed")
def test_increment():
    app = TestApp(CacheMiddleware(simple_app))
    res = app.get("/", extra_environ={"beaker.clear": True})
    assert "current value is: 1" in res
    res = app.get("/")
    assert "current value is: 2" in res
    res = app.get("/")
    assert "current value is: 3" in res


@util.skip_if(lambda: TestApp is None, "webtest not installed")
def test_cache_manager():
    app = TestApp(CacheMiddleware(cache_manager_app))
    res = app.get("/")
    assert "test_key is: test value" in res
    assert "test_key cleared" in res
