# -*- coding: utf-8 -*-
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.intersphinx',
              'sphinx.ext.todo', 'sphinx.ext.viewcode']
templates_path = ['_templates']
source_suffix = '.rst'
master_doc = 'index'
project = u'Connect'
copyright = u'2015, Organizing for Action'
exclude_patterns = ['_build']
pygments_style = 'sphinx'
html_theme = 'sphinx_rtd_theme'
html_static_path = []
htmlhelp_basename = 'Connectdoc'
latex_documents = [
  ('index', 'Connect.tex', u'Connect Documentation',
   u'Matías Aguirre', 'manual'),
]
man_pages = [
    ('index', 'connect', u'Connect Documentation',
     [u'Organizing for Action'], 1)
]
intersphinx_mapping = {'http://docs.python.org/': None}
