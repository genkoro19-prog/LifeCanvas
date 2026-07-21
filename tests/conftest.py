def pytest_sessionstart(session):
    session.config.option.maxfail = 1
    session.config.option.verbose = 2
