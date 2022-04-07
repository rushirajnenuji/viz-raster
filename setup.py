from setuptools import setup

with open('README.md', 'r') as fh:
    long_description = fh.read()

setup(
    name='pdgraster',
    version='0.1.0',
    description='Rasterization to GeoTiff and web-based tiles for the PDG '
                'Visualization pipeline',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/PermafrostDiscoveryGateway/viz-raster',
    packages=['pdgraster'],
    install_requires=[
        'numpy==1.22.2',
        'geopandas==0.10.2',
        'coloraide==0.10.0',
        'Pillow==9.0.1',
        'morecantile==3.1.0',
        'Rtree==0.9.7',
        'rasterio==1.2.10',
        'pdgstaging @ git+https://github.com/PermafrostDiscoveryGateway/viz-staging.git@develop#egg=pdgstaging'
    ],
    python_requires='>=3.9'
)
