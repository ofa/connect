**************************************
Developing Connect with Docker Compose
**************************************

The quickest way to get Connect running locally is by using `Docker Compose`_. A ``docker-compose.yml`` file suitable for **development** is included in the repository.

Each time you want to re-build connect and test things out, run ``docker-compose build`` then ``docker-compose up``.



.. warning::
    The default ``docker-compose.yml`` file has the ``DEBUG`` variable set to ``True`` and both the Secret and Email Key baked-in. Keeping these defaults espo As such, **do not deploy Connect to production with the settings defined in the default docker-compose.yml file**

.. _Docker Compose: https://docs.docker.com/compose/
