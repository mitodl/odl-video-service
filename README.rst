ODL Video Service
=================

This is a video hosting platform, designed for MIT's
`Office of Digital Learning`_ (ODL). It is tightly integrated with MIT's
Touchstone_ authentication system and Moira_ permission system.

This project is still under heavy development, and is not yet ready for
production.

Installation
------------

You will need to obtain several different secrets in order to get this project
up and running:

* AWS access key and secret
* AWS keypair for signing CloudFront URLs
* Docker app key and secret
* X.509 certificates for Moira_
* `Touchstone integration`_

Copy the ``.env.example`` file to ``.env``, and put your secrets into this file.
For the ``AWS_PRIVATE_KEY_CONTENTS`` variable, you'll need to replace literal
newline characters with ``\n``, so that the entire contents of the file is on
one line.

Once you've got your ``.env`` file set up, you can use `Docker Compose`_
to run the project:

.. code-block:: bash

    docker-compose up

.. _Office of Digital Learning: http://odl.mit.edu/
.. _Touchstone: https://ist.mit.edu/touchstone
.. _Touchstone integration: https://github.com/singingwolfboy/touchstone-notes
.. _Moira: http://kb.mit.edu/confluence/display/istcontrib/Moira+Overview
.. _Docker Compose: https://docs.docker.com/compose/
