from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="snc",
    version="0.1.0",
    author="Weston Voglesonger",
    author_email="weston@voglesonger.com",
    description="System Narrative Compiler",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/WestonVoglesonger/System-Narrative-Compiler",
    packages=find_packages(),
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
        "click>=8.0.0,<9.0.0",
    ],
    entry_points={
        "console_scripts": [
            "snc=snc.cli.main:cli",
            "snc-init=snc.cli.setup_cmd:init",
            "snc-validate=snc.cli.validate_cmd:validate",
            "snc-repl=snc.script.repl:main",
        ],
    },
)
