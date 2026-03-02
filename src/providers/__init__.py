"""Auto-discovers and imports all emulator provider classes in this package."""

import os
import importlib
import inspect

pkg_dir = os.path.dirname(__file__)

# Import all .py provider files
for filename in os.listdir(pkg_dir):
    if filename.endswith(".py") and filename != "__init__.py":
        module_name = filename[:-3]
        module = importlib.import_module(f".{module_name}", package=__name__)

        for name, obj in inspect.getmembers(module):
            if inspect.isclass(obj) and obj.__module__ == module.__name__:
                globals()[name] = obj
