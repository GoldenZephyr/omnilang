from setuptools import find_packages, setup

setup(
    name="omnilang",
    version="0.0.1",
    url="",
    author="",
    author_email="",
    description="Framework for specifying and solver scene graph planning problems",
    package_dir={"": "src"},
    packages=find_packages("src"),
    package_data={"": ["*.yaml", "*.pddl", "*.lark", "*.lp"]},
    install_requires=["lark", "clingo"],
)
