from setuptools import setup, find_packages

setup(
    name="qnote",
    version="1.0.2",
    description="Minimalist Scratchpad with 10 Eye-friendly Papers & Silky Ink Drawing",
    author="realsky",
    packages=find_packages(),
    install_requires=[
        "PyQt6>=6.5.0",
        "pynput>=1.7.6",
    ],
    entry_points={
        "console_scripts": [
            "qnote=main:main",
        ],
    },
    python_requires=">=3.8",
)
