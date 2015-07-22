"""
Connect to Koppeltaal server
"""
import urlparse
import lxml.etree
import requests
import koppeltaal
import koppeltaal.metadata
import feedreader.parser

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

    def post_message(self, xml):
        # Get from the metadata definition
        mailbox_url = koppeltaal.metadata.metadata(
            self.metadata())['messaging']['endpoint']
        # Assert that the protocol is the same.
        assert urlparse.urlparse(mailbox_url).scheme == urlparse.urlparse(
            self.server).scheme

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

    def _do_message_query(self, params):
        url = '{}/{}/_search'.format(self.server, MESSAGE_HEADER_URL)
        response = requests.get(
            url,
            params=params,
            auth=(self.username, self.password),
            headers={'Accept': 'application/xml'},
            allow_redirects=False)
        response.raise_for_status()
        return response.content

    def message(self, id):
        """
        https://koppeltaal/FHIR/Koppeltaal/MessageHeader/_search?_id=[id]

        Fetches a complete Bundle for a single Message.
        """
        return self._do_message_query({'_id': id})

    def messages(
            self,
            patient_url=None,
            processing_status=None,
            summary=None,
            count=None):
        """
        https://koppelbox/FHIR/Koppeltaal/MessageHeader/_search?_summary=true&_count=[X]

        This will return a Bundle of MessageHeaders, allowing an application
        to browse the available messages. A pagesize can be specified in the
        _count parameter.

        The following additional query parameters can be specified:

        Patient: Filters on the Patient dossier this message belongs event:
        Filters on the message type ProcessingStatus: Filters on the
        ProcessingStatus (New|Claimed|Success|Failed).
        """
        params = {
            # Get all messages if no count is given.
            '_count': count if count is not None else 5000
        }
        if patient_url:
            params['Patient'] = patient_url
        if processing_status:
            params['ProcessingStatus'] = processing_status
        if summary:
            params['_summary'] = 'true'
        return self._do_message_query(params)

    def process_message(self, id, action):
        # Updating the ProcessingStatus for a Message - After a message
        # has been successfully processed, the application must update its
        # ProcessingStatus to "Success" on URL
        # [[|https://koppelbox/FHIR/Koppeltaal/MessageHeader/[id]]] (that
        # is, the URL returned as id link in the for the MessageHeader in
        # the bundle.)
        status = {
            'claim': 'Claimed',
            'success': 'Success'
        }.get(action, None)
        if status is None:
            raise ValueError('Unknown status')

        # Get the message.
        url = '{}/{}/_search'.format(self.server, MESSAGE_HEADER_URL)
        response = requests.get(
            url,
            params={'_id': id},
            auth=(self.username, self.password),
            headers={'Accept': 'application/xml'},
            allow_redirects=False)
        response.raise_for_status()
        feed = feedreader.parser.from_string(response.content)
        # XXX How can you be so sure about nr 0.?
        message_header = feed.entries[0].content.find(
            './/fhir:MessageHeader', namespaces=koppeltaal.NS)
        # Parse the XML with lxml.etree and set the ProcessingStatus.
        processing_status = message_header.find(
            './/fhir:extension[@url="{koppeltaal}/MessageHeader#'
            'ProcessingStatusStatus"]'.format(
                **koppeltaal.NS), namespaces=koppeltaal.NS).find(
            'fhir:valueCode', namespaces=koppeltaal.NS)
        processing_status.attrib['value'] = status

        response = requests.put(
            feed.entries[0].id,
            data=lxml.etree.tostring(message_header),
            auth=(self.username, self.password),
            headers={'Accept': 'application/xml'},
            allow_redirects=False)
        response.raise_for_status()
        return response.content
