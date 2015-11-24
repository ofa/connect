****************
Quickstart Guide
****************

Launching your first demo version of Connect is relatively straightforward, as long as you don't mind the standard theme and are willing to use `Heroku`_.

While this guide will not result in a version of Connect capable of handling considerable lap, it's enough to get a sense of the admin functionality.



Prerequisites: Accounts
-----------------------

Connect relies heavily on 2 services: `Heroku`_ and `Amazon Web Services`_, and to get started you'll need accounts on both.

On Amazon Web Services in particular, you'll at the very minimum need a working account for their `Simple Storage Service`_ (or S3), and to use the outgoing email notification functionality of Connect you'll need an account with Amazon's `Simple Email Service`_ (or SES.)

If you don't have accounts on those two services, you'll need to set those accounts up before continuing. 

While you'll be required to enter your credit card when setting these services up, by default Connect will not require enough resources to use more than the "Free Tier" for either Amazon S3 nor Simple Email Service, and a base demo version of Connect can run 24/7 on Heroku for as low as $14.

.. note:: While Connect can be run on Heroku's "Free" plan, Connect has a "scheduler" that the "worker" process keeps running 24/7. For $7 per process (or "Dyno" in Heroku speak) per month you can have your "web" process and "scheduler" process run 24/7. This is usage-based, so if you only run Connect for a few days you'll only be charged for a portion of the overall cost.

.. warning:: While Connect can be run for $14/month, a production installation of Connect on Heroku with all the necessary extra services starts at $350/month (as of Oct 27, 2015) and can go higher depending on load. A Heroku support package which includes 24/7 response time is available for $1000/month on top of your base cost. For a very high volume Connect installation this package is recommended, although it can be split among multiple applications on Heroku (and even multiple installations of Connect.)


Step 1: Setting up Amazon S3
----------------------------

"Static Assets" (or the base images, icons, styles and fonts used by Connect) as well as uploaded assets (such as profile images, group images, resources, etc) are stored on Amazon's S3 service.

You'll need at least one S3 "`bucket <https://docs.aws.amazon.com/AmazonS3/latest/dev/UsingBucket.html>`_". This can be called anything, but it's recommended that the bucket be contained in Amazon's `US-Standard <https://docs.aws.amazon.com/general/latest/gr/rande.html#s3_region>`_ region. This is the default region for Amazon.

Connect uses "Web fonts" for icons. Because of this, you'll need to log into your `AWS Management Console <https://console.aws.amazon.com>`_ and enable `Cross Origin Resource Sharing <https://docs.aws.amazon.com/AmazonS3/latest/dev/cors.html>`_ (commonly known as CORS.) The management console makes it quite easy to enable CORS on a bucket, and if you get stuck here feel free to move on. You'll notice a few missing icons.

Once you have this "bucket" setup, you're ready to deploy to Heroku.

Step 2: Deploy to Heroku
------------------------

Connect is available as a one-click app installation on Heroku. Once you have your Heroku account and Amazon S3 bucket setup, click below to deploy the latest version of Connect:

.. image:: https://www.herokucdn.com/deploy/button.svg
    :target: https://heroku.com/deploy?template=https://github.com/ofa/connect

Keep track of the "Admin Key" that you generate. You'll need this in step 3.

Step 3: Login to Connect & setup an admin account
-------------------------------------------------

Once your version of Connect is ready, you'll be able to create an account and login. Go to https://your-app-name.herokuapp.com/welcome/new-admin/ right away. You'll first be directed to the default authentication provider used by Connect (currently NGPVAN's `ActionID <http://developers.ngpvan.com/action-id>`_), asked to accept the terms of Connect, and theirafter be asked for the "Admin Key" you setup in the above set.

The "Admin Key" is a secret key that is used exclusively to elevate accounts to elevate accounts to staff-level permissions if no other admin account exists. **After you've esclated one account, it's recommended you remove the "Admin Key" from your configuration.**

.. warning:: You only have one bite at the apple when creating your first staff account via the /new-admin/ endpoint. If you lose access to your first staff account you'll need to esclate a new account via the Heroku command line. See :doc:`/dev/management/promote_superuser` for more info about the ``promote_superuser`` management command.

Step 4: Setup Outgoing Email
----------------------------

Connect relies heavily on outgoing email for notifications. There are multiple ways of setting up outgoing email that involve varying levels of complexity.

You can find more information at this documentation page: :doc:`email`


.. _Heroku: https://www.heroku.com
.. _Amazon Web Services: https://aws.amazon.com
.. _Simple Email Service: https://aws.amazon.com/ses/
.. _Simple Storage Service: https://aws.amazon.com/s3/
