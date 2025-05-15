from setuptools import find_packages, setup
from Cython.Build import cythonize
import numpy as np

setup(
    ext_modules=cythonize(
        "./evsim/gradient_flow_matching/cython/get_TAM.pyx",
        language="c++",
        compiler_directives={'language_level': '3'}
    ),
    include_dirs=[np.get_include()],
    extra_compile_args=["-std=c++11"],
    extra_link_args=["-std=c++11"]
)