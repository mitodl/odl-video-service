""" techtv2ovs command """
import os
from bonobo.contrib.django import ETLCommand

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
            '--collection',
            dest='collection',
            help='Process only this collection id',
            type=int
        )

        parser.add_argument(
            '--aws',
            dest='aws',
            action='store_true',
            help='Copy files from S3'
        )

    def handle(self, *args, **options):
        """
        Run the command
        """

        importer = TechTVImporter(
            db_user=options['user'],
            db_pw=os.getenv('MYSQL_PASSWORD', default=''),
            db_name=options['db'],
            db_host=options['host'],
            collection=options['collection'],
            protected=options['protected'],
            aws=options['aws'],
            output=self.stdout
        )
        importer.run()
