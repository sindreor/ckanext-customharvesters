import json
import logging
from hashlib import sha1
import datetime
from ckanext.dcat import converters
from ckanext.dcat.harvesters.base import DCATHarvester

log = logging.getLogger(__name__)

#MERK: Kystverket linker alle datasettene til samme applikasjon for aa hente datasett fra, dette bryter med hvordan
# harvesteren definerer et datasett som unikt!


class GeoNorgeHarvester(DCATHarvester):

    def info(self):
        return {
            'name': 'Geonorge harvester',
            'title': 'Geonorge harvester',
            'description': 'This harvester harvests all kinds of datasets from geonorge.no'
        }


    def _get_guids_and_datasets(self, content):
        doc = json.loads(content)
        datasets=doc["Results"]
        for dataset in datasets:
            guid="GEONORGE:"+dataset.get("Uuid")
            as_string=json.dumps(dataset)
            '''
            if (dataset['Type'] != 'dataset'):
                as_string = 'ABORT'#This to avoid entities that are not datasets
            '''

            yield guid, as_string






    def _get_package_dict(self, harvest_object):

        content = harvest_object.content

        json_dict = json.loads(content)

        package_dict = converters.geonorge_to_CKANpackage(json_dict)



        return package_dict, json_dict
