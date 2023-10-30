from setuptools import setup, find_packages
import os


def get_requirements(file):
    ff = os.path.join(os.path.dirname(__file__), file)
    lineiter = (line.strip() for line in open(ff))
    return [line for line in lineiter if line and not line.startswith("#")]


setup(
    name="inflation_app",
    version="0.1",
    packages=find_packages(),
    install_requires=get_requirements("requirements.txt"),
    python_requires=">=3.12",
    author="Carlos Ayestarán Latorre",
    author_email="carlosal1993@gmail.com",
    description=(
        "A simple dash app to plot annualised inflation rates taken from "
        "different URLs. "
        "To produce an example, run app.py."
    ),
)
