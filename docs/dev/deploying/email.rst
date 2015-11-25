****************************
Outgoing Email Configuration
****************************

Connect is heavily reliant on outgoing email notifications. Incoming email replies are not supported yet. Making sure those emails are sent by Connect (and reliably received by the end-user) means it's necessary to link Connect to a 3rd party transactional email service provider.

Email Service Provider
----------------------

The recommended outgoing email service provider for Connect is Amazon's `Simple Email Service`_ (or SES.)

Connect comes pre-installed with the `Sea Cucumber`_ library, which will put all outgoing messages into Connect's task queue, allowing your Heroku workers to stagger their outgoing email to match the send speed limits spelled out on Amazon S3.

To use the Sea Cucumber library, make sure your ``AWS_ACCESS_KEY_ID`` and ``AWS_SECRET_ACCESS_KEY`` settings are correct and have the correct SES permissions and then set the ``EMAIL_BACKEND`` environment variable to ``seacucumber.backend.SESBackend``


.. warning::

    Connect does not support incoming email. Users who reply to emails from Connect such as new message digests and notifications will receive the (quite ugly) "Your email could not be delivered" reply by default.

    It's recommended you use an outgoing address like `no-reply@yourdomain\.com` and have that address reply with a friendly "Your email was not received, please visit Connect to comment."


Handling Bounces
----------------

Connect has a built-in 'Unsubscribe' feature. Each outgoing message checks the ``open_connect.mailer.models.Unsubscribe`` table for a record that matches the outgoing email address. If a record is found, the outgoing message is discarded.

Installed by default is OFA's in-house-built `Django Bouncy`_ application, which will allow you to send bounces and spam complaints from SES directly into Connect via Amazon's `Simple Notification Service`_ (or SNS.) Hard bounces and complaints are configured to create ``Unsubscribe`` objects in Connect, which will result in the app being denied.

More details about configuring Django Bouncy can be found in the `Django Bouncy Readme <https://pypi.python.org/pypi/django-bouncy>`_. In order to prevent nefarious third parties from bulk un-subscribing connect members, by default ``BOUNCY_AUTO_SUBSCRIBE`` is set to ``False`` and ``BOUNCY_TOPIC_ARN`` is empty. Both of these can be overridden by setting their relevant environment variables.

The path Django Bouncy is installed at on Connect is ``https://connect.yourdomain.local/mail/bouncy/``.

.. note::

    It's important that the Django Bouncy path is included in the ``LOGIN_EXEMPT_URLS`` list in the ``connect.settings.authentication_settings`` settings file. Otherwise Connect will attempt to forward Amazon SNS to your login provider. By default ``mail/*`` is in that list.


.. _Simple Email Service: https://aws.amazon.com/ses/
.. _Sea Cucumber: https://github.com/duointeractive/sea-cucumber/
.. _Django Bouncy: https://github.com/ofa/django-bouncy
.. _Simple Notification Service: https://aws.amazon.com/sns/
