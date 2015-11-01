"""
Blue State Digital's BSDTools OAuth2 Python-Social-Auth Provider
"""
from social.backends.oauth import BaseOAuth2


class BSDToolsOAuth2(BaseOAuth2):
    """
    BSDTool's OAuth2 backend

    BSDTools offers an OAuth2 backend for client usage. Contact BSD customer
    support for more information about how to create and manage OAuth2
    credentials.
    """
    name = 'bsdtools'
    ID_KEY = 'id'
    USERNAME_KEY = 'id'
    ACCESS_TOKEN_METHOD = 'GET'
    REFRESH_TOKEN_METHOD = 'GET'
    AUTHORIZATION_URL = 'https://{instance}/page/oauth2/authorize'
    ACCESS_TOKEN_URL = 'https://{instance}/page/oauth2/access-token'

    def authorization_url(self):
        """Return the BSDTools Authorization URL"""
        return self.AUTHORIZATION_URL.format(instance=self.instance)

    def access_token_url(self):
        """Return the BSDTools Access Token URL"""
        return self.ACCESS_TOKEN_URL.format(instance=self.instance)

    def request_access_token(self, *args, **kwargs):
        """Request the Access Token"""
        kwargs['params'] = kwargs.get('data', {})
        return super(BSDToolsOAuth2, self).request_access_token(*args, **kwargs)

    @property
    def instance(self):
        """Return the BSDTools Instance Hostname"""
        return self.setting('INSTANCE')

    # pylint: disable=no-self-use
    def get_user_details(self, response):
        """
        Return user details from a BSD constituent record

        Takes the constituent record JSON response from `/page/graph/cons` and
        generates user data similar to other python-social-auth backends.
        """
        username = response['id']
        first_name = response.get('firstname', '')
        last_name = response.get('lastname', '')
        full_name = u'{first} {last}'.format(
            first=first_name, last=last_name).strip()
        email = [em['email'] for em in response['email'] if em['is_primary']][0]

        return {'username': username,
                'email': email,
                'fullname': full_name,
                'first_name': first_name,
                'last_name': last_name}

    def user_data(self, access_token, *args, **kwargs):
        """Loads user data from service"""
        url = 'https://{instance}/page/graph/cons'.format(
            instance=self.instance)
        return self.get_json(url, params={
            'access_token': access_token
        })
