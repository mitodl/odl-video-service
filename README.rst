ODL Video Service
=================

|build-status| |coverage-status|

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

You'll also need to set three S3 bucket for storing video files, and a CloudFront
distribution that is hooked up to that S3 bucket. The files in the S3 bucket
should *not* be publicly accessible, and the CloudFront distribution should
be set up to serve private content. `(See the CloudFront documentation for
more information.)
<http://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/PrivateContent.html>`_
Set the S3 upload bucket name as the ``VIDEO_S3_BUCKET`` environment variable, the
transcode bucket name as the ``VIDEO_S3_TRANSCODE_BUCKET``` environment variable, the
thumbnail bucket name as the ``VIDEO_S3_THUMBNAIL_BUCKET``` environment variable, and
set the CloudFront distribution ID as the ``VIDEO_CLOUDFRONT_DIST`` environment
variable, using the ``.env`` file.

The Buckets should each have a CORS configuration that will allow for cross-origin requests,
for example:

You also must have a proper Elastic Transcoder pipeline configured to use the specified 3 bucket names.

...code-block: xml

    <?xml version="1.0" encoding="UTF-8"?>
    <CORSConfiguration xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
    <CORSRule>
        <AllowedOrigin>video.odl.mit.edu</AllowedOrigin>
        <AllowedMethod>GET</AllowedMethod>
        <AllowedMethod>PUT</AllowedMethod>
        <AllowedMethod>POST</AllowedMethod>
        <AllowedMethod>DELETE</AllowedMethod>
        <AllowedMethod>HEAD</AllowedMethod>
        <MaxAgeSeconds>3000</MaxAgeSeconds>
        <AllowedHeader>*</AllowedHeader>
    </CORSRule>
    </CORSConfiguration>

The Cloudfront distribution's behaviors should also forward and whitelist the 'Origin' headers.

You can also optionally create a public CloudFront distribution for
serving static files for the web application. If you want to do this, set the
CloudFront distribution ID as the ``STATIC_CLOUDFRONT_DIST`` environment
variable, using the ``.env`` file.

This app expects the transcoding to use HLS, and the ```PRESET_IDS``` environment variable
should be a comma-delimited list of Video HLS presets for AWS ElasticTranscode.  The defaults
are standard presets (2M, 1M, 600K).

Dropbox
~~~~~~~

`Create an app on Dropbox <https://www.dropbox.com/developers/apps/create>`_,
and store the app key and app secret in the file
``secrets/dropbox-credentials.ini``, like this:

.. code-block:: ini

    [default]
    dropbox_app_key=foo
    dropbox_app_secret=bar

MIT Web Services
~~~~~~~~~~~~~~~~

You'll need an X.509 certificate and private key to access MIT web services,
including the Moira_ web API. Follow `MIT's instructions for how to get an
X.509 certificate <https://wikis.mit.edu/confluence/display/devtools/How+to+acquire+and+verify+a+x509+Application+Certificate>`_.
Store the certificate in the file
``secrets/mit-ws-cert.crt``, and the private key in the file
``secrets/mit-ws-key.pem``.

Touchstone
~~~~~~~~~~

Touchstone hasn't been configured yet, but here are some instructions for
`Touchstone integration`_.

Running
-------
To run the application, install Docker and `Docker Compose`_, then run:

.. code-block:: bash

    docker-compose up


Tests
-----
To run the tests, install the development dependencies and then run the test suite,
like this:

.. code-block:: bash

    ./scripts/test/test_suite.sh

.. _Office of Digital Learning: http://odl.mit.edu/
.. _Touchstone: https://ist.mit.edu/touchstone
.. _Touchstone integration: https://github.com/singingwolfboy/touchstone-notes
.. _Moira: http://kb.mit.edu/confluence/display/istcontrib/Moira+Overview
.. _Docker Compose: https://docs.docker.com/compose/

.. |build-status| image:: https://travis-ci.org/mitodl/odl-video-service.svg?branch=master&style=flat
   :target: https://travis-ci.org/mitodl/odl-video-service
   :alt: Build status
.. |coverage-status| image:: http://codecov.io/github/mitodl/odl-video-service/coverage.svg?branch=master
   :target: http://codecov.io/github/mitodl/odl-video-service?branch=master
   :alt: Test coverage
