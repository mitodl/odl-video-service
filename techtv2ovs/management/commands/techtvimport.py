""" techtv2ovs command """
import os
from bonobo.contrib.django import ETLCommand
from django.core.management import CommandError

from techtv2ovs.utils import TechTVImporter


class Command(ETLCommand):
    """
    Django command for importing TechTV collections and videos via Bonobo ETL Graph
    """

    def add_arguments(self, parser):
        """
        Arguments for MySQL connection parameters
        """
        parser.add_argument(
            '--host',
            dest='host',
            help='MySQL host',
            type=str
        )
        parser.add_argument(
            '--db',
            dest='db',
            help='MySQL database',
            type=str
        )
        parser.add_argument(
            '--user',
            dest='user',
            help='MySQL user',
            type=str
        )

        parser.add_argument(
            '--protected',
            dest='protected',
            help='filter by protected status (value 0 or 1)',
            default=1,
            choices=[0, 1],
            type=int
        )

        parser.add_argument(
            '--collections',
            dest='collections',
            help='Process only these collection ids',
            type=int,
            nargs='+'
        )

        parser.add_argument(
            '--noyoutube',
            dest='noyoutube',
            help='list of public collections that should not be uploaded to YouTube',
            type=int,
            nargs='+',
            default=[]
        )

        parser.add_argument(
            '--cloudfront',
            dest='cloudfront',
            help='list of public collections that should be streamable from both Cloudfront and Youtube',
            type=int,
            nargs='+',
            default=[]
        )

        parser.add_argument(
            '--aws',
            dest='aws',
            action='store_true',
            help='Copy files from S3'
        )

        parser.add_argument(
            '--videos',
            dest='videos',
            help='Process only these video ids',
            type=int,
            nargs='+'
        )

    def handle(self, *args, **options):
        """
        Run the command
        """
        for env in ('DROPBOX_FOLDER', 'DROPBOX_TOKEN'):
            if os.getenv(env) is None:
                raise CommandError('`{}` environment variable must be set'.format(env))
        importer = TechTVImporter(
            db_user=options['user'],
            db_pw=os.getenv('MYSQL_PASSWORD', default=''),
            db_name=options['db'],
            db_host=options['host'],
            collections=options['collections'],
            protected=options['protected'],
            aws=options['aws'],
            output=self.stdout,
            cloudfront=options['cloudfront'],
            noyoutube=options['noyoutube']
        )
        importer.run()
