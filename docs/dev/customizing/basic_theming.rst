*************
Basic Theming
*************

Initial Theming
===============

The easiest way to give Connect a look-and-feel that matches your organization's brand while maintaining the ability to receive updates is to skin it as follows:

1) Install the needed dependencies by running, from the root directory:

.. code-block:: bash

    npm i
    bower i

Dev dependencies for Connect are managed by NPM, and front-end dependencies are managed by bower. These dependencies are required before compilation.

A top level folder called ``/private_connect/`` is provided as a template. You can rename this folder to anything you like, but we'll reference it with this name for the remainder of this documentation, so substitute your own folder name as needed.

This is where you will create your additional assets.

2) In your ``.env`` file, include the following: ``CONNECT_APP=private_connect``

3) In the folder ``/private_connect/assets/less``, you'll see a file called ``private_config.less`` -- open it in your favorite editor and make changes. If you've worked with Bootstrap, this should seem somewhat familiar. It's essentially a variables file-- change colors, point it to the correct images, and update as you like. You can also add overrides and additional style (either within this file, or imported from another file) as needed.

4) Compile the customized assets: from the root directory, run `grunt`.

What's happening in this step:

Grunt will use the ``CONNECT_APP`` assignment you set in the ``.env`` file to know where to look for its configuration. In this case, ``/private_connect/grunt_config.json``.

There are already some default tasks setup to compile your new customized Connect assets. The LESS task (``/private_connect/grunt/less.js``) uses ``/private_connect/assets/less/private_connect.less`` as its main file and compiles out to a CSS file in ``/private_connect/static/connect/css``.

Django also uses the ``CONNECT_APP`` assignment you set in the ``.env`` file to know where to look for static files, so it loads them into the app.

When you run the server and look at Connect, you should see it using your custom LESS changes instead of the default styles.


Multiple Theme Instructions
===========================

Through the use of environment variables and a special grunt command, it's possible to use the same central repository and have multiple themes of Connect.

You can pass a ``target`` option to grunt at the command line so you can switch easily between tasks for different versions of Connect, with different settings, compiling in different places.

Example:

``grunt --target="private-connect"``

You can also write your own grunt configurations for any of the other tasks, i.e. uglification, template precompilation with hogan, etc, or add new custom tasks. Anything you can do with a normal grunt file, you can do here. See `this article 
<http://www.thomasboyt.com/2013/09/01/maintainable-grunt.html>`_ for more about Grunt configurations that are loaded from separate files.
