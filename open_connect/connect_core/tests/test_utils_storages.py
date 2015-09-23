"""Tests for the AttachmentStorage storage"""
from datetime import datetime
import re

from django.test import TestCase
from open_connect.connect_core.utils.storages import (
    AttachmentStorage, uniqify_filename
)


class TestAttachmentStorage(TestCase):
    """Test for the AttachmentStorage storage"""
    def test_uniqify_filename_uniqueness(self):
        """Test that uniqify_filename returns unique filenames"""
        # Confirm a list of 1000 uniquified filenames has 1000 unique results
        unique_filenames = [
            # pylint: disable=unused-variable
            uniqify_filename('hey.png') for x in range(0, 1000)
        ]
        self.assertEqual(len(set(unique_filenames)), 1000)

    def test_unique_filename_format(self):
        """Test that the format of the filename is correct"""
        # Confirm that the format of the filename is correct
        result = uniqify_filename('hey.png')
        self.assertTrue(
            re.search(
                r'^[0-9a-f]{32}\.png$',
                result
            )
        )

    def test_name_generator(self):
        """Test for the AttachmentStorage name generator

        Because boto will, by default, overwrite files that already exist on S3
        we must rename our files to something unique before uploading them.
        """
        # `directory/testfile.png` should return a result in the format of
        # `directory/130701.a1b2c.testfile.png`
        filename = "directory/testfile.png"

        storageinstance = AttachmentStorage()
        name_result = storageinstance.get_available_name(filename)

        self.assertFalse(name_result == filename)
        self.assertTrue(
            re.search(
                r'^directory/[1-4][0-9]{5}\.[0-9a-f]{32}\.png$',
                name_result
            )
        )
        self.assertIn("directory/", name_result)
        self.assertIn(datetime.now().strftime('%y%m%d'), name_result)
        self.assertTrue(len(name_result), 54)
        self.assertTrue(name_result.count("."), 2)
