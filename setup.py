from setuptools import setup, find_packages

setup(
    name="st7796_rpi",
    version="0.1.0",
    author="Andrés",
    author_email="andres.castrom@gmail.com",
    description="Driver para pantallas ST7796 en Raspberry Pi",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/AndGonZ1/st7796_rpi",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
    install_requires=[
        "spidev>=3.5",
        "RPi.GPIO>=0.7.0",
        "numpy",
    ],
)