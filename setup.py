from setuptools import setup, find_packages

setup(
    name="NADOO-CONNECT",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "python-dotenv",
        "cryptography",
        "aiosmtplib"
        # List all your dependencies here
    ],
    python_requires=">=3.6",
    # Add other metadata like author, description, etc.
)
