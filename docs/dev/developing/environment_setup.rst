**********************************
Setting Up a Developer Environment
**********************************

Connect is an application with extensive compiled less/hogan/javascript front-end and interpreted Python/Django back-end components. While it's not necessary for a back-end developer to know how to build front-end tests, nor does a front-end developer need to know how to write Python code, it is vital that anyone working on Connect have the packages for both available locally.

Some parts of this documentation are based off the `DjangoCMS Documentation <http://docs.django-cms.org/en/develop/how_to/install.html>`_

.. note:: These instructions apply for development using OS X, although there shouldn't be much change needed to develop on Linux.


System Package Requirements
===========================

As a `12 Factor App`_ developers of Connect should strive for `Dev/prod parity`_, where the environment run locally is as close as possible to production.


Before starting, make sure you have `Homebrew`_ installed, so you can install the required libraries. The following instructions imply that you have ``brew`` installed

* `Node`_ - Command-line javascript system. ``brew install node``
* `PostgreSQL`_ - Database. ``brew install postgresql`` or via `Postgres.app`_ with the `command line tools <http://postgresapp.com/documentation/cli-tools.html>`_ configured. Postgres.app is more user-friendly, but both work.
* `Grunt`_ - Front-end task runner. ``sudo npm install -g grunt-cli``
* `Bower`_ - Front-end dependency management. ``sudo npm install -g bower``
* `libjpeg`_ - JPEG image support. ``brew install libjpeg``
* `pip`_ - Python dependency management. ``sudo easy_install pip``
* `virtualenv`_ or `virtualenvwrapper`_ - Python package isolation. It's recommended you install the more user-friendly virtualenvwrapper, which also installs virtualenv, but these instructions imply you're using the vanilla virtualenv. ``sudo pip install virtualenv``
* `GIT`_ - Code management. This may be installed already on your system, but to use the latest version of Git use ``brew install git``


Optional (but recommended) packages

* `libmemcached`_ Library for compiling memcached client. ``brew install libmemcached``
* `Memcached`_ - Caching framework. Note: Django offers alternative caches ``brew install memcached``
* `Gifsicle`_ - Animated GIF support. Gifsicle is required for GIFs to maintain animation after resize. It also allows some tests that are otherwise skipped to run. ``brew install gifscicle``
* `RabbitMQ`_ - Task Queue. Note: For convenience it's recommended you run Connect in development with ``CELERY_ALWAYS_EAGAR`` enabled (it is enabled by default when in ``DEBUG`` mode), disabling local task queues. It's also possible to use alternative task queues locally. ``brew install rabbitmq``


.. _12 Factor App: http://12factor.net/
.. _Dev/prod parity: http://12factor.net/dev-prod-parity

.. _Homebrew: http://brew.sh/

.. _Node: https://nodejs.org/en/
.. _PostgreSQL: http://www.postgresql.org/
.. _Postgres.app: http://postgresapp.com/
.. _Grunt: http://gruntjs.com/
.. _Bower: http://bower.io/
.. _libjpeg: http://libjpeg.sourceforge.net/
.. _pip: https://pip.readthedocs.org/en/stable/
.. _virtualenv: https://pypi.python.org/pypi/virtualenv
.. _virtualenvwrapper: https://virtualenvwrapper.readthedocs.org/en/latest/
.. _GIT: https://git-scm.com/

.. _libmemcached: http://
.. _Memcached: http://memcached.org/
.. _Gifsicle: https://www.lcdf.org/gifsicle/
.. _RabbitMQ: https://www.rabbitmq.com/


Forking Connect
===============

Connect requires users to fork their own version of the `Connect Github project`_ then use the official project as a remote that changes can be merged in from.

How to fork Connect and move the upstream changes into that fork is outside the scope of this documentation, but for simplicity's sake we can clone Connect from the official repository locally.

To clone the Connect project locally, set the official project as a remote called "open", and enter that folder run the following:

.. code-block:: bash

  git clone -o open https://github.com/ofa/connect.git
  cd connect


.. note::
    Be careful merging in upstream changes from the official Connect project into your local project, and always review code changes and commit messages manually before merging. While we strive for stability, Connect is under active development and some changes to the core project can break your local modifications.

.. _Connect Github project: https://github.com/ofa/connect


Back-end Configuration & Setup
==============================


Installing in a virtualenv using pip
------------------------------------

Installing inside a `virtualenv`_ is the preferred way to install any Django
installation. These instructions imply you're using the vanilla version of
virtualenv and not virtualenvwrapper_, which has more user-friendly shortcuts
when dealing with virtualenv, but is slightly more difficult to setup.

To create a new virtualenv

.. code-block:: bash

    virtualenv env

.. note:: If you are *not* using a system-wide install of Python (such as with Homebrew),
          omit the usage of ``sudo`` when installing via ``pip``.

Switch to the virtualenv at the command line by typing:

.. code-block:: bash

  source env/bin/activate


Connect relies on ``pip`` for python dependency management.

The python dependencies necessary for development of Connect are located in the ``dev-requirements.txt`` file [1]_.  To install all the packages necessary to run Connect, run:

.. code-block:: bash

    pip install -r dev-requirements.txt


.. warning::
    There are a few packages that are compiled during this step that require system packages above, specifically ``libjpeg`` for JPEG image handling and ``PostgreSQL`` for database handling. Make sure you've installed both before attempting to install postgres.


.. [1] There are multiple ``requirements.txt`` files in Connect, including an actual ``requirements.txt``, which has packages aimed specifically at Heroku and may not compile on OS X. Each of these files include ``common-requirements.txt``, which contains the core cross-platform packages necessary to run Connect on any platform. For development, use ``dev-requirements.txt``


Setting up a .env file
----------------------

Basic configuration of Connect is based around the 12 Factor `Environment-Based Configuration`_ philosophy. Instead of having to directly edit your environment, Connect's backend uses `Django-environ`_ and frontend uses `dotenv`_ to allow users to store the configuration in an ``.env`` file locally that is not tracked by version control. The ``.env`` file is a key/value file containing variables that will be loaded into the environment at startup.

The first step in setting up your developer environment is to clone the ``.env-dev-example`` file (which is tracked in version control) to be your local ``.env`` file (which will not be tracked by version control)

.. code-block:: bash

    cp .env-dev-example .env

You can then edit the ``.env`` file to reflect the settings you need locally. Available settings are available in the :doc:`/dev/settings` documentation.

.. _Environment-Based Configuration: http://12factor.net/config
.. _Django-environ: https://django-environ.readthedocs.org/en/latest/
.. _dotenv: https://github.com/motdotla/dotenv


Setting up a database
---------------------

This assumes that you have `Postgres.app`_ installed and have correctly installed the `command line tools <http://postgresapp.com/documentation/cli-tools.html>`_.

The ``.env`` file that ships with Connect assumes that you have a database called ``connect`` in your localhost database. To both create this database and have Connect insert all the preliminary code, run:

.. code-block:: bash

    createdb connect
    python manage.py migrate


Front-end Configuration & Setup
===============================

Loading front-end dependencies
------------------------------

Some files necessary for managing Connect are not contained in the repository itself, and instead must be brought in via the `Node Package Manager`_ and `Bower`_.

To load all front-end dependencies run:

.. code-block:: bash

    npm install
    bower install


.. _Node Package Manager: https://www.npmjs.com/


Compiling front-end files
-------------------------

Connect uses `Grunt`_ to compile static assets. A simple default task is already created to compile all the necessary static assets.

.. code-block:: bash

    grunt


.. note::
    Grunt is used elsewhere in Connect for front-end related tests. As long as you do not have a ``CONNECT_APP`` loaded in your ``.env`` file, you can run tasks like ``grunt jasmine`` and have the app-wide tests run. If you do have a ``CONNECT_APP`` defined in your ``.env`` you can run those same tasks by settings a ``--target "open_connect/connect_core"`` flag to your grunt tasks. For jasmine tests that would be ``grunt --target "open_connect/connect_core" jasmine``


.. _Jasmine: https://jasmine.github.io/


Setting up your version of Connect
==================================

Running Connect locally
-----------------------

Once you have your static files built, you'll be able to launch your version of Connect using Django's built-in development server.

While inside your local virtualenv, run


.. code-block:: bash

    python manage.py runserver


You should now be able to visit ``http://127.0.0.1:8000/`` and see a fully functioning version of Connect using the open source theming.


Promote a user to be a superuser
--------------------------------

Connect uses NGPVAN_'s `ActionID`_ single-sign-on system for authentication via `Python Social Auth`_.

When you first go to your development server you'll be given 2 buttons, one to Login and one to Create a New Account. Click on either and follow the login or registration flow presented by ActionID. **Remember the email address you use.** After you're done with that you'll be redirected back to Connect with a new account.

In order to upgrade your account to be a super-user, you'll need to use the :doc:`promote_superuser </dev/management/promote_superuser>` Django management command and include the email address you used to sign-up for ActionID with.

.. code-block:: bash

    python manage.py promote_superuser youremail@here.com


Your account should now be properly promoted to a superuser. From here on out you can manage your local version of Connect by following the :doc:`/user/admin/index`.


.. _NGPVAN: https://www.ngpvan.com
.. _ActionID: http://developers.ngpvan.com/action-id
.. _Python Social Auth: http://psa.matiasaguirre.net/
