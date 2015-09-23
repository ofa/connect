"""Tests for detecting a user's location."""

from decimal import Decimal

from django.test import TestCase
from mock import Mock, patch

from open_connect.connect_core.utils import location


@patch.object(location.geocoders, 'GoogleV3')
class GeocodeLocationTest(TestCase):
    """Test geocode_location."""
    def test_geocode_location(self, mock):
        """Test that a location is geocoded correctly."""
        mock_geocoder = Mock()
        mock_geocoder.geocode.return_value = [
            (u'North Desplaines St & West Fulton Mkt, Chicago, IL 60661, USA',
             (41.8868014, -87.6442893))
        ]
        mock.return_value = mock_geocoder
        self.assertEqual(
            location.geocode_location('something'),
            (41.8868014, -87.6442893)
        )

    def test_geocode_location_geocoder_raises_exception(self, mock):
        """Test that geocode_location returns None if there's an exception."""
        exception = ValueError('something went wrong')
        mock_geocoder = Mock()
        mock_geocoder.geocode.side_effect = exception
        mock.return_value = mock_geocoder
        self.assertEqual(
            location.geocode_location('some location'),
            (None, None)
        )

    def test_geocode_returns_invalid_format(self, mock):
        """Test geocode_location returns None if the response is unusual."""
        mock_geocoder = Mock()
        mock_geocoder.geocode.return_value = "this isn't right!"
        mock.return_value = mock_geocoder
        self.assertEqual(
            location.geocode_location('some location'),
            (None, None)
        )


class CleanCoordsTest(TestCase):
    """Test clean_coords."""
    VALID_RESPONSE = (Decimal(81), Decimal(-81))

    # pylint: disable=invalid-name
    def assertCoordsAreValid(self, coords):
        """Shortcut for asserting that coordinates are valid."""
        self.assertEqual(coords, self.VALID_RESPONSE)

    def test_coords_is_string(self):
        """Test clean_coords with a string that has coordinates in it."""
        response = location.clean_coords("81,-81")
        self.assertCoordsAreValid(response)

    def test_coords_is_invalid_string(self):
        """Test clean_coords with a string that does not have coordinates."""
        response = location.clean_coords("awooga!")
        self.assertIsNone(response)

    def test_coords_is_unicode(self):
        """Test clean_coords with a unicode string that has coordinates."""
        response = location.clean_coords(u'81,-81')
        self.assertCoordsAreValid(response)

    def test_coords_is_invalid_unicode(self):
        """Test clean_coords with a unicode string that doesn't have coords."""
        response = location.clean_coords(u'awooga!')
        self.assertIsNone(response)

    def test_coords_is_tuple(self):
        """Test clean_coords with a tuple that has coordinates."""
        response = location.clean_coords((81, -81))
        self.assertCoordsAreValid(response)

    def test_coords_is_list(self):
        """Test clean_coords with a list that has coordinates."""
        response = location.clean_coords([81, -81])
        self.assertCoordsAreValid(response)

    def test_coords_tuple_length_is_less_than_two(self):
        """Test clean_coords returns None if tuple has less than 2 items."""
        response = location.clean_coords((81,))
        self.assertIsNone(response)

    def test_coords_tuple_length_is_greater_than_two(self):
        """Test clean_coords returns None if tuple has more than 2 items."""
        response = location.clean_coords((81, -81, 100))
        self.assertIsNone(response)

    def test_coords_index_0_invalid(self):
        """Test clean_coords if index 0 is invalid."""
        response = location.clean_coords(('cow', -81))
        self.assertIsNone(response)

    def test_coords_index_1_invalid(self):
        """Test clean_coords if index 1 is invalid."""
        response = location.clean_coords((81, 'cow'))
        self.assertIsNone(response)

    def test_coords_invalid_type(self):
        """Test clean_coords returns None if it gets an invalid type."""
        response = location.clean_coords(1)
        self.assertIsNone(response)

    def test_coords_dict(self):
        """Test clean_coords if it receives a dict with coordinates."""
        response = location.clean_coords({'lat': 81, 'lng': -81})
        self.assertCoordsAreValid(response)

    def test_coords_dict_no_lat(self):
        """Test clean_coords if it receives a dict with only latitude."""
        response = location.clean_coords({'lng': 1})
        self.assertIsNone(response)

    def test_coords_dict_no_lng(self):
        """Test clean_coords if it receives a dict with only longitude."""
        response = location.clean_coords({'lat': 1})
        self.assertIsNone(response)

    def test_coords_dict_no_lat_no_lng(self):
        """Test clean_coords if it receives a dict without coordinates."""
        response = location.clean_coords({})
        self.assertIsNone(response)


class GetLocationTest(TestCase):
    """Test get_location."""
    def test_get_location_with_coords(self):
        """Test get_location with coordinates."""
        response = location.get_coordinates((81, -81))
        self.assertEqual(response, (81, -81))

    @patch.object(location, 'geocode_location')
    def test_get_location_without_coords(self, mock):
        """Test get_location without coordinates."""
        self.assertEqual(mock.call_count, 0)
        location.get_coordinates('awooga!')
        self.assertEqual(mock.call_count, 1)
