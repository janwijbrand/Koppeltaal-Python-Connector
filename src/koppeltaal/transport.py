import urlparse
import requests

from koppeltaal import (interfaces, logger)


class Response(object):

    def __init__(self, json=None, location=None):
        self.json = json
        self.location = location


class Transport(object):

    def __init__(self, server, username, password):
        parts = urlparse.urlparse(server)

        self.server = server
        self.scheme = parts.scheme
        self.netloc = parts.netloc
        self.username = username
        self.password = password

        self.session = requests.Session()

    def absolute_url(self, url):
        # Make sure we talk to the proper server by updating the URL.
        parts = urlparse.urlparse(url)[2:]
        return urlparse.urlunparse((self.scheme, self.netloc) + parts)

    def query(self, url, params=None, username=None, password=None):
        """Query a url.
        """
        try:
            response = self.session.get(
                self.absolute_url(url),
                params=params,
                auth=(username or self.username, password or self.password),
                headers={'Accept': 'application/json'},
                timeout=interfaces.TIMEOUT,
                allow_redirects=False)
            response.raise_for_status()
        except requests.RequestException as error:
            raise interfaces.InvalidResponse(error)
        if not response.headers['content-type'].startswith('application/json'):
            raise interfaces.InvalidResponse(response)
        json = response.json()
        logger.debug_json('Query on {url}:\n {json}', json=json, url=url)
        return Response(json=json)

    def query_redirect(self, url, params=None):
        """Query a url for a redirect.
        """
        try:
            response = self.session.get(
                self.absolute_url(url),
                params=params,
                auth=(self.username, self.password),
                timeout=interfaces.TIMEOUT,
                allow_redirects=False)
        except requests.RequestException as error:
            raise interfaces.InvalidResponse(error)
        if not response.is_redirect:
            raise interfaces.InvalidResponse(response)
        return Response(location=response.headers.get('location'))

    def create(self, url, data):
        """Create a new resource at the given url with JSON data.
        """
        try:
            response = self.session.post(
                self.absolute_url(url),
                auth=(self.username, self.password),
                json=data,
                headers={'Accept': 'application/json'},
                timeout=interfaces.TIMEOUT,
                allow_redirects=False)
            response.raise_for_status()
        except requests.RequestException as error:
            raise interfaces.InvalidResponse(error)
        if not response.headers['content-type'].startswith('application/json'):
            raise interfaces.InvalidResponse(response)
        return Response(
            json=response.json() if response.text else None,
            location=response.headers.get('content-location'))

    def update(self, url, data):
        """Update an existing resource at the given url with JSON data.
        """
        try:
            response = self.session.put(
                self.absolute_url(url),
                auth=(self.username, self.password),
                json=data,
                headers={'Accept': 'application/json'},
                timeout=interfaces.TIMEOUT,
                allow_redirects=False)
            response.raise_for_status()
        except requests.RequestException as error:
            raise interfaces.InvalidResponse(error)
        if not response.headers['content-type'].startswith('application/json'):
            raise interfaces.InvalidResponse(response)
        return Response(
            json=response.json() if response.text else None,
            location=response.headers.get('content-location'))