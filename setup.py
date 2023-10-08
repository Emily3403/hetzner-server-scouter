import re

from setuptools import setup


def open_readme_case_insensitively(directory: str = '.') -> str | None:
    for filename in os.listdir(directory):
        if filename.lower() == 'readme.md':
            with open(os.path.join(directory, filename), 'r') as f:
                return f.read()

    return None


with open("src/hetzner_server_scouter/version.py") as f:
    __version__ = re.search('"(.+)"', f.read()).group(1)

if __name__ == "__main__":
    setup(version=__version__)  # type: ignore
