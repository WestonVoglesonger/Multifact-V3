from setuptools import setup, find_packages
import re

# Read version from __init__.py
with open("snc/__init__.py", encoding="utf-8") as f:
    content = f.read()
    version_match = re.search(r"__version__\s*=\s*['\"]([^'\"]+)['\"]", content)
    if not version_match:
        raise RuntimeError("Unable to find version string in snc/__init__.py")
    version = version_match.group(1)

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="snc",
    version=version,
    author="Weston Voglesonger",
    author_email="westonvogelsong@gmail.com",
    description="A system narrative compiler for allowing developers to write code in natural, narrative language.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/westonvogelsong/snc-v3",
    packages=find_packages(include=["snc", "snc.*"]),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    python_requires=">=3.8",
    install_requires=[
        "fastapi[all]>=0.100.0,<0.101.0",
        "psycopg2-binary>=2.9.5,<2.10.0",
        "sqlalchemy>=2.0.4,<2.1.0",
        "alembic>=1.10.2,<1.11.0",
        "python-dotenv>=1.0.0,<1.1.0",
        "pydantic>=1.8.0",
        "pydantic-settings>=2.0.0",
        "openai>=1.57.4,<1.58.0",
        "groq>=0.13.1,<0.14.0",
        "pyjwt>=2.6.0,<2.7.0",
        "requests>=2.31.0,<2.32.0",
        "lark-parser>=0.12.0,<0.13.0",
    ],
    entry_points={
        "console_scripts": [
            "snc-db=snc.script.create_database:main",
        ],
    },
)
