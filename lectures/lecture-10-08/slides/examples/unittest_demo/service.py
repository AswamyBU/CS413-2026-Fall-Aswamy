"""Small network boundary replaced by a mock in the tests."""
from urllib.request import urlopen


def status_code(url):
    with urlopen(url, timeout=2) as response:
        return response.status
