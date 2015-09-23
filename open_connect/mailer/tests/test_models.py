"""Model tests for the mailer app"""
# pylint: disable=protected-access, maybe-no-member
import hashlib

from django.test import TestCase
from django.test.utils import override_settings
from mock import patch
from model_mommy import mommy as maker

from open_connect.mailer import models


class TestCacheNameGenerator(TestCase):
    """Test functions inside models.py"""
    def test_cache_name_generator(self):
        """Test the key name generator for our unsubscribe cache"""
        name = models._cache_name('bo@example.com')
        hexaddress = hashlib.md5('bo@example.com').hexdigest()
        self.assertIn('unsub-', name)
        self.assertIn(hexaddress, name)


class TestUnsubscribeManager(TestCase):
    """Tests for the Unsubscribe model manager"""
    def setUp(self):
        """Test the UnsubscribeManager"""
        cache_patcher = patch('open_connect.mailer.models.cache')
        self.mockcache = cache_patcher.start()
        self.addCleanup(cache_patcher.stop)

    def test_cache_copy_exists(self):
        """Test that when a cached copy exists"""
        self.mockcache.get.return_value = True
        self.assertTrue(
            models.Unsubscribe.objects.address_exists('awesome@example.com'))

    def test_cache_copy_is_false(self):
        """Test when an address has been previously checked"""
        self.mockcache.get.return_value = False
        self.assertFalse(
            models.Unsubscribe.objects.address_exists('awesome@example.com'))

    def test_entry_exists_not_in_cache(self):
        """Test when an unsubscribe entry exists but is not in a cache"""
        self.mockcache.get.return_value = None
        unsub = maker.make(models.Unsubscribe, address='nocache@example.com')
        self.assertTrue(
            models.Unsubscribe.objects.address_exists('nocache@example.com'))
        self.mockcache.set.assert_called_with(
            models._cache_name('nocache@example.com'), unsub)

    def test_entry_does_not_exist(self):
        """Test when an address does not have an entry"""
        self.mockcache.get.return_value = None
        self.assertFalse(
            models.Unsubscribe.objects.address_exists('nothere@example.com'))
        self.mockcache.set.assert_called_with(
            models._cache_name('nothere@example.com'), False)

    def test_multiple_unsubscribe_records(self):
        """Test where someone has unsubscribed multiple times"""
        self.mockcache.get.return_value = None
        self.assertFalse(
            models.Unsubscribe.objects.address_exists('nope@example.com'))
        first_unsub = maker.make(
            models.Unsubscribe, address='nope@example.com')
        maker.make(models.Unsubscribe, address='nope@example.com')
        self.assertEqual(models.Unsubscribe.objects.filter(
            address='nope@example.com').count(), 2)
        self.assertTrue(models.Unsubscribe.objects.address_exists(
            'nope@example.com'))
        self.mockcache.set.assert_called_with(
            models._cache_name('nope@example.com'), first_unsub)


class TestUnsubscribeModel(TestCase):
    """Tests for the Unsubscribe model"""
    def setUp(self):
        """Test the Unsubscribe Model"""
        cache_patcher = patch('open_connect.mailer.models.cache')
        self.mockcache = cache_patcher.start()
        self.addCleanup(cache_patcher.stop)

    def test_unicode(self):
        """Test the unicode method on the Unsubscribe model"""
        unsub = maker.make(models.Unsubscribe, address='cool@example.com')
        self.assertEqual(str(unsub), 'Unsubscribe cool@example.com')

    def test_save_sets_cache(self):
        """Test that save() sets the cache"""
        unsub = maker.make(models.Unsubscribe, address='test@example.com')
        self.mockcache.set.assert_called_with(
            models._cache_name('test@example.com'), unsub)

    def test_delete_removes_cache(self):
        """Test that delete() removes the record from the cache"""
        unsub = maker.make(models.Unsubscribe, address='test2@example.com')
        self.mockcache.set.assert_called_with(
            models._cache_name('test2@example.com'), unsub)
        unsub.delete()
        self.mockcache.delete.assert_called_with(
            models._cache_name('test2@example.com'))

    def test_user_match(self):
        """Test that match_user() matches a user if one exists"""
        unsub = maker.make(models.Unsubscribe, address='test3@example.com')
        self.assertFalse(unsub.match_user())
        self.assertFalse(unsub.user)
        user = maker.make('accounts.User', email='test3@example.com')
        self.assertEqual(user, unsub.match_user())

    def test_save_attaches_user(self):
        """Test that the save() method attaches a user record if one exists"""
        unsub = maker.make(models.Unsubscribe, address='test4@example.com')
        self.assertFalse(unsub.user)
        user = maker.make('accounts.User', email='test4@example.com')
        unsub.save()
        self.assertTrue(unsub.user)
        self.assertEqual(unsub.user, user)


@override_settings(ORIGIN='http://connect.local', EMAIL_SECRET_KEY='abcd')
class TestEmailOpen(TestCase):
    """Tests for EmailOpen."""
    def test_save_truncates_user_agent(self):
        """If the user agent is too long, it should be truncated to fit."""
        email_open = maker.make(
            models.EmailOpen,
            user_agent="Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.0;"
                       " Trident/4.0; (R1 1.6); SLCC1; .NET CLR 2.0.50727;"
                       " InfoPath.2; OfficeLiveConnector.1.3;"
                       " OfficeLivePatch.0.0; .NET CLR 3.5.30729;"
                       " .NET CLR 3.0.30618; 66760635803; runtime 11.00294;"
                       " 876906799603; 97880703; 669602703; 9778063903;"
                       " 877905603; 89670803; 96690803; 8878091903; 7879040603;"
                       " 999608065603; 799808803; 6666059903; 669602102803;"
                       " 888809342903; 696901603; 788907703; 887806555703;"
                       " 97690214703; 66760903; 968909903; 796802422703;"
                       " 8868026703; 889803611803; 898706903; 977806408603;"
                       " 976900799903; 9897086903; 88780803; 798802301603;"
                       " 9966008603; 66760703; 97890452603; 9789064803;"
                       " 96990759803; 99960107703; 8868087903; 889801155603;"
                       " 78890703; 8898070603; 89970603; 89970539603;"
                       " 89970488703; 8789007603; 87890903; 877904603;"
                       " 9887077703; 798804903; 97890264603; 967901703;"
                       " 87890703; 97690420803; 79980706603; 9867086703;"
                       " 996602846703; 87690803; 6989010903; 977809603;"
                       " 666601903; 876905337803; 89670603; 89970200903;"
        )
        self.assertEqual(len(email_open.user_agent), 255)
