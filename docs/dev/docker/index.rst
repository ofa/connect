**************************************
Development and Deployment with Docker
**************************************

Connect ships with support for Docker_.

The ``Dockerfile`` will install all the required dependencies for the build, as well as a script called ``proclaunch``. As the Dockerfile does not have a ``CMD`` or ``ENTRYPOINT`` which launches all of Connect (nor does it have all the required settings pre-defined), to launch each process you'll need to run ``proclaunch web``, ``proclaunch scheduler``, and/or ``proclaunch worker`` to run the correct process.

By default there are not enough environment settings to fully launch Connect. You'll want to create a ``.env`` file to pass into docker which contains the settings in :doc:`/dev/settings`.

In order to have dev/production parity, you'll want to also launch docker containers for Memcached_ and RabbitMQ_ and set the ``BROKER_URL`` and ``CACHE_URL`` to link to those. ``docker-compose.yml`` contains example code for running web, scheduler and worker processes.

.. note::
    The first time you build the dockerfile (either via the standard docker build process or via ``docker-compose build``) your machine will have to pull in all the dependencies for both frontend and backend code. Subsequent builds will skip these steps. If you want to re-pull dependencies, the easiest step is to change ``requirements.txt`` for python packages, ``package.json`` for node packages, or ``bower.json`` for static dependencies. Docker will scan these files for changes during each build process, and if there is a change it will re-run that part of the build process.

.. warning::
    While ``docker-compose.yml`` is a good starting-point for knowing what settings should be defined, it's written for development.

.. _Docker: https://www.docker.com/
.. _Memcached: https://hub.docker.com/r/library/memcached/
.. _RabbitMQ: https://hub.docker.com/r/library/rabbitmq/
