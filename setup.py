from setuptools import setup, find_packages

# Read requirements
with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="busygit",
    version="0.1",
    packages=find_packages(
        include=["busygit", "busygit.*"]
    ),  # This ensures all subdirectories
    package_data={"busygit": ["ui/components/*", "config/*", "git_tasks/*"]},
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "busygit=busygit.main:main",
        ],
    },
    author="PaysanCorrezien",
    description="A Git utility tool to manage lots of repositories",
    url="https://github.com/PaysanCorrezien/BusyGit",
)
