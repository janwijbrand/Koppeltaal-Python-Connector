
import json

from koppeltaal.fhir import packaging
from koppeltaal import (
    fhir,
    codes,
    interfaces)


MARKER = object()


class ResourceEntry(object):
    _model = MARKER
    _content = MARKER
    _definition = MARKER
    _resource_type = MARKER
    _standard_type = MARKER
    _fhir_link = MARKER

    def __init__(self, bundle, resource=None, model=None):
        self._bundle = bundle

        if resource is not None:
            self._content = resource.copy()
            resource_type = self._content.get('resourceType', 'Other')
            if resource_type == 'Other':
                self._standard_type = False
                assert 'code' in self._content
                for code in self._content.get('code').get('coding', []):
                    resource_type = codes.OTHER_RESOURCE_USAGE.unpack_coding(
                        code)
            assert resource_type != 'Other'
            self._resource_type = resource_type
            self._definition = fhir.REGISTRY.definition_for_type(
                self.resource_type)
        if model is not None:
            self._model = model

    @property
    def definition(self):
        if self._definition is not MARKER:
            return self._definition
        assert self._model is not MARKER, 'Need a model.'
        self._definition = fhir.REGISTRY.definition_for_model(self._model)
        return self._definition

    @property
    def resource_type(self):
        if self._resource_type is not MARKER:
            return self._resource_type
        self._resource_type, self._standard_type = \
            fhir.REGISTRY.type_for_definition(self.definition)
        return self._resource_type

    @property
    def standard_type(self):
        if self._standard_type is not MARKER:
            return self._standard_type
        self._resource_type, self._standard_type = \
            fhir.REGISTRY.type_for_definition(self.definition)
        return self._standard_type

    @property
    def fhir_link(self):
        if self._fhir_link is not MARKER:
            return self._fhir_link
        assert self._model is not MARKER, 'Need a model.'

        if self._model.fhir_link is not None:
            self._fhir_link = self._model.fhir_link
            return self._fhir_link

        if interfaces.IIdentifiedFHIRResource.providedBy(self._model):
            self._fhir_link = self._bundle.configuration.link(
                self._model, self.resource_type)
            return self._fhir_link

        return None

    def unpack(self):
        if self._model is not MARKER:
            return self._model

        self._model = None
        if self.definition is not None:
            self._model = packaging.unpack(
                self._content, self.definition, self._bundle)
            if self._model is not None:
                self._model.fhir_link = self.fhir_link
        return self._model

    def pack(self):
        if self._content is MARKER:
            if self.definition is None:
                raise interfaces.InvalidValue(None, self._model)
            self._content = packaging.pack(
                self._model, self.definition, self._bundle)
            if self.standard_type:
                self._content['resourceType'] = self.resource_type
            else:
                # This is not a standard fhir resource type.
                self._content['resourceType'] = 'Other'
                self._content['code'] = {
                    'coding': [
                        codes.OTHER_RESOURCE_USAGE.pack_coding(
                            self.resource_type)]}
        return self._content

    def __eq__(self, other):
        if isinstance(other, dict):
            return other.get('reference', None) in (
                self.fhir_link, self.atom_id)
        if interfaces.IFHIRResource.providedBy(other):
            if self._model is not MARKER:
                return self._model is other
            assert self.fhir_link is not None, 'Should not happen'
            return other.fhir_link == self.fhir_link

        return NotImplemented()

    def __format__(self, _):
        return '<{} fhir_link="{}" type="{}">{}</{}>'.format(
            self.__class__.__name__,
            self.fhir_link,
            self.resource_type,
            json.dumps(self._content, indent=2, sort_keys=True),
            self.__class__.__name__)


class Resource(object):
    entry_type = ResourceEntry

    def __init__(self, domain=None, configuration=None):
        self.items = []
        self.domain = domain
        self.configuration = configuration

    def add_payload(self, response):
        self.items.append(self.entry_type(self, resource=response))

    def add_model(self, model):
        assert interfaces.IFHIRResource.providedBy(model), \
            'Can only add resources'
        entry = self.find(model)
        if entry is None:
            entry = self.entry_type(self, model=model)
            self.items.append(entry)
        return entry

    def find(self, entry):
        for item in self.items:
            if entry == item:
                # ResourceEntry provides a smart "comparison".
                return item
        return None

    def pack(self):
        for item in self.items:
            yield item.pack()

    def get_payload(self):
        for payload in self.pack():
            return payload

    def unpack(self):
        for item in self.items:
            yield item.unpack()
