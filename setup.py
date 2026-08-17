from os import path, walk
from setuptools import setup, find_packages
import shutil

var_strResourcesPath = ""

var_strDir = path.abspath(path.dirname(__file__))

var_strDocsPath = "docs"
var_strTestsPath = "tests"
var_strMainPackage = "prj_TCC_PREVISOR_STEAM"

for var_strRaiz, var_listSubDir, var_listArquivos in walk(var_strDir):
    for var_strSub in var_listSubDir:
        for var_strRaiz_nvl2, var_listSubDir_nvl2, var_listArquivos_nvl2 in walk(path.join(var_strRaiz, var_strSub)):
            if "resources" in var_listSubDir_nvl2:
                var_strResourcesPath = path.join(var_strRaiz_nvl2, "resources")

if path.exists(var_strResourcesPath):
    shutil.rmtree(var_strResourcesPath)

with open(path.join(var_strDir, "README.md"), encoding="utf-8") as var_fileReadme:
    readme = var_fileReadme.read()

with open(path.join(var_strDir, "VERSION"), encoding="utf-8") as var_fileVersion:
    version = var_fileVersion.read()

with open(path.join(var_strDir, "requirements.txt")) as var_fileRequirements:
    requirements = [linha for linha in var_fileRequirements.read().splitlines() if not linha.startswith("#")]

setup(
    name=var_strMainPackage,
    version=version,
    author="Camilo Prado",
    author_email="camilovgprado21@gmail.com",
    description="Projeto de previsor de preços utilizando Machine Learning. Com foco na plataforma Steam.",
    long_description=readme,
    long_description_content_type="text/markdown",
    packages=find_packages(exclude=[var_strDocsPath, var_strTestsPath]),
    include_package_data=True,
    package_data={
        var_strMainPackage: ["resources/*"]
        },
    install_requires=requirements,
)