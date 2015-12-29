****************************
Developer and Operator Guide
****************************

Connect is written in Python using the `Django`_ library.

Running Connect
===============

The easiest way to run Connect is by deploying it as a Heroku_ app with static files and uploaded content stored on `Amazon S3`_. However, support for Docker_ is also available, which is useful for doing custom deployments into existing environments as well as for local development.

Guides
------

.. toctree::
    :maxdepth: 1

    /dev/deploying/heroku_setup
    /dev/deploying/fonts_on_s3
    /dev/docker/index


Individual Topics
-----------------

.. toctree::
    :maxdepth: 1

    /dev/settings
    /dev/deploying/email
    /dev/deploying/authentication_backends
    /dev/management/promote_superuser



Developing Connect
==================


Local Development
-----------------

.. toctree::
    :maxdepth: 1

    /dev/developing/environment_setup
    /dev/docker/compose


Customization
-------------

.. toctree::
    :maxdepth: 1

    /dev/customizing/basic_theming


Project Layout
--------------

.. toctree::
    :maxdepth: 1

    /dev/developing/backend_layout
    /dev/developing/frontend_layout

Configuration of the runtime version of Connect is done primarially via environment variables.

.. _Django: https://www.djangoproject.com/
.. _Heroku: http://heroku.com/
.. _Amazon S3: https://aws.amazon.com/s3/
.. _Docker: https://www.docker.com/
