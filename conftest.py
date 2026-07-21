def pytest_collection_modifyitems(config, items):
    selected = [item for item in items if "test_completion_audit_logic.py" in item.nodeid]
    items[:] = selected


def pytest_configure(config):
    config.option.maxfail = 1
    config.option.verbose = 2
