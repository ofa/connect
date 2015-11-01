"""Sphinx docstring"""
# pylint: disable=invalid-name
from os.path import abspath, dirname
import sys

from django.conf import settings


# Insert our copy of the app into the path to all sphinx autodoc
sys.path.insert(1, dirname(dirname(abspath(__file__))))

# Configure the django settings to allow us to use autodoc
settings.configure()


extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.todo',
    'sphinx.ext.coverage',
    'sphinx.ext.mathjax',
    'sphinx.ext.ifconfig',
    'sphinx.ext.viewcode',
]
templates_path = ['_templates']
source_suffix = '.rst'
master_doc = 'index'
project = u'Connect'
html_show_copyright = False
exclude_patterns = ['_build']
pygments_style = 'sphinx'
html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
htmlhelp_basename = 'Connectdoc'
latex_documents = [
    ('index', 'Connect.tex', u'Connect Documentation',
     u'Organizing for Action', 'manual'),
]
man_pages = [
    ('index', 'connect', u'Connect Documentation',
     [u'Organizing for Action'], 1)
]
intersphinx_mapping = {'http://docs.python.org/': None}
