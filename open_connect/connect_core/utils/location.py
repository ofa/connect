"""Location utilities."""
# pylint: disable=broad-except

from decimal import Decimal

from geopy import geocoders


# pylint: disable=line-too-long
STATES = ['AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'DC', 'FL', 'GA', 'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD', 'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ', 'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC', 'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY']


def geocode_location(location):
    """Geocode a location string using Google geocoder."""
    geocoder = geocoders.GoogleV3()
    try:
        result = geocoder.geocode(location, exactly_one=False)
    except Exception:
        return None, None
    try:
        ctr_lat, ctr_lng = result[0][1]
    except IndexError:
        return None, None

    return clean_coords(coords=(ctr_lat, ctr_lng))


def clean_coords(coords):
    """Make a best guess at finding coordinates.

    Input can be a list, tuple, or string representing coordinates.

    Returns a tuple containing Decimals representing coordinates.
    """
    if isinstance(coords, (str, unicode)):
        coords = coords.split(',')

    if isinstance(coords, dict):
        if 'lat' in coords and 'lng' in coords:
            coords = coords['lat'], coords['lng']

    if isinstance(coords, (tuple, list)):
        if len(coords) != 2:
            coords = None

        try:
            coords = (Decimal(coords[0]), Decimal(coords[1]))
        except Exception:
            coords = None
    else:
        coords = None

    return coords


def get_coordinates(location):
    """Find coordinates in location or attempt to geocode it."""
    coords = clean_coords(location)
    if not coords:
        coords = geocode_location(location)
    return coords
