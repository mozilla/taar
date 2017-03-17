from setuptools import find_packages, setup

setup(
    name='mozilla-taar',
    use_scm_version=True,
    setup_requires=['setuptools_scm'],
    include_package_data = True,
    packages=find_packages(exclude=['tests', 'tests/*']),
    description='Telemetry-Aware Addon Recommender',
    author='Mozilla Foundation',
    author_email='fx-data-dev@mozilla.org',
    url='https://github.com/mdoglio/taar',
    license='MPL 2.0',
    install_requires=[
        'numpy',
        'requests',
        'thriftpy',
        'six',
        'ply'
    ],
    dependency_links=['https://github.com/wbolster/happybase/archive/33b7700375ba59f1810c30c8cd531577b0718498.zip#egg=happybase-1.0.1'],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment :: Mozilla',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Scientific/Engineering :: Information Analysis'
    ],
    zip_safe=False,
)
