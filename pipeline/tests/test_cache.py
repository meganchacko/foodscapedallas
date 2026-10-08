from pipeline.cache import clear_map_cache, create_redis


def test_clear_map_cache_deletes_only_map_keys(test_redis):
    test_redis.set("tracts:v1", "old map data")
    test_redis.set("geocode:main st", "unrelated")

    cleared = clear_map_cache(test_redis)

    assert cleared == 1
    assert test_redis.get("tracts:v1") is None
    assert test_redis.get("geocode:main st") is not None


def test_clear_map_cache_doesnt_fail_when_redis_is_down():
    unreachable = create_redis(host="localhost", port=1)  # nothing listens on port 1

    assert clear_map_cache(unreachable) == 0
