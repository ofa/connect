================
Connect Settings
================

.. contents::
    :local:
    :depth: 1



Required
========

Without these settings set you will not be able to start Connect



SECRET_KEY
----------

**No Default Provided**

From the Django Documentation:

A secret key for a particular Django installation. This is used to provide
`cryptographic signing <https://docs.djangoproject.com/en/1.8/topics/signing/>`_, and should be set to a unique, unpredictable value.

Connect will refuse to start if ``SECRET_KEY`` is not set.



EMAIL_SECRET_KEY
----------------

**No Default Provided**

Similar to ``SECRET_KEY`` the Email Secret Key is a secret key that is used in cryptographic functions that involve outgoing emails.

As Connect usually requires users to be logged in to perform actions such as modify their subscription statuses we can usually verify that a specific user has permission to change these settings by comparing their login state.

In order to prevent spam complaints we do not require users to log in to unsubscribe if they are unsubscribing via a link in an email. In order to prevent a malicious third party from bulk unsubscribing users, we generate a hash based on the email address and ``EMAIL_SECRET_KEY`` to confirm that the user visiting the unsubscribe URL is in fact authorized to unsubscribe that user, even if they are not logged in.

This is different from ``SECRET_KEY`` since you may wish to keep your ``SECRET_KEY`` unique and secure on staging and production and require developers to have their own local ``SECRET_KEY``, but you may also want to have a shared ``EMAIL_SECRET_KEY`` among developers and staging systems.

It's usually wise to have both be unique.



DATABASE_URL
------------

**No Default Provided**

Connect is optimized to work with PostgreSQL as the database backend on top of Heroku, with the database being provided by Heroku's Postgres service. As a backup for local development where PostgreSQL is not available, it is possible to use ``SQLite``, although support for all features is not guaranteed.

In order to provide database service Heroku sets an environment variable called ``DATABASE_URL``.

But that doesn't mean that there isn't flexibility built in for users who may want to use alternative database engines.


For local development using `Postgres.app <http://postgresapp.com/>`_ we usually use ``DATABASE_URL=pgsql://@localhost/connect``


Here is the URL structure from the dj-database-url package readme (note that only PostgreSQL and SQLite work out of the box, and SQLite is not recommended for production):

+-------------+--------------------------------------------+--------------------------------------------------+
| Engine      | Django Backend                             | URL                                              |
+=============+============================================+==================================================+
| PostgreSQL  | ``django.db.backends.postgresql_psycopg2`` | ``postgres://USER:PASSWORD@HOST:PORT/NAME`` [1]_ |
+-------------+--------------------------------------------+--------------------------------------------------+
| PostGIS     | ``django.contrib.gis.db.backends.postgis`` | ``postgis://USER:PASSWORD@HOST:PORT/NAME``       |
+-------------+--------------------------------------------+--------------------------------------------------+
| MySQL       | ``django.db.backends.mysql``               | ``mysql://USER:PASSWORD@HOST:PORT/NAME``         |
+-------------+--------------------------------------------+--------------------------------------------------+
| MySQL (GIS) | ``django.contrib.gis.db.backends.mysql``   | ``mysqlgis://USER:PASSWORD@HOST:PORT/NAME``      |
+-------------+--------------------------------------------+--------------------------------------------------+
| SQLite      | ``django.db.backends.sqlite3``             | ``sqlite:///PATH`` [2]_                          |
+-------------+--------------------------------------------+--------------------------------------------------+

.. [1] With PostgreSQL, you can also use unix domain socket paths with
       `percent encoding <http://www.postgresql.org/docs/9.2/interactive/libpq-connect.html#AEN38162>`_:
       ``postgres://%2Fvar%2Flib%2Fpostgresql/dbname``.
.. [2] SQLite connects to file based databases. The same URL format is used, omitting
       the hostname, and using the "file" portion as the filename of the database.
       This has the effect of four slashes being present for an absolute file path:
       ``sqlite:////full/path/to/your/database/file.sqlite``.


.. warning::
    Connect is tested against and run in production with PostgreSQL. SQLite has been confirmed to work in the past, although its usage is discouraged. Past issues with MySQL have included problems with out-of-the-box emoji support. Pull requests which improve MySQL support would be highly appreciated.



CACHE_URL
---------

**No Default Provided**

Connect is heavily reliant on a cache, and there is an inherent danger in choosing a default that may end up in production. As such, we require that you explicitly set a ``CACHE_URL`` in your environment.

+-------------+---------------------------------------------------------+--------------------------------------------+
| Engine      | Django Backend                                          | URL                                        |
+=============+=========================================================+============================================+
| Local Memory| ``django.core.cache.backends.locmem.LocMemCache``       | ``locmemcache://[NAME]``                   |
+-------------+---------------------------------------------------------+--------------------------------------------+
| Dummy       | ``django.core.cache.backends.dummy.DummyCache``         | ``dummycache://``                          |
+-------------+---------------------------------------------------------+--------------------------------------------+
| Database    | ``django.core.cache.backends.db.DatabaseCache``         | ``dbcache://USER:PASSWORD@HOST:PORT/NAME`` |
+-------------+---------------------------------------------------------+--------------------------------------------+
| File        | ``django.core.cache.backends.filebased.FileBasedCache`` | ``filecache:///PATH/TO/FILE``              |
+-------------+---------------------------------------------------------+--------------------------------------------+
| memcached   | ``django.core.cache.backends.memcached.MemcachedCache`` | ``memcached://HOST:PORT``                  |
+-------------+---------------------------------------------------------+--------------------------------------------+
| pymemcached | ``django.core.cache.backends.memcached.PyLibMCCache``   | ``pymemcached://HOST:PORT``                |
+-------------+---------------------------------------------------------+--------------------------------------------+
| redis       | ``django_redis.cache.RedisCache``                       | ``redis://[USER:PASSWORD@]HOST:PORT[/DB]`` |
+-------------+---------------------------------------------------------+--------------------------------------------+


.. note::
    Heroku provides multiple memcached add-ons which provide cache support using their own custom environment variables. By default the Heroku version of Connect will install `django-heroku-memcacheify <https://github.com/rdegges/django-heroku-memcacheify>`_, which will allow you to use your choice of `MemCachier <https://addons.heroku.com/memcachier>`_ or `Memcached Cloud <https://addons.heroku.com/memcachedcloud>`_ out of the box.

.. warning::
    When testing Connect we recommend you use the ``dummycache://`` setting to avoid cross-test cache contamination.
    Running ``CACHE_URL=dummycache:// python manage.py test`` for your testing is the best way to guarantee tests are being run correctly.



ALLOWED_HOSTS
-------------

Default: ``['']`` (Empty list)

While not required while ``DEBUG=True``, to run Connect in production you'll need your ``ALLOWED_HOSTS`` setting to be set.

From the Django Documentation:

A list of strings representing the host/domain names that this Django site can
serve. This is a security measure to prevent an attacker from poisoning caches
and triggering password reset emails with links to malicious hosts by submitting
requests with a fake HTTP ``Host`` header, which is possible even under many
seemingly-safe web server configurations.

Values in this list can be fully qualified names (e.g. ``'www.example.com'``),
in which case they will be matched against the request's ``Host`` header
exactly (case-insensitive, not including port). A value beginning with a period
can be used as a subdomain wildcard: ``'.example.com'`` will match
``example.com``, ``www.example.com``, and any other subdomain of
``example.com``. A value of ``'*'`` will match anything; in this case you are
responsible to provide your own validation of the ``Host`` header.

Django also allows the `fully qualified domain name (FQDN)`_ of any entries.
Some browsers include a trailing dot in the ``Host`` header which Django
strips when performing host validation.

.. _`fully qualified domain name (FQDN)`: https://en.wikipedia.org/wiki/Fully_qualified_domain_name

When ``DEBUG`` is ``True`` or when running tests, host validation is
disabled; any host will be accepted. Thus it's usually only necessary to set it
in production.



Application
===========

These are some variables that are necessary to the functionality and display of Connect, specifically in templates and emails where minimization of changes in any fork is important.



BRAND_TITLE
-----------

Default: ``Connect`` (String)

The title you're using for your version of Connect. This is used throughout the Connect codebase.



ORGANIZATION
------------

Default: ``Owner`` (String)

The name of the organization or person running this copy of Connect. This will be attached to all outgoing emails as well as included in a few copyright sections.



HOSTNAME
--------

Default: ``localhost:8000`` (String)

The hostname that this version of Connect is running on, without the protocol. If connect is running at ``https://public.ofaconnect.com/`` then the hostname would be ``public.ofaconnect.com``



ORIGIN
------

Default: ``http://localhost:8000`` (String)

The full URL that this version of Connect is running at, with the protocol. This is used when absolute URLs are needed (such as in notification emails.) If Connect is running at ``https://public.ofaconnect.com/`` this would be ``https://public.ofaconnect.com``



DEFAULT_FROM_ADDRESS
--------------------

Default: ``no-reply@connect.local`` (String)

The "From" address will be used when outgoing emails are compiled by Connect.

**You must have this address whitelisted to be sent from with your Email Service Provider**

This is the raw email address, with no names attached.



DEFAULT_FROM_EMAIL
------------------

Default: ``Connect <no-reply@connect.local>`` (String)

The friendly "From" address that will be used on outgoing emails sent from Connect. This is what will appear in your end user's email client as the sender of notifications.

**You must have this address whitelisted to be sent from with your Email Service Provider**



SYSTEM_USER_NAME
----------------

Default: ``Connect`` (String)

Connect has a ``System User`` which is the user account that Connect uses internally for notifications and other actions that need to be performed on the end-user level.



SYSTEM_USER_EMAIL
-----------------

Default: ``connect@connect.local`` (String)

It's possible to override the email address of the system user.

**This is not important for the functioning of Connect and once set this can never be changed. So it's wise to just leave the default.**

.. warning::
    If you do decide to change this, and it is recommended you do not, realize that you'll immediately have to change the email address of the system user in your database to reflect the new setting.



GOOGLE_ANALYTICS_PROPERTY_ID
----------------------------

Default: ``UA-0-0`` (String)

The `Google Analytics`_ property ID.

`Google Analytics support <https://support.google.com/analytics/answer/1032385?hl=en>`_ has details on how to find this code.


.. _Google Analytics: https://www.google.com/analytics/


GOOGLE_ANALYTICS_DEBUG_MODE
---------------------------

Default: ``False`` (Boolean)

A boolean specifying if Connect should set Google Analytics into `Debug Mode <https://developers.google.com/analytics/devguides/collection/analyticsjs/debugging>`_.

**This is likely only necessary to change if you're developing Google Analytics code**



CONNECT_APP
-----------

Default: **No Default**

The app that contains the assets and templates for the version of Connect you'll want to use.

If you're branding your own version of Connect you'll likely want to change this to ``private_connect`` (or whatever app name you choose)

If no custom ``CONNECT_APP`` is defined Connect will fall back to the open source assets and templates.



ICON_PREFIX
---------------------------

Default: ``glyphicon glyphicon-`` (String)

Connect offers you the ability to swap-out the standard `Glyphicon`_ library by specifying a prefix of both the class name for the iconset as well as the prefix for the icon itself.

.. _Glyphicon: http://glyphicons.com/



Base
====



DEBUG
-----

Default: ``False`` (boolean)

From the Django Documentation:

Never deploy a site into production with ``DEBUG`` turned on.

Did you catch that? NEVER deploy a site into production with ``DEBUG``
turned on.

One of the main features of debug mode is the display of detailed error pages.
If your app raises an exception when ``DEBUG`` is ``True``, Django will
display a detailed traceback, including a lot of metadata about your
environment, such as all the currently defined Django settings (from
``settings.py``).

As a security measure, Django will *not* include settings that might be
sensitive (or offensive), such as ``SECRET_KEY``. Specifically, it will
exclude any setting whose name includes any of the following:

* ``'API'``
* ``'KEY'``
* ``'PASS'``
* ``'SECRET'``
* ``'SIGNATURE'``
* ``'TOKEN'``

Note that these are *partial* matches. ``'PASS'`` will also match PASSWORD,
just as ``'TOKEN'`` will also match TOKENIZED and so on.

Still, note that there are always going to be sections of your debug output
that are inappropriate for public consumption. File paths, configuration
options and the like all give attackers extra information about your server.

It is also important to remember that when running with ``DEBUG``
turned on, Django will remember every SQL query it executes. This is useful
when you're debugging, but it'll rapidly consume memory on a production server.

Finally, if ``DEBUG`` is ``False``, you also need to properly set
the ``ALLOWED_HOSTS`` setting. Failing to do so will result in all
requests being returned as "Bad Request (400)".



TIME_ZONE
---------

Default: ``US/Eastern`` (String)

A string representing the time zone for this installation. It's recommended that you choose from one of the following:

* ``US/Eastern``
* ``US/Central``
* ``US/Mountain``
* ``US/Pacific``



LANGUAGE_CODE
-------------

Default: ``en-us`` (String)

A string representing the language code for this installation.

Currently Connect only supports the United States English language code (``en-us``) although if you want to adapt Connect into another language this would be a setting you'd want to change.



SESSION_COOKIE_NAME
-------------------

Default: ``messages_sessionid`` (String)

In order to avoid cookie collisions and overwrites with other applications hosted on the same domain, the session cookie name is customized on Connect. If you want to have multiple installations of Connect on the same domain where a user could be simultaneously logged into each version it's likely you'll need to change this setting.

.. note::
    It is possible to have multiple copies of Connect on the same domain using the same ``messages_sessionid`` cookie name. Just realize that your browser can only be logged into one copy of Connect per domain.



CSRF_COOKIE_NAME
----------------

Default: ``mesages_csrftoken`` (String)

The "CSRF Cookie" is a browser cookie created by Connect that prevents third parties from using javascript to perform actions as users. This type of attack, known as a `Cross-site request forgery <https://en.wikipedia.org/wiki/Cross-site_request_forgery>`_, is a large concern for Connect.

You can change the name of the cookie here. This may be important if you have multiple installations of Connect on the same domain and want to allow users to be simultaneously logged into both, although this is not recommended.

.. warning:: The Connect frontend assumes that the CSRF cookie is called ``messages_csrftoken``, so changing this setting may involve finding all the references to ``messages_csrftoken`` in Connect's frontend code to maintain HTTP POST functionality.



SESSION_ENGINE
--------------

Default: ``django.contrib.sessions.backends.cached_db`` (String)

From the Django documentation:

Controls where Django stores session data. Included engines are:

* ``'django.contrib.sessions.backends.db'``
* ``'django.contrib.sessions.backends.file'``
* ``'django.contrib.sessions.backends.cache'``
* ``'django.contrib.sessions.backends.cached_db'``
* ``'django.contrib.sessions.backends.signed_cookies'``



SESSION_SERIALIZER
------------------

Default: ``django.contrib.sessions.serializers.PickleSerializer`` (String)

Full import path of a serializer class to use for serializing session data.
Included serializers are:

* ``'django.contrib.sessions.serializers.PickleSerializer'``
* ``'django.contrib.sessions.serializers.JSONSerializer'``

.. note::
    While not optimal, we use ``PickleSerializer`` for Connect to handle some edge cases that have cropepd up in the past using the ``JSONSerializer``.



SESSION_EXPIRE_AT_BROWSER_CLOSE
-------------------------------

Default: ``False`` (String)

Whether to expire the session when the user closes their browser.

.. note::
    There is significant advantage to setting this to ``True`` when using authentication backends which will "Trust" Connect and immediately authenticate users coming from Connect if the user is logged into the authentication provider.
    That way if the user logs out of their account with the authentication provider they're also logged out of Connect.



SESSION_COOKIE_SECURE
---------------------

Default: ``False`` (String)

Whether to use a secure cookie for the session cookie. If this is set to
``True``, the cookie will be marked as "secure," which means browsers may
ensure that the cookie is only sent under an HTTPS connection.

**It's highly recommended you set this to ``True`` in production**



SECURE_PROXY_SSL_HEADER
-----------------------

Default: ``'HTTP_X_FORWARDED_PROTO', 'https'`` (Tuple)

A tuple representing a HTTP header/value combination that signifies a request
is secure. This controls the behavior of the request object's ``is_secure()``
method.

.. warning::
    This is included by default to match the header Heroku sends to signify if a request is secure or not. Heroku will not allow an end-user to spoof the ``HTTP_X_FORWARDED_PROTO`` header. If you're deploying Connect on a different platform make sure it is not possible for an end user to spoof the ``HTTP_X_FORWARDED_PROTO`` header, otherwise set this to ``None`` or a different non-spoof-able header.


From the Django Documentation:

This takes some explanation. By default, ``is_secure()`` is able to determine
whether a request is secure by looking at whether the requested URL uses
"https://". This is important for Django's CSRF protection, and may be used
by your own code or third-party apps.

If your Django app is behind a proxy, though, the proxy may be "swallowing" the
fact that a request is HTTPS, using a non-HTTPS connection between the proxy
and Django. In this case, ``is_secure()`` would always return ``False`` -- even
for requests that were made via HTTPS by the end user.

In this situation, you'll want to configure your proxy to set a custom HTTP
header that tells Django whether the request came in via HTTPS, and you'll want
to set ``SECURE_PROXY_SSL_HEADER`` so that Django knows what header to look
for.

You'll need to set a tuple with two elements -- the name of the header to look
for and the required value. For example::

    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

Here, we're telling Django that we trust the ``X-Forwarded-Proto`` header
that comes from our proxy, and any time its value is ``'https'``, then the
request is guaranteed to be secure (i.e., it originally came in via HTTPS).
Obviously, you should *only* set this setting if you control your proxy or
have some other guarantee that it sets/strips this header appropriately.

Note that the header needs to be in the format as used by ``request.META`` --
all caps and likely starting with ``HTTP_``. (Remember, Django automatically
adds ``'HTTP_'`` to the start of x-header names before making the header
available in ``request.META``.)


KEY_PREFIX
----------

Default: (Empty string)

A string that will be automatically included (prepended by default) to
all cache keys used by the Django server.

.. note::
    This would be useful to modify if you want to share one memcached cluster across multiple installations of Connect.


Email Settings
==============

The ability for Connect to send outgoing email is vital. It's highly recommended you read :doc:`/dev/deploying/email` before attempting to configure outgoing email in production.



USE_SES
-------

Default: ``False`` (Boolean)

A boolean specifying if Connect should use Amazon's `Simple Email Service`_.

.. _Simple Email Service: https://aws.amazon.com/ses/



EMAIL_BACKEND
-------------

Default: ``django.core.mail.backends.dummy.EmailBackend`` (String)

The outgoing email backend that Connect should use.

If using the SMTP backend, this will need to be set to ``django.core.mail.backends.smtp.EmailBackend``.

If you're using SES you'll likely want to use `Sea Cucumber`_, a Django email backend library that will use Celery_ to queue and rate-limit outgoing Simple Email Service requests, and thus set this to ``seacucumber.backend.SESBackend``.

.. _Sea Cucumber: https://pypi.python.org/pypi/seacucumber/
.. _Celery: http://www.celeryproject.org/


EMAIL_HOST
----------

Default: ``localhost`` (String)

**For the SMTP backend only**

The host to use for sending email via SMTP.



EMAIL_HOST_PASSWORD
-------------------

Default: (Empty string)

**For the SMTP backend only**

Password to use for the SMTP server defined in ``EMAIL_HOST``. This
setting is used in conjunction with ``EMAIL_HOST_USER`` when
authenticating to the SMTP server. If either of these settings is empty,
Django won't attempt authentication.



EMAIL_HOST_USER
---------------

Default: (Empty string)

**For the SMTP backend only**

Username to use for the SMTP server defined in ``EMAIL_HOST``.
If empty, Django won't attempt authentication.



EMAIL_PORT
----------

Default: ``25`` (Integer)

**For the SMTP backend only**

Port to use for the SMTP server defined in ``EMAIL_HOST``.



EMAIL_USE_TLS
-------------

Default: ``False`` (Boolean)

**For the SMTP backend only**

Whether to use a TLS (secure) connection when talking to the SMTP server.
This is used for explicit TLS connections, generally on port 587. If you are
experiencing hanging connections, see the implicit TLS setting
``EMAIL_USE_SSL``.



EMAIL_USE_SSL
-------------

Default: ``False`` (Boolean)

**For the SMTP backend only**

Whether to use an implicit TLS (secure) connection when talking to the SMTP
server. In most email documentation this type of TLS connection is referred
to as SSL. It is generally used on port 465. If you are experiencing problems,
see the explicit TLS setting ``EMAIL_USE_TLS``.

Note that ``EMAIL_USE_TLS``/``EMAIL_USE_SSL`` are mutually
exclusive, so only set one of those settings to ``True``.



EMAIL_SSL_CERTFILE
------------------

Default: ``None`` (String)

**For the SMTP backend only**

If ``EMAIL_USE_SSL`` or ``EMAIL_USE_TLS`` is ``True``, you can
optionally specify the path to a PEM-formatted certificate chain file to use
for the SSL connection.



EMAIL_SSL_KEYFILE
-----------------

Default: ``None`` (String)

**For the SMTP backend only**

If ``EMAIL_USE_SSL`` or ``EMAIL_USE_TLS`` is ``True``, you can
optionally specify the path to a PEM-formatted private key file to use for the
SSL connection.

Note that setting ``EMAIL_SSL_CERTFILE`` and ``EMAIL_SSL_KEYFILE``
doesn't result in any certificate checking. They're passed to the underlying SSL
connection. Please refer to the documentation of Python's
:func:`python:ssl.wrap_socket` function for details on how the certificate chain
file and private key file are handled.



EMAIL_TIMEOUT
-------------

Default: ``None`` (Integer)

**For the SMTP backend only**

Specifies a timeout in seconds for blocking operations like the connection
attempt.



CUCUMBER_RATE_LIMIT
-------------------

**For the Sea Cucumber backend only**

Default: ``1`` (Integer)

The number of emails per second that will be sent from Connect via Sea Cucumber.

If you are a new SES user, your default quota will be 1,000 emails per 24 hour period at a maximum rate of one email per second. You can use the command ``python manage.py ses_usage`` to get your quota.



BOUNCY_AUTO_SUBSCRIBE
---------------------

Default: ``False`` (Boolean)

Used by the `Django Bouncy`_ library.

All Amazon `Simple Notification Service`_ (SNS) endpoints must verify with Amazon that they're willing to accept incoming messages. Setting ``BOUNCY_AUTO_SUBSCRIBE`` to ``True`` will tell Connect to verify with Amazon any incoming SNS subscription requests.

In order to avoid malicious third parties with Amazon Web Services accounts from sending unsubscribe requests to your version of Connect, this is turned off by default.


BOUNCY_TOPIC_ARN
----------------

Default: ``None`` (List)

Used by the `Django Bouncy`_ library.

All Simple Notification Service queues are assigned a unique `Amazon Resource Name`_ (ARN). Connect allows you to specify a list of valid ARNs that should be allowed to unsubscribe users.

Considering ``BOUNCY_AUTO_SUBSCRIBE`` is set to ``False`` Connect should never subscribe to a malicious third party's notification queue in the first place, but for added assurance it may make sense to add your ARN to this setting.


.. _Simple Notification Service: https://aws.amazon.com/sns/
.. _Django Bouncy: https://github.com/ofa/django-bouncy
.. _Amazon Resource Name: https://docs.aws.amazon.com/general/latest/gr/aws-arns-and-namespaces.html


Authentication
==============

Connect relies heavily on `Python Social Auth`_ for authentication.

.. _Python Social Auth: http://psa.matiasaguirre.net/


DEFAULT_AUTH_BACKEND
--------------------

Default: ``social.backends.ngpvan.ActionIDOpenID`` (String)

Also available: ``connect_extras.auth_backends.bsdtools.BSDToolsOAuth2``

You can find out more information about different authentication backends available at :doc:`/dev/deploying/authentication_backends`


POST_LOGOUT_PAGE
----------------

Default: ``/`` (String)


If ``DEFAULT_AUTH_BACKEND`` is ``social.backends.ngpvan.ActionIDOpenID`` this defaults to ``https://accounts.ngpvan.com/Account/LogOut``

If ``DEFAULT_AUTH_BACKEND`` is ``connect_extras.auth_backends.bsdtools.BSDToolsOAuth2`` this defaults to ``https://{BSDTOOLS_INSTANCE}/page/user/logout``



SOCIAL_AUTH_NEW_USER_REDIRECT_URL
---------------------------------

Default: ``/explore/`` (String)



LOGIN_REDIRECT_URL
------------------

Default: ``/messages/`` (String)



LOGIN_ERROR_URL
---------------

Default: ``/`` (String)



SOCIAL_AUTH_PROTECTED_FIELDS
----------------------------

Default: ``username,`` (List)



USE_SOCIAL_AUTH_AS_ADMIN_LOGIN
------------------------------

Default: ``True`` (Boolean)



OPTIONAL: BSDTOOLS_INSTANCE
---------------------------

Default: (Empty string)



OPTIONAL: BSDTOOLS_KEY
----------------------

Default: (Empty string)



OPTIONAL: BSDTOOLS_SECRET
-------------------------

Default: (Empty string)



Celery/Task Queue
=================

Connect relies on Celery_ as a distributed task queue and scheduler.

Connect specifically uses tasks when actions a) do not need to be completed immediately, b) are especially intensive or lengthy, or c) to be run automatically on a schedule.

While there is no expectation that tasks will be performed instantly, users will notice if tasks are substantially backed up and as such you should ensure that you have enough workers assigned to promptly handle new tasks.

.. _Celery: http://www.celeryproject.org/


BROKER_URL
----------

Default: ``django://`` (String)

Also allowed: ``CLOUDAMQP_URL``

Connect is mostly broker-agnostic, but the default implementation uses RabbitMQ_.

The expected format of the ``BROKER_URL`` for different backends can be found in the `Celery Broker Documentation`_.

In order support the `CloudAMQP Heroku Addon`_ if ``BROKER_URL`` is not present and ``CLOUDAMQP_URL`` is, Connect will use ``CLOUDAMQP_URL`` as the broker URL.

.. _RabbitMQ: https://www.rabbitmq.com/
.. _Celery Broker Documentation: http://docs.celeryproject.org/en/latest/getting-started/brokers/
.. _CloudAMQP Heroku Addon: https://elements.heroku.com/addons/cloudamqp



BROKER_POOL_LIMIT
-----------------

Default: ``1`` (Integer)



BROKER_HEARTBEAT
----------------

Default: ``30`` (Integer)



BROKER_CONNECTION_TIMEOUT
-------------------------

Default: ``30`` (Integer)



CELERY_EVENT_QUEUE_EXPIRES
--------------------------

Default: ``60`` (Integer)



CELERY_ALWAYS_EAGER
-------------------

Default: ``True`` (Boolean)



CELERY_TIMEZONE
---------------

Default: ``UTC`` (String)



CELERY_SEND_EVENTS
------------------

Default: ``False`` (Boolean)



CELERY_RESULT_BACKEND
---------------------

Default: ``None`` (String)



ALSO: CLOUDAMQP_URL
-------------------

Default: (Empty string)



Storage
=======

By default Connect relies on `Amazon S3`_ for storage functionality.

.. _Amazon S3: https://aws.amazon.com/s3/

AWS_ACCESS_KEY_ID
-----------------

Default: (Empty string)

An Amazon Web Services access key id. This is also used by the Sea Cucumber library for outgoing email via Simple Email Service should you enable that functionality.


AWS_SECRET_ACCESS_KEY
---------------------

Default: (Empty string)

The associated secret key associated with the ``AWS_ACCESS_KEY_ID``


USE_S3
------

Default: ``False`` (Boolean)

A boolean set to ``True`` if Connect is to store content on Amazon S3.


AWS_STORAGE_BUCKET_NAME
-----------------------

Default: (Empty string)

The name of a storage bucket that the ``AWS_ACCESS_KEY_ID`` has full access to and can upload both static assets and media for Connect.


DEFAULT_S3_PATH
---------------

Default: ``connect/uploads`` (String)

The default path in the S3 bucket for uploads to be uploaded to.

.. warning::
    If you want to use the same S3 bucket for multiple Connect installations, such as a staging and production installation, you should make ``DEFAULT_S3_PATH`` and ``STATIC_S3_PATH`` unique.


STATIC_S3_PATH
--------------

Default: ``connect/static`` (String)

The default path in the S3 bucket for static files to be uploaded to.


Logging
=======


LOG_LEVEL
---------

Default: ``WARNING`` (String)

