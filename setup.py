from setuptools import setup


setup(
    name="maki",
    version="0.1.0",
    description="simple coding agent.",
    license="MIT",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
    ],
    py_modules=["maki"],
    python_requires=">=3.9",
    install_requires=[
        "openai",
    ],
    entry_points={
        "console_scripts": [
            "maki=maki:main",
        ],
    },
)
