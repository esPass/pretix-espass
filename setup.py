from setuptools import setup, find_packages


setup(
    name='pretix-espass',
    version='0.0.0',
    description='esPass support for pretix',
    long_description='Provides support for the esPass ticket format',
    url='https://github.com/espass/pretix-espass',
    author='ligi',
    author_email='ligi@ligi.de',

    install_requires=[],
    packages=find_packages(exclude=['tests', 'tests.*']),
    include_package_data=True,
    entry_points="""
[pretix.plugin]
espass=pretix_espass:PretixPluginMeta
""",
)
