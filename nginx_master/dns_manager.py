import ovh
from dns import resolver

from oslo_log import log as logging

LOG = logging.getLogger(__name__)

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

NOTCHANGED = 'notchanged'
UPDATED = 'updated'
CREATED = 'created'


class DomainNotFound(Exception):
    pass

def resolve(name, reg_type=A, nameservers=['8.8.8.8', '8.8.4.4']):
    _resolver = resolver.Resolver()
    _resolver.nameservers = nameservers
    return list(_resolver.query(name, reg_type))


class Domain:
    def __init__(self, domain):
        self._domain = domain
        self._client = ovh.Client()

    @property
    def records(self):
        records = {}
        try:
            for record_id in self._client.get(
                    '/domain/zone/{}/record'.format(self._domain)):
                info = self._client.get('/domain/zone/{}/record/{}'.format(
                    self._domain, record_id))
                records[(info['subDomain'], info['fieldType'])] = info
        except ovh.exceptions.ResourceNotFoundError:
            raise DomainNotFound()
        return records

    def set_record(self, name, rec_type, value, ttl=3600):
        ttl = int(ttl)
        records = self.records

        if (name, rec_type) in records:
            record = records[(name, rec_type)]
            if rec_type == SPF:
                record['target'] = record['target'].strip('"')
            if record['target'] == value and record['ttl'] == ttl:
                LOG.info('DNS record %s.%s (%s) as "%s" (ttl=%d) was already'
                         ' set', name, self._domain, rec_type, value, ttl)
                return NOTCHANGED
            LOG.info('Updating record %s.%s (%s) to "%s" (ttl=%d)', name,
                     self._domain, rec_type, value, ttl)
            self._update_record(records[(name, rec_type)]['id'], name,
                                rec_type, value, ttl)
            return UPDATED

        else:
            LOG.info('Creating record %s.%s (%s) as "%s" (ttl=%d)', name,
                     self._domain, rec_type, value, ttl)
            self._create_record(name, rec_type, value, ttl)
            return CREATED

    def del_record(self, name, rec_type):
        records = self.records
        if (name, rec_type) in records:
            self._client.delete('/domain/zone/{}/record/{}'.format(
                self._domain, records[(name, rec_type)]['id']))
            self._refresh()
            return True
        return False

    def _update_record(self, rec_id, name, rec_type, value, ttl=3600):
        self._client.delete('/domain/zone/{}/record/{}'.format(self._domain,
                                                               rec_id))
        self._create_record(name, rec_type, value, ttl)

    def _create_record(self, name, rec_type, value, ttl=3600):
        self._client.post('/domain/zone/{}/record'.format(self._domain),
                          fieldType=rec_type, subDomain=name, target=value,
                          ttl=ttl)
        self._refresh()

    def _refresh(self):
        self._client.post('/domain/zone/{}/refresh'.format(self._domain))