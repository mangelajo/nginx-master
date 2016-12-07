import ovh
from dns import resolver

A = 'A'
CNAME = 'CNAME'
AAAA = 'AAAA'
DKIM = 'DKIM'
LOC = 'LOC'
MX = 'MX'
NAPTR = 'NAPTR'
NS = 'NS'
PTR = 'PTR'
SPF = 'SPF'
SRV = 'SRV'
SSHFP = 'SSHFP'
TXT = 'TXT'

UPDATED = 'updated'
CREATED = 'created'


def resolve(name, reg_type=A):
    _resolver = resolver.Resolver()
    _resolver.nameservers = ['8.8.8.8', '8.8.4.4']
    return list(_resolver.query(name, reg_type))


class Domain:
    def __init__(self, domain):
        self._domain = domain
        self._client = ovh.Client()

    @property
    def records(self):
        records = {}

        for record_id in self._client.get(
                '/domain/zone/{}/record'.format(self._domain)):
            info = self._client.get('/domain/zone/{}/record/{}'.format(
                self._domain, record_id))
            records[(info['subDomain'], info['fieldType'])] = info

        return records

    def set_record(self, name, rec_type, value):
        records = self.records
        if (name, rec_type) in records:
            self._update_record(records[(name, rec_type)]['id'], name,
                                rec_type, value)
            return UPDATED

        else:
            self._create_record(name, rec_type, value)
            return CREATED

    def del_record(self, name, rec_type):
        records = self.records
        if (name, rec_type) in records:
            self._client.delete('/domain/zone/{}/record/{}'.format(
                self._domain, records[(name, rec_type)]['id']))
            self._refresh()
            return True
        return False


    def _update_record(self, rec_id, name, rec_type, value):
        self._client.delete('/domain/zone/{}/record/{}'.format(self._domain,
                                                               rec_id))
        self._create_record(name, rec_type, value)

    def _create_record(self, name, rec_type, value):
        self._client.post('/domain/zone/{}/record'.format(self._domain),
                          fieldType=rec_type, subDomain=name, target=value)
        self._refresh()

    def _refresh(self):
        self._client.post('/domain/zone/{}/refresh'.format(self._domain))