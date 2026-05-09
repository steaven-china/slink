from setuptools import setup, find_packages

setup(
    name="slinks",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "click>=8.0.0",
        "cryptography>=41.0.0",
    ],
    entry_points={
        "console_scripts": [
            "sli=slink.cli:main",
            "sli-ui=slink.gui:main",
        ],
    },
    python_requires=">=3.8",
    description="Secure SSH Connection Manager with encrypted storage",
    license="LGPL-3.0",
    author="",
    author_email="",
)
