***************************
Deploying Connect to Heroku
***************************

The easiest way to test out Connect is to deploy it via `Heroku`_ backed by `Amazon S3`_ for storage and (if possible) `Amazon Simple Email Service`_ (SES) for outgoing email.

.. _Heroku: https://heroku.com
.. _Amazon S3: https://aws.amazon.com/s3/
.. _Amazon Simple Email Service: https://aws.amazon.com/ses/


Prerequisites
=============

There are 4 things you need to start with:

1) A verified Heroku Account, with the Heroku Toolbelt installed locally
2) An Amazon Web Services Key/Secret
3) A S3 Bucket the above Key/Secret has access to. This will store static assets and uploads.
4) A Simple Email Service verified address you're willing to use for outgoing Connect email

Heroku
------

This tutorial assumes that you have a `verified Heroku account <https://devcenter.heroku.com/articles/account-verification>`_ with an attached credit card and the `Heroku Toolbelt`_ installed locally on your machine and available to you via command line.

.. _Heroku Toolbelt: https://toolbelt.heroku.com/

Amazon
------

It also assumes that you have an Amazon Web Service Key and Secret, which has full access to S3 and (if you want to use it) the SES email address or domain you wish to send email from.

Static Asset & Upload Storage
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Connect uses Amazon S3 by default to store both static assets and uploaded files. You'll need a S3 bucket which Connect can use to store these assets. You can define the specific folder you want any one installation of Connect to store its files in, but this tutorial will put uploaded files in the ``connectdemo/uploads`` folder and static assets in the ``connectdemo/staticfiles`` folder.

In order for fonts to correctly work on Connect, you'll need to enable Cross-Origin Resource Sharing on the bucket you'll be storing static assets on. More details on how to do this can be found at :doc:`/dev/deploying/fonts_on_s3`


Outgoing Email via Simple Email Service
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you want to use SES, the same Key/Secret you use for Amazon will need to have outgoing email rights on SES and the email address you want notifications to be sent from needs to be a `verified outgoing email address <https://docs.aws.amazon.com/ses/latest/DeveloperGuide/verify-email-addresses.html>`_ or part of a `verified domain <https://docs.aws.amazon.com/ses/latest/DeveloperGuide/verify-email-addresses.html>`_.

More details about setting up outgoing email can be found at :doc:`/dev/deploying/email`.


Deploying Connect to Heroku
===========================

The initial deployment of Connect involves these steps:

1) Clone the Connect repo
2) Create a Heroku App
3) Add Add-ons for the Heroku App
4) Configure Core Connect Settings
5) Configure S3 Static & Upload Storage
6) Deploy Connect to Heroku
7) Setup the Connect Database
8) Deploy Static Assets
9) Scale up Connect


Clone the Connect repo
----------------------

.. code-block:: bash

    # Clone the Connect Repository
    git clone https://github.com/ofa/connect.git

    # Switch to the new local Connect folder
    cd connect

Create the Heroku App
---------------------

.. code-block:: bash

    # Replace 'public-connect' in all these commands with the app name you want
    heroku apps:create public-connect

    # Use the Heroku Multi-Buildpack
    heroku buildpacks:set https://github.com/heroku/heroku-buildpack-multi

Add Add-ons for the Heroku App
------------------------------

.. code-block:: bash

    # Add the Heroku PostgreSQL Add-ons
    # The free version works for small deployments.
    heroku addons:create heroku-postgresql:hobby-dev

    # Add the CloudAMQP RabbitMQ Add-on
    # Odds are you'll want to upgrade this at some point in the next 15 days.
    # Connect uses some AMQP resources while idle which will go past the free plan.
    # But this demo assumes you want to pay $0
    heroku addons:create cloudamqp:lemur

    # Add the MemCachier Memcached Add-on
    # Connect doesn't use much caching, but check the Add-ons for other limitations
    heroku addons:create memcachier:dev

    # Add the New Relic monitoring Add-on
    # If you have an existing Newrelic account, skip this and add your account key as the
    # `NEW_RELIC_LICENSE_KEY` environment variable and set a `NEW_RELIC_APP_NAME` variable
    heroku addons:create newrelic:wayne


Configure Core Connect Settings
-------------------------------

.. code-block:: bash

    # A secret key used by django
    heroku config:set SECRET_KEY=random_string_here

    # A secret key used just for email
    heroku config:set EMAIL_SECRET_KEY=random_string

    # A list of hosts you're allowing Connect to live at.
    # `*` would allow ALL hostnames, but it's highly recommended you use a list such as
    # 'public-connect.herokuapp.com,connect.mydomain.com'
    heroku config:set ALLOWED_HOSTS=public-connect.herokuapp.com

    # The hostname of the app, no protocol
    heroku config:set HOSTNAME=public-connect.herokuapp.com

    # The full URL of the app, with protocol.
    # This will be used in outgoing emails that need an absolute URL
    heroku config:set ORIGIN=https://public-connect.herokuapp.com


Configure S3 Static & Upload Storage
------------------------------------

.. code-block:: bash

    # Access key, will need S3 and (if you want to use it) SES access
    heroku config:set AWS_ACCESS_KEY_ID=your_aws_access_key

    # Secret key to go with the above access key
    heroku config:set AWS_SECRET_ACCESS_KEY=your_aws_secret_key

    # Bucket you want Connect to use for static files and uploads
    heroku config:set AWS_STORAGE_BUCKET_NAME=storage_bucket_to_use_here

    # Folder in the S3 bucket to store uploads (change this to fit your needs)
    heroku config:set DEFAULT_S3_PATH=publicconnect/uploads

    # Folder in the S3 bucket to store static files
    heroku config:set STATIC_S3_PATH=publicconnect/staticfiles

    # Boolean to tell Connect to rely on S3
    heroku config:set USE_S3=True


Deploy Connect to Heroku
------------------------

.. code-block:: bash

    # Push code & compile your new heroku app.
    # This could take a bit, and you may have to try multiple times.
    git push heroku master


Setup the Connect Database
---------------------------

.. code-block:: bash

    # Install the database
    heroku run python manage.py migrate


Deploy Static Assets
--------------------

.. code-block:: bash

    # Download, compile, and deploy static assets to S3.
    # This could take a bit.
    heroku run 'bower install --config.interactive=false;grunt prep;python manage.py collectstatic --noinput'

.. note::
    Make sure your S3 bucket has a CORS policy, otherwise fonts will be broken. See: :doc:`/dev/deploying/fonts_on_s3`


Scale up Connect
----------------

.. code-block:: bash

    # Scale up the scheduler.
    # You'll soon need to make the scheduler a 2x dyno, but this demo is free
    heroku ps:scale web=1 scheduler=1

.. note::
    There are 3 apps defined in the heroku ``Procfile``: ``web``, ``scheduler`` and ``worker``.

    You need at least 1 ``web`` dyno, which accepts incoming HTTP requests, and at least 1 worker. Your first worker must be a ``scheduler`` dyno (which is a `Celery <http://www.celeryproject.org/>`_ worker which starts `periodic tasks <http://docs.celeryproject.org/en/latest/userguide/periodic-tasks.html>`_.) If your task queue is too large, you'll want to create additional ``worker`` dynos, which are the same as ``scheduler`` except they will not create new scheduled tasks.

.. warning::
    Never create more than 1 ``scheduler`` dyno. If you need extra task-processing capacity, create new workers. In order to properly launch the Connect python process all worker/scheduler dynos must have at least 1GB of RAM (known as 2X dynos)


Working with a Deployed Connect
===============================

When you visit your ``https://appname.herokuapp.com`` (or whatever domain you assigned Connect to) you'll have the opportunity to login via NGPVAN's ActionID. Do this, and remember the email address you used.

In order to promote your first user to a superadmin, run

.. code-block:: bash

    heroku run python manage.py promote_superuser yourname@yourdomain.com

From here on out you'll want to follow the :doc:`/user/admin/index`


Setting up Amazon's Simple Email Service
========================================

Having an outgoing email service is not required. By default Connect will discard all outgoing emails.

If you'd like to setup Amazon's Simple Email Service, change these configuration settings:

.. code-block:: bash

    # Actual from address to be used. Must be whitelisted in SES
    heroku config:set DEFAULT_FROM_ADDRESS=myconnectemail@mydomain.com

    # The `To: ` field in outgoing emails, must be SES whitelisted
    heroku config:set DEFAULT_FROM_EMAIL="My Connect <myconnectemail@mydomain.com>"

    # Use the "seacucumber" backend for outgoing email, which uses the task queue
    heroku config:set EMAIL_BACKEND=seacucumber.backend.SESBackend

More detail can be found at :doc:`/dev/deploying/email`
