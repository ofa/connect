#!/usr/bin/env python
from livereload import Server, shell
server = Server()
server.watch('*.rst', shell('make html', cwd='.'))
server.watch('*/*.rst', shell('make html', cwd='.'))
server.watch('*/*/*.rst', shell('make html', cwd='.'))
server.serve(root='_build/html', host='0.0.0.0')