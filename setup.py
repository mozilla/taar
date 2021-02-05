from setuptools import find_packages, setup

setup(
    name="mozilla-taar3",
    use_scm_version=False,
    version="1.0.7",
    setup_requires=["setuptools_scm", "pytest-runner"],
    tests_require=["pytest"],
    include_package_data=True,
    packages=find_packages(exclude=["tests", "tests/*"]),
    description="Telemetry-Aware Addon Recommender",
    author="Mozilla Foundation",
    author_email="fx-data-dev@mozilla.org",
    url="https://github.com/mozilla/taar",
    license="MPL 2.0",
    install_requires=[],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Web Environment :: Mozilla",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Scientific/Engineering :: Information Analysis",
    ],
    entry_points="""
    [taarapi_app]
    app=taar.plugin:configure_plugin
    """,
    scripts=["bin/taar-redis.py"],
    zip_safe=False,
)
