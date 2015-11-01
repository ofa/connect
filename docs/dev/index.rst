****************************
Developer and Operator Guide
****************************

Connect is written in Python using the `Django`_ library.

Deploying Connect
=================

Out-of-the-box Connect is built to run as a Heroku_ app, with static files and uploaded content stored on `Amazon S3`_. As such, out of the box you'll need accounts on both services.

Guides
------

.. toctree::
    :maxdepth: 1

    /dev/deploying/quickstart

Individual Topics
-----------------

.. toctree::
    :maxdepth: 1

    /dev/deploying/email
    /dev/deploying/environment

Configuration of the runtime version of Connect is done primarially via environment variables.

.. _Django: https://www.djangoproject.com/
.. _Heroku: http://heroku.com/
.. _Amazon S3: https://aws.amazon.com/s3/
