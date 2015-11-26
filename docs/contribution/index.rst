***********************
Contributing to Connect
***********************

Connect is an open-source project released under the :doc:`MIT license <../license>` and pull requests and issues can be filed on the `Connect Github Repository`_.

Contribute Front-End Code
=========================


1) Install the needed dependencies by running, from the root directory:

`npm i`
`bower i`

Dev dependencies for Connect are managed by NPM, and front-end dependencies are managed by bower. These dependencies are required before compilation.

2) Review Connect's client-side code: The files are found in the top level folder `assets.` Javascript, JS templates, and LESS files are located here.

3) Compile the assets: From the root directory, run the command `grunt` -- this will pre-compile the Hogan templates, compile the LESS, minify the javascript, autoprefix the compiled CSS files, and copy the webfonts to the correct directory.

As a default, the Gruntfile is pointed at the default tasks configurations, location in `/open_connect/connect_core/`. Each task has its own file in a folder called `grunt`, and global variables for use in the tasks are defined in `grunt_config.json`.

As you make edits default client side assets, you can compile to see the changes.

**NOTE: This process is only for making open source constributions. Changing the default assets is not the recommended way of customizing/skinning Connect, as your changes would be overwritten as you upgrade versions. To customize Connect's styles, see instructions below.**

A `watch` task is provided in case you would like files to compile while you work.


Contribution Logistics & CLA
============================

Before code can be accepted by Organizing for Action for inclusion in our projects, contributors must sign OFA's Contributor License Agreement.

Individuals should sign the `Individual Contributor License Agreement`_ and if your work was done as part of your employment you will need to submit the `Entity Contributor License Agreement`_.

There is also an `OFA Contributor License FAQ`_ which provides further details about contributing code. Further questions can be sent to `cla@barackobama.com <mailto:cla@barackobama.com>`_.


.. _Individual Contributor License Agreement: https://ofa.github.io/cla-individual.html
.. _Entity Contributor License Agreement: https://ofa.github.io/cla-entity.html
.. _OFA Contributor License FAQ: https://ofa.github.io/cla-faq.html
.. _Connect Github Repository: https://github.com/ofa/connect
