from setuptools import setup, find_packages

setup(
    name='jsonnet',
    packages=find_packages(exclude=['jsonnet.tests']),
    setup_requires=['cffi>=1.0.0'],
    cffi_modules=['jsonnet/build.py:ffibuilder'],
    install_requires=['cffi>=1.0.0'],
)
