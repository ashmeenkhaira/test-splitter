import json
import os

import pytest

from splitter import split_tests
durations = {}

def pytest_runtest_logreport(report):
    durations[report.nodeid] = durations.get(report.nodeid,0) +report.duration

def pytest_sessionfinish(session, exitstatus):
    if not durations:   # no tests ran (e.g. bad --shard), so don't save an empty file
        return

    shard = session.config.getoption("--shard")
    if shard is None:
        path = ".test-durations.json"
    else:
        path = f".test-durations.shard{shard}.json"
    with open(path, "w") as f:
        json.dump(durations, f, indent=2)


def pytest_addoption(parser):
    parser.addoption("--shard", type=int, default=None, help="which shard to run (1 to N)")
    parser.addoption("--num-shards", type=int, default=None, help="total number of shards")


def pytest_collection_modifyitems(config, items):
    shard = config.getoption("--shard")
    num_shards = config.getoption("--num-shards")

    if shard is None:
        return

    if num_shards is None:
        raise pytest.UsageError("--shard also needs --num-shards")
    if shard < 1 or shard > num_shards:
        raise pytest.UsageError(f"--shard must be between 1 and {num_shards}, got {shard}")

    # A brand-new project has no recorded times yet; every test then gets the
    # 1.0 default below, which splits roughly by count until a full run exists.
    recorded = {}
    if os.path.exists(".test-durations.json"):
        with open(".test-durations.json") as f:
            recorded = json.load(f)

    test_times = {}
    for item in items:
        test_times[item.nodeid] = recorded.get(item.nodeid, 1.0)
    shards = split_tests(test_times, num_shards)
    mine = shards[shard - 1]
    keep = []
    for item in items:
        if item.nodeid in mine:
            keep.append(item)
    items[:] = keep



