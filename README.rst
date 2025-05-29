ODL Video Service
=================

|build-status| |coverage-status|

This is a video hosting platform, designed for MIT's
`Office of Digital Learning`_ (ODL). It is tightly integrated with MIT's
Touchstone_ authentication system and Moira_ permission system.

Installation
------------

You will need to obtain several different pieces of information
in order to get this project up and running. Secret and non-secret settings
will be stored in environment variables. In order to make it easier to get
started, you can copy ``.env.example`` to ``.env``.

Django
~~~~~~
Create a secret key for Django, and store it in the ``.env`` file as SECRET_KEY.
You can run this code to create a key:

.. code-block:: bash

    head -c 50 /dev/urandom | base64

AWS
~~~

You'll need an AWS access key ID and secret access key. Store them in the file
``.env``, like this:

.. code-block:: ini

    AWS_ACCESS_KEY_ID=foo
    AWS_SECRET_ACCESS_KEY=bar

You'll also need a CloudFront private key for generating signed URLs for
CloudFront. Store the private key file in ``.env`` in one single string
(careful with the newlines), like this:

.. code-block:: ini

    CLOUDFRONT_PRIVATE_KEY==----BEGIN RSA PRIVATE KEY-----\nMIICXAIBAAKBgQCQMjkVo9gogtb8DI2bZyFGvnnN81Q4d0crS4S9UDrxHJU/yrKg\n...

Set the key ID as the ``CLOUDFRONT_KEY_ID`` environment variable, using the
``.env`` file.

You'll also need to set three S3 bucket for storing video files, and a CloudFront
distribution that is hooked up to that S3 bucket. The files in the S3 bucket
should *not* be publicly accessible, and the CloudFront distribution should
be set up to serve private content. `(See the CloudFront documentation for
more information.)
<http://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/PrivateContent.html>`_
Set the S3 upload bucket name as the ``VIDEO_S3_BUCKET`` environment variable, the
transcode bucket name as the ``VIDEO_S3_TRANSCODE_BUCKET`` environment variable, the
thumbnail bucket name as the ``VIDEO_S3_THUMBNAIL_BUCKET`` environment variable, the
subtitle bucket name as the ``VIDEO_S3_SUBTITLE_BUCKET`` environment variable, and
set the CloudFront distribution ID as the ``VIDEO_CLOUDFRONT_DIST`` environment
variable, using the ``.env`` file.

The Buckets should each have a CORS configuration that will allow for cross-origin requests,
for example:

You also must have a proper Elastic Transcoder pipeline configured to use the specified 3 bucket names.

.. code-block:: xml

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

Each of the Cloudfront origins should be configured as follows:
  - Restrict Bucket Access
  - Origin Access Identity: Use an Existing Identity
  - Your Identities: select an existing CloudFront user (create if necessary)

You also need to create cloudfront behaviors for each bucket:
  - Allowed HTTP methods: `GET, HEAD, OPTIONS`
  - Whitelist Headers: `Access-Control-Request-Headers`,`Access-Control-Request-Method`, `Origin`
  - Restrict Viewer Access: No

  - `VIDEO_S3_TRANSCODE_BUCKET` bucket:
      - Precedence: 0
      - Path pattern: `transcoded/*`
  - `VIDEO_S3_SUBTITLE_BUCKET` bucket:
      - Precedence: 1
      - Path pattern: `subtitles/*`
  - `VIDEO_S3_THUMBNAIL_BUCKET`
      - Precedence 2:
      - Path pattern: `thumbnails/*`
  - `VIDEO_S3_BUCKET`
      - Precedence 3:
      - Path pattern: `Default(*)`


You can also optionally create a public CloudFront distribution for
serving static files for the web application. If you want to do this, set the
CloudFront distribution ID as the ``STATIC_CLOUDFRONT_DIST`` environment
variable, using the ``.env`` file.

This app expects the transcoding to use HLS or MP4, and the ``ET_HLS_PRESET_IDS`` and ``ET_MP4_PRESET_ID``environment variables, respectively.
``ET_HLS_PRESET_IDS`` should be a comma-delimited list of Video HLS presets for AWS ElasticTranscode.  The defaults
are standard presets (2M, 1M, 600K).

Dropbox
~~~~~~~

`Create an app on Dropbox <https://www.dropbox.com/developers/apps/create>`_,
and store the app key in the file
``.env``, like this:

.. code-block:: ini

    DROPBOX_KEY=foo

MIT Web Services
~~~~~~~~~~~~~~~~

You'll need an X.509 certificate and private key to access MIT web services,
including the Moira_ web API. Follow `MIT's instructions for how to get an
X.509 certificate <https://wikis.mit.edu/confluence/display/devtools/How+to+acquire+and+verify+a+x509+Application+Certificate>`_.
Store the certificate and the private key in the file ``.env``
in one line strings (careful with the newlines), like this:

.. code-block:: ini

    MIT_WS_CERTIFICATE=foo\nblah\n...
    MIT_WS_PRIVATE_KEY=bar\nblah\n...

Touchstone
~~~~~~~~~~

Touchstone hasn't been configured yet, but here are some instructions for
`Touchstone integration`_.


YouTube Integration
~~~~~~~~~~~~~~~~~~~

- Create a new project at https://console.cloud.google.com/apis/dashboard
  - Save the project ID in your ``.env`` file as ``YT_PROJECT_ID``
- Create an OAuth client ID for the project (type: ``Other``)
  - Save your client ID and client secret in your ``.env`` file (as ``YT_CLIENT_ID`` and ``YT_CLIENT_SECRET``)
- Enable the YouTube Data API v3 for your project
- Run the following Django command to generate values for ``YT_ACCESS_TOKEN`` and ``YT_REFRESH_TOKEN``:

.. code-block:: bash

    docker-compose run web python manage.py oauthtokens

- Click on the provided link, follow the prompts, and enter the verification code back in the shell.
- Save the ``YT_ACCESS_TOKEN`` and ``YT_REFRESH_TOKEN`` values to your ``.env`` file


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


Commits
-------
To ensure commits to github are safe, you should install the following first:
.. code-block:: bash
    pip install pre_commit detect-secrets
    pre-commit install

To automatically install precommit hooks when cloning a repo, you can run this:
.. code-block:: bash
    git config --global init.templateDir ~/.git-template
    pre-commit init-templatedir ~/.git-template
