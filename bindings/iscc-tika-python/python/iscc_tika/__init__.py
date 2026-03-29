import os
from platform import system

# On Windows there is no equivalent way of setting RPATH
# This adds the current directory to PATH so that the graalvm libs will be found
if system() == "Windows":
    libpath = os.path.dirname(__file__)
    os.environ["PATH"] = libpath + os.pathsep + os.environ["PATH"]

from ._iscc_tika import *

__doc__ = _iscc_tika.__doc__
__all__ = _iscc_tika.__all__
