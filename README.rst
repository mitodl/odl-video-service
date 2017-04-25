ODL Video Service
=================

This is a video hosting platform, designed for MIT's
`Office of Digital Learning`_ (ODL). It is tightly integrated with MIT's
Touchstone_ authentication system and Moira_ permission system.

This project is still under heavy development, and is not yet ready for
production.

Installation
------------

You will need to obtain several different pieces of information
in order to get this project up and running. Secrets will be stored in the
``secrets`` directory, which is not versioned with Git. Non-secret settings
will be stored in environment variables. In order to make it easier to get
started, you can copy ``.env.example`` to ``.env``.

Django
~~~~~~
Create a secret key for Django, and store it in the file
``secrets/django-secret-key``. You can run this code to do so:

.. code-block:: bash

    head -c 50 /dev/urandom > secrets/django-secret-key

AWS
~~~

You'll need an AWS access key ID and secret access key. Store them in the file
``secrets/aws-credentials.ini``, like this:

.. code-block:: ini

    [default]
    aws_access_key_id=foo
    aws_secret_access_key=bar

You'll also need a CloudFront private key, for generated signed URLs for
CloudFront. Store the private key file in ``secrets/cloudfront-key.pem``.
Set the key ID as the ``CLOUDFRONT_KEY_ID`` environment variable, using the
``.env`` file.

You'll also need to set an S3 bucket for storing video files, and a CloudFront
distribution that is hooked up to that S3 bucket. The files in the S3 bucket
should *not* be publicly accessible, and the CloudFront distribution should
be set up to serve private content. `(See the CloudFront documentation for
more information.)
<http://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/PrivateContent.html>`_
Set the S3 bucket name as the ``VIDEO_S3_BUCKET`` environment variable, and
set the CloudFront distribution ID as the ``VIDEO_CLOUDFRONT_DIST`` environment
variable, using the ``.env`` file.

You can also optionally create a public CloudFront distribution for
serving static files for the web application. If you want to do this, set the
CloudFront distribution ID as the ``STATIC_CLOUDFRONT_DIST`` environment
variable, using the ``.env`` file.

Dropbox
~~~~~~~

Sign up for an app key and app secret. Store them in the file
``secrets/dropbox-credentials.ini``, like this:

.. code-block:: ini

    [default]
    dropbox_app_key=foo
    dropbox_app_secret=bar

MIT Web Services
~~~~~~~~~~~~~~~~

You'll need an X.509 certificate and private key to access MIT web services,
including the Moira_ web API. Store the certificate in the file
``secrets/mit-ws-cert.crt``, and the private key in the file
``secrets/mit-ws-key.pem``.

Running
-------
To run the application, install Docker and `Docker Compose`_, then run:

.. code-block:: bash

    docker-compose up

.. _Office of Digital Learning: http://odl.mit.edu/
.. _Touchstone: https://ist.mit.edu/touchstone
.. _Touchstone integration: https://github.com/singingwolfboy/touchstone-notes
.. _Moira: http://kb.mit.edu/confluence/display/istcontrib/Moira+Overview
.. _Docker Compose: https://docs.docker.com/compose/
