import koppeltaal


def test_messages(connector):
    '''Get messages from the server.'''


def test_messages_for_patient(connector):
    '''Get messages for a specific patient.'''


def test_message_for_id(connector):
    '''Get a specific message.'''


def test_messages_for_status(connector):
    '''Get messages for a specific status.'''


def test_claim(connector, patient, practitioner, careplan):
    '''Claim a specific message.'''
    from koppeltaal.activity_definition import parse
    from koppeltaal.message import parse_messages
    from koppeltaal.create_or_update_care_plan import generate

    # XXX Move to a fixture.
    first_activity = list(parse(connector.activity_definition()))[0]
    xml = generate(connector.domain, first_activity, patient, careplan, practitioner)
    result = connector.create_or_update_care_plan(xml)

    # Get the messages for this patient.
    messages_xml = connector.messages(patient_url=patient.url)
    messages_for_pat = list(parse_messages(messages_xml))
    assert len(messages_for_pat) == 1
    message_info = messages_for_pat[0]
    assert message_info.id is not None
    assert message_info.status == 'New'

    full_message = connector.process_message(message_info.id)
    # Smoke test.
    assert patient.name.given in full_message

    # Now claim the message.
    connector.process_message(message_info.id, action='claim')

    # The status is "Claimed".
    messages_xml = connector.messages(patient_url=patient.url)
    messages_for_pat = list(parse_messages(messages_xml))
    assert len(messages_for_pat) == 1
    message_info = messages_for_pat[0]
    assert message_info.id is not None
    assert message_info.status == 'Claimed'

def test_success(connector, patient, practitioner, careplan):
    '''Claim a specific message and mark it as a success.'''
    from koppeltaal.activity_definition import parse
    from koppeltaal.message import parse_messages
    from koppeltaal.create_or_update_care_plan import generate

    # XXX Move to a fixture.
    first_activity = list(parse(connector.activity_definition()))[0]
    xml = generate(connector.domain, first_activity, patient, careplan, practitioner)
    result = connector.create_or_update_care_plan(xml)

    # Get the messages for this patient.
    messages_xml = connector.messages(patient_url=patient.url)
    messages_for_pat = list(parse_messages(messages_xml))
    assert len(messages_for_pat) == 1
    message_info = messages_for_pat[0]

    # Now claim the message.
    connector.process_message(message_info.id, action='claim')
    connector.process_message(message_info.id, action='success')

    messages_xml = connector.messages(
        patient_url=patient.url, processing_status='New')
    assert len(list(parse_messages(messages_xml))) == 0
    res = connector.process_message(message_info.id)
    # XXX We could parse this instead of doing a string check.
    self.assertIn('<valueCode value="Success" />', res)

def test_cannot_finalize_non_claimed_message(connector):
    '''
    When we try to finalize a message that we hadn't claimed before, this should
    yield an error.
    '''
