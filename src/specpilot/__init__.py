import importlib.metadata

try:
    __version__ = importlib.metadata.version("specpilot")
except importlib.metadata.PackageNotFoundError:
    __version__ = "1.2.0"



