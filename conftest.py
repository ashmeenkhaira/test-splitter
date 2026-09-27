import json
durations = {}
def pytest_runtest_logreport(report):
    durations[report.nodeid] = durations.get(report.nodeid,0) +report.duration

def pytest_sessionfinish(session, exitstatus):
    with open(".test-durations.json", "w") as f:
        json.dump(durations, f, indent=2)