from pathlib import Path

from setuptools import find_packages, setup

readme = Path(__file__).parent.parent.parent / "README.md"

setup(
    name="fedoc-multigraph-backend",
    version="0.1.0",
    description="Multigraph backend for the fedoc project",
    long_description=readme.read_text(encoding="utf-8") if readme.exists() else "",
    long_description_content_type="text/markdown",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=["Flask>=3.0"],
)
