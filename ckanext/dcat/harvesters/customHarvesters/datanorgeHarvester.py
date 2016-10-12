import json
import logging
from hashlib import sha1
from ckanext.dcat import converters
from ckanext.dcat.harvesters.base import DCATHarvester

log = logging.getLogger(__name__)


class DCATJSONHarvester(DCATHarvester):

    def info(self):
        return {
            'name': 'dcat_json',
            'title': 'Datanorge harvester(Transport related datasets)',
            'description': 'This harvester harvests transport-related datasets, and is intended for harvesting from data.norge.no'
        }


    def _get_guids_and_datasets(self, content):

        doc = json.loads(content)

        if isinstance(doc, list):
            # Assume a list of datasets
            datasets = doc
        elif isinstance(doc, dict):
            datasets = doc.get('datasets', [])#Changed from 'dataset' to 'datasets'
        else:
            raise ValueError('Wrong JSON object')

        for dataset in datasets:
            # Modification_____________________________
            if ('Transport' not in dataset['keyword']):
                as_string = 'ABORT'
            else:
            # _________________________________
                as_string = json.dumps(dataset)

            # Get identifier
            guid = dataset.get('id')#Changed from identifier to id
            if not guid:
                # This is bad, any ideas welcomed
                guid = sha1(as_string).hexdigest()

            yield guid, as_string





    def _get_package_dict(self, harvest_object):

        content = harvest_object.content

        dcat_dict = json.loads(content)

        package_dict = converters.dcat_to_ckan(dcat_dict)



        return package_dict, dcat_dict
