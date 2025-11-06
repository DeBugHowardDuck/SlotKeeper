from slotkeeper import __version__

def test_version_present():
    assert isinstance(__version__, str) and len(__version__) > 0
