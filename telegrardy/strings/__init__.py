from collections import UserDict
import telegrardy.strings as strings
import importlib.resources as pkg_resources
import sys
import tomlkit
import types


class ModuleDict(types.ModuleType, UserDict):
    data = tomlkit.parse(pkg_resources.read_text(strings, "en_US.toml"))


sys.modules[__name__] = ModuleDict(__name__)
