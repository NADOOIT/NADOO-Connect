from setuptools import setup, find_packages

# Read requirements.txt for install_requires
with open("requirements.txt") as f:
    required = f.read().splitlines()

setup(
    name="NADOO-CONNECT",
    version="0.1.1",
    packages=find_packages(),
    install_requires=required,
    python_requires=">=3.6",
    # Add other metadata like author, description, etc.
)
