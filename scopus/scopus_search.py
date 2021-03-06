import hashlib
import warnings
from collections import namedtuple
from json import loads
from os.path import join

from scopus import config
from scopus.utils import download
from scopus.classes import Search


class ScopusSearch(Search):
    @property
    def EIDS(self):
        """Outdated property, will be removed in a future release.  Please use
        get_eids() instead.  For details see
        https://scopus.readthedocs.io/en/latest/tips.html#migration-guide-to-0-x-to-1-x.
        """
        text = "Outdated property, will be removed in a future release.  "\
               "Please use get_eids() instead.  For details see "\
               "https://scopus.readthedocs.io/en/latest/tips.html#"\
               "migration-guide-to-0-x-to-1-x."
        warnings.warn(text, DeprecationWarning)
        return self.get_eids()

    @property
    def results(self):
        """A list of namedtuples in the form (eid doi pii title subtype
        creator authname authid afid coverDate coverDisplayDate
        publicationName issn source_id aggregationType volume issueIdentifier
        pageRange citedby_count openaccess).
        Field definitions correspond to
        https://dev.elsevier.com/guides/ScopusSearchViews.htm, except for
        authname, authid and afid:  These are the ;-joined names resp. Scopus
        IDs resp. Affiliation IDs of the authors of the document.  In case
        the author has multiple affiliations, they are joined on "-".
        """
        out = []
        fields = 'eid doi pii title subtype creator authname authid afid '\
                 'coverDate coverDisplayDate publicationName issn source_id '\
                 'aggregationType volume issueIdentifier pageRange '\
                 'citedby_count openaccess'
        doc = namedtuple('Document', fields)
        for item in self._json:
            try:
                # Deduplicate list of authors
                authors = []
                for i in item['author']:
                    if i not in authors:
                        authors.append(i)
                # Extract information
                authname = ";".join([d['authname'] for d in authors])
                authid = ";".join([d['authid'] for d in authors])
                affs = []
                for auth in authors:
                    aff = auth.get('afid', [])
                    if not isinstance(aff, list):
                        aff = [aff]
                    affs.append('-'.join([d['$'] for d in aff]))
                afid = ';'.join(affs)
                if afid == "":
                    afid = None
            except KeyError:
                authname = None
                authid = None
                afid = None
            new = doc(eid=item['eid'], doi=item.get('prism:doi'),
                      pii=item.get('pii'), title=item['dc:title'],
                      subtype=item.get('subtype'), creator=item.get('dc:creator'),
                      authname=authname, authid=authid, afid=afid,
                      coverDate=item.get('prism:coverDate'),
                      coverDisplayDate=item.get('prism:coverDisplayDate'),
                      publicationName=item.get('prism:publicationName'),
                      issn=item.get('prism:issn'), source_id=item.get('source-id'),
                      aggregationType=item.get('prism:aggregationType'),
                      volume=item.get('prism:volume'),
                      issueIdentifier=item.get('prism:issueIdentifier'),
                      pageRange=item.get('prism:pageRange'),
                      citedby_count=item.get('citedby-count'),
                      openaccess=item['openaccess'])
            out.append(new)
        return out

    def __init__(self, query, refresh=False):
        """Class to search a query, and retrieve a list of EIDs as results.

        Parameters
        ----------
        query : str
            A string of the query.

        refresh : bool (optional, default=False)
            Whether to refresh the cached file if it exists or not.

        Raises
        ------
        Exception
            If the number of search results exceeds 5000.

        Notes
        -----
        Json results are cached in ~/.scopus/search_scoups/{fname} where fname
        is the md5-hashed version of query.

        The COMPLETE view is used to access more fields, see
        https://dev.elsevier.com/guides/ScopusSearchViews.htm.
        """

        self.query = query
        qfile = join(config.get('Directories', 'ScopusSearch'),
                     hashlib.md5(query.encode('utf8')).hexdigest())
        url = 'https://api.elsevier.com/content/search/scopus'
        Search.__init__(self, query, qfile, url, refresh,
                        max_entries=5000, count=25, start=0, view='COMPLETE')

    def __str__(self):
        eids = self.get_eids()
        s = """Search {} yielded in {} documents:\n    {}"""
        return s.format(self.query, len(eids), '\n    '.join(eids))

    def get_eids(self):
        """EIDs of retrieved documents."""
        return [d['eid'] for d in self._json]
