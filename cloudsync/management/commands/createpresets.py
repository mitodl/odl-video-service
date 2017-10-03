"""
Script for creating OVS presets from a JSON file
"""

import os
import json

import boto3
from django.conf import settings
from django.core.management import BaseCommand

script_path = os.path.dirname(os.path.realpath(__file__))


class Command(BaseCommand):
    """
    Create video transcoding presets for OVS
    """

    def add_arguments(self, parser):
        """ Named (optional) arguments """
        parser.add_argument(
            '--json',
            dest='filejson',
            default=os.path.join(script_path, '../../../config/et_presets.json'),
            help='Path to file containing presets in JSON format',
        )

    def handle(self, *args, **options):
        """
        Run the command
        """
        with open(options['filejson']) as filejson:
            presets = json.load(filejson)

        client = boto3.client('elastictranscoder',
                              region_name=settings.AWS_REGION,
                              aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                              aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)
        for preset in presets:
            preset['created'] = client.create_preset(**preset)
        self.stdout.write('ET_PRESET_IDS={}'.format(','.join(
            [preset['created']['Preset']['Id'] for preset in presets])))
