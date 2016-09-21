from setuptools import setup

setup(name='oanda_fx_api',
      version=0.1,
      description='a wrapper for the Oanda FX trading API',
      url='https://github.com/abberger1/fx_stoch_event_algo',
      author='Andrew Berger',
      packages=['oanda_fx_api'],
      install_requires=[x for x in open('requirements.txt', 'r')],
      zip_safe=False)
