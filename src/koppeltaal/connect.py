"""
Connect to Koppeltaal server
"""
import urlparse
import requests
import koppeltaal
import koppeltaal.metadata

# The URLs that can't be reached from the metadata are defined as constants
# here.
METADATA_URL = 'FHIR/Koppeltaal/metadata'
ACTIVITY_DEFINITION_URL = 'FHIR/Koppeltaal/Other?code=ActivityDefinition'
MESSAGE_HEADER_URL = 'FHIR/Koppeltaal/MessageHeader'
OAUTH_LAUNCH_URL = 'OAuth2/Koppeltaal/Launch'

# XXX Request pool, take into account multiple apps may be using this same
# piece of code.

class Connector(object):
    server = None
    username = None
    password = None
    domain = None  # The domain on the server to work against.

    def __init__(self, server, username, password, domain=None):
        self.server = server
        self.username = username
        self.password = password
        self.domain = domain

    # Some nice cache decorator here.
    def metadata(self):
        # XXX Add caching based on the 'reliableCache' information.
        url = '{}/{}'.format(self.server, METADATA_URL)
        response = requests.get(
            url,
            headers={'accept': 'application/xml'},
            allow_redirects=False)
        response.raise_for_status()
        # The result is raw XML conformance statement.
        return response.content

    def test_authentication(self):
        # Perhaps some other URL to test authentication?
        url = '{}/{}'.format(self.server, ACTIVITY_DEFINITION_URL)
        koppeltaal.logger.debug('test_authentication %s', url)
        response = requests.get(
            url,
            headers={'accept': 'application/xml'},
            auth=(self.username, self.password),
            allow_redirects=False)
        return response.status_code == 200

    def activity_definition(self):
        # XXX Cache this information?
        url = '{}/{}'.format(self.server, ACTIVITY_DEFINITION_URL)
        response = requests.get(
            url,
            auth=(self.username, self.password),
            headers={'Accept': 'application/xml'},
            allow_redirects=False)
        response.raise_for_status()
        return response.content

    def create_or_update_care_plan(self, xml):
        # Get from the metadata definition
        mailbox_url = koppeltaal.metadata.metadata(
            self.metadata())['messaging']['endpoint']
        # Assert that the protocol is the same.
        assert urlparse.urlparse(mailbox_url).scheme == urlparse.urlparse(self.server).scheme

        koppeltaal.logger.debug('Sending XML %s', xml)
        response = requests.post(
            mailbox_url,
            auth=(self.username, self.password),
            data=xml,
            headers={
                'Accept': 'application/xml',
                'Content-Type': 'application/xml',
            },
            allow_redirects=False)
        response.raise_for_status()
        # We could parse the response.
        # In the response find the URL to the newly created careplan:
        # XXX History information.
        return response.content

    def launch(self, activity_id, patient_url, user_url):
        response = requests.get(
            '{}/{}'.format(self.server, OAUTH_LAUNCH_URL),
            auth=(self.username, self.password),
            params={
                'client_id': activity_id,
                'patient': patient_url,
                'user': user_url,
                'resource': activity_id
            },
            allow_redirects=False)
        assert response.is_redirect
        # The Launch sequence returns a redirect to the URL we should present
        # to the user.
        return response.headers.get('location')

    def messages(self, patient_url=None):
        """
        From the specs:

        Retrieving messages - There are 3 supported interactions:

        https://koppelbox/FHIR/Koppeltaal/MessageHeader/_search?_summary=true&_count=[X]
        This will return a Bundle of MessageHeaders, allowing an application to
        browse the available messages. A pagesize can be specified in the _count
        parameter.

        https://koppeltaal/FHIR/Koppeltaal/MessageHeader/_search?_id=[id]
        This can be used to fetch the complete Bundle for a single Message for which
        the MessageHeader was retrieved through the previous action.

        The following additional query parameters can be specified:

        Patient: Filters on the Patient dossier this message belongs
        event: Filters on the message type
        ProcessingStatus: Filters on the ProcessingStatus (New|Claimed|Success|Failed).
        This query parameter cannot be passed to the named query used in interaction 1.

        Currently, only patient url is implemented.
        """
        url = '{}/{}/_search'.format(self.server, MESSAGE_HEADER_URL)

        params = {}
        if patient_url:
            params['Patient'] = patient_url

        response = requests.get(
            url,
            params=params,
            auth=(self.username, self.password),
            headers={'Accept': 'application/xml'},
            allow_redirects=False)
        response.raise_for_status()
        return response.content

    def message(self, id, action='get'):
        """
        Interact with a single message. Actions are:
        get the message (default)
        claim the message
        finalize the message as a success
        """
        import pytest ; pytest.set_trace()
