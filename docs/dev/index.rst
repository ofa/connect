****************************
Developer and Operator Guide
****************************

Connect is written in Python using the `Django`_ library.

Running Connect
===============

Out-of-the-box Connect is built to run as a Heroku_ app, with static files and uploaded content stored on `Amazon S3`_. As such, out of the box you'll need accounts on both services.


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
