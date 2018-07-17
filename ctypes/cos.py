# wrap c funciton
from ctypes import *
from ctypes.util import find_library

# method1: lib = cdll.LoadLibrary(find_library('cos'))
# method2: lib = cdll.LoadLibrary('lib/libcos.so')
lib = CDLL('lib/libcos.so')

lib.cos_func.argtypes = [c_double]
lib.cos_func.restype = c_double

def cos_func(x):
    x = c_double(x)
    return lib.cos_func(x)
