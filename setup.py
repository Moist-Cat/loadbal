import setuptools
from pathlib import Path

with open("README.md", "r") as file:
    long_description = file.read()

with open("requirements.txt") as file:
    REQUIREMENTS = file.read().split("\n")

setuptools.setup(
     name="loadbal",
     version="0.0.1",
     author="Moist-Cat",
     author_email="moistanonpy@gmail.com",
     description="Load baalncer for distributed services",
     long_description=long_description,
   long_description_content_type="text/markdown",
     url="https://github.com/Moist-Cat/loadbal",
     install_requires=REQUIREMENTS,
     include_package_data=True,
     package_dir={"":"src"},
     packages=setuptools.find_packages(where="src"),
     python_requires=">=3",
     classifiers=[
         "Programming Language :: Python :: 3",
#         "License :: OSI Approved :: MIT License",
         "Operating System :: POSIX :: Linux",
     ],
 )
