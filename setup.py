from setuptools import setup, find_packages

setup(
    name="dirlock",
    description="A simple directory based lock implementation for Python.",
    use_scm_version=True,
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="Falk B. Schimweg",
    author_email="git@falk.schimweg.de",
    url="https://github.com/z3rone-org/dirlock",
    license="MIT",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    extras_require={
        "dev": [
            "pytest",
        ]
    },
    setup_requires=['setuptools_scm'],
    python_requires=">=3.8",
)

