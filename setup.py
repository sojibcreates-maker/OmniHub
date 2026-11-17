from setuptools import setup, find_packages

setup(
    name="omnihub",
    version="3.0.0",
    description="Ultra-Modern Precision AI Gateway & System Studio for Linux, Windows and macOS",
    author="Md Sojib Hossain",
    author_email="sojib@matraki.org",
    url="https://github.com/sojibcreates-maker/OmniHub",
    packages=find_packages(),
    py_modules=["main"],
    install_requires=[
        "PyQt5>=5.15.0",
        "requests>=2.28.0",
        "psutil>=5.9.0",
    ],
    entry_points={
        "console_scripts": [
            "omnihub=main:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
)
