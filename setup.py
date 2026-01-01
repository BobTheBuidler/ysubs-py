from setuptools import find_packages, setup

with open("requirements.txt") as f:
    requirements = list(map(str.strip, f.read().split("\n")))[:-1]

setup(
    name='ysubs-py',
    python_requires=">=3.9,<3.14",
    packages=find_packages(),
    use_scm_version={
        "root": ".",
        "relative_to": __file__,
        "local_scheme": "no-local-version",
        "version_scheme": "python-simplified-semver",
    },
    description='A Python interface for ySubs smart contracts',
    author='BobTheBuidler',
    author_email='bobthebuidlerdefi@gmail.com',
    url='https://github.com/BobTheBuidler/ysubs-py',
    license='MIT',
    install_requires=requirements,
    setup_requires=['setuptools_scm']
)
