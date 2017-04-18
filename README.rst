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

* AWS key and secret
* X.509 certificates for Moira_
* `Touchstone integration`_

You will then need to install the Python dependencies specified in the
``requirements.txt`` file, and run the project:

.. code-block:: bash

    pip install -r requirements.txt
    python manage.py runserver


.. _Office of Digital Learning: http://odl.mit.edu/
.. _Touchstone: https://ist.mit.edu/touchstone
.. _Touchstone integration: https://github.com/singingwolfboy/touchstone-notes
.. _Moira: http://kb.mit.edu/confluence/display/istcontrib/Moira+Overview
