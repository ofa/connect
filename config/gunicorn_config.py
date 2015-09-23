"""Gunicorn Configuration"""
# pylint: disable=invalid-name

def pre_fork(server, worker):
    """Functionality to run before forking workers"""
    f = '/tmp/app-initialized'
    open(f, 'w').close()

bind = 'unix:///tmp/nginx.socket'
