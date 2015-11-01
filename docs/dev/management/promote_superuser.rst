*************************************
Management Command: promote_superuser
*************************************

You can assign an existing user to be "Staff" and have all permissions (be a superuser) by running the ``promote_superuser`` management command and provide the email address of the user you wish to promote to a staff member with all permissions.

.. code-block:: bash

    python manage.py promote_superuser email@email.com

If using Heroku, you'd go to your Connect directory and run

.. code-block:: bash

    heroku run python manage.py promote_superuser email@email.com -a connect-app-name