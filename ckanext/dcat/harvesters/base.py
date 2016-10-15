import logging
import os
import uuid
import datetime
import sys

import rdflib
import requests
from ckanext.harvest.harvesters import HarvesterBase
from ckanext.harvest.model import HarvestObject, HarvestObjectExtra

import json

from ckan import logic
from ckan import model
from ckan import plugins as p

log = logging.getLogger(__name__)


class DCATHarvester(HarvesterBase):

    MAX_FILE_SIZE = 1024 * 1024 * 50  # 50 Mb
    CHUNK_SIZE = 1024

    force_import = False

    _user_name = None




    def _get_content_and_type(self, url, harvest_job, page=1, content_type=None):
        '''
        Gets the content and type of the given url.

        :param url: a web url (starting with http) or a local path
        :param harvest_job: the job, used for error reporting
        :param page: adds paging to the url
        :param content_type: will be returned as type
        :return: a tuple containing the content and content-type
        '''

        if not url.lower().startswith('http'):
            # Check local file
            if os.path.exists(url):
                with open(url, 'r') as f:
                    content = f.read()
                content_type = content_type or rdflib.util.guess_format(url)
                return content, content_type
            else:
                self._save_gather_error('Could not get content for this url', harvest_job)
                return None, None

        try:
            if page > 1:
                url = url + '&' if '?' in url else url + '?'
                url = url + 'page={0}'.format(page)


            log.debug('Getting file %s', url)

            # first we try a HEAD request which may not be supported
            did_get = False
            r = requests.head(url)
            if r.status_code == 405 or r.status_code == 400:
                r = requests.get(url, stream=True)
                did_get = True
            r.raise_for_status()

            cl = r.headers.get('content-length')
            if cl and int(cl) > self.MAX_FILE_SIZE:
                msg = '''Remote file is too big. Allowed
                    file size: {allowed}, Content-Length: {actual}.'''.format(
                    allowed=self.MAX_FILE_SIZE, actual=cl)
                self._save_gather_error(msg, harvest_job)
                return None, None

            if not did_get:
                r = requests.get(url, stream=True)

            length = 0
            content = ''
            for chunk in r.iter_content(chunk_size=self.CHUNK_SIZE):
                content = content + chunk
                length += len(chunk)

                if length >= self.MAX_FILE_SIZE:
                    self._save_gather_error('Remote file is too big.', harvest_job)
                    return None, None

            if content_type is None and r.headers.get('content-type'):
                content_type = r.headers.get('content-type').split(";", 1)[0]

            return content, content_type

        except requests.exceptions.HTTPError, error:
            if page > 1 and error.response.status_code == 404:
                # We want to catch these ones later on
                raise

            msg = 'Could not get content. Server responded with %s %s' % (
                error.response.status_code, error.response.reason)
            self._save_gather_error(msg, harvest_job)
            return None, None
        except requests.exceptions.ConnectionError, error:
            msg = '''Could not get content because a
                                connection error occurred. %s''' % error
            self._save_gather_error(msg, harvest_job)
            return None, None
        except requests.exceptions.Timeout, error:
            msg = 'Could not get content because the connection timed out.'
            self._save_gather_error(msg, harvest_job)
            return None, None

    def _get_user_name(self):
        if self._user_name:
            return self._user_name

        user = p.toolkit.get_action('get_site_user')(
            {'ignore_auth': True, 'defer_commit': True},
            {})
        self._user_name = user['name']

        return self._user_name

    def _get_object_extra(self, harvest_object, key):
        '''
        Helper function for retrieving the value from a harvest object extra,
        given the key
        '''
        for extra in harvest_object.extras:
            if extra.key == key:
                return extra.value
        return None

    def _get_package_name(self, harvest_object, title):

        package = harvest_object.package
        if package is None or package.title != title:
            name = self._gen_new_name(title)
            if not name:
                raise Exception('Could not generate a unique name from the title or the GUID. Please choose a more unique title.')
        else:
            name = package.name

        return name

    def get_original_url(self, harvest_object_id):
        obj = model.Session.query(HarvestObject).\
                                    filter(HarvestObject.id==harvest_object_id).\
                                    first()
        if obj:
            return obj.source.url
        return None

    ## Start hooks

    def modify_package_dict(self, package_dict, dcat_dict, harvest_object):
        '''
            Allows custom harvesters to modify the package dict before
            creating or updating the actual package.
        '''
        return package_dict

    ## End hooks

    def gather_stage(self,harvest_job):
        log.debug('In DCATHarvester gather_stage')


        ids = []

        # Get the previous guids for this source
        query = model.Session.query(HarvestObject.guid, HarvestObject.package_id).\
                                    filter(HarvestObject.current==True).\
                                    filter(HarvestObject.harvest_source_id==harvest_job.source.id)



        guid_to_package_id = {}

        for guid, package_id in query:
            guid_to_package_id[guid] = package_id

        guids_in_db = guid_to_package_id.keys()
        guids_in_source = []


        # Get file contents
        url = harvest_job.source.url

        previous_guids = []
        page = 1
        while True:

            try:
                content, content_type = self._get_content_and_type(url, harvest_job, page)
            except requests.exceptions.HTTPError, error:
                if error.response.status_code == 404:
                    if page > 1:
                        # Server returned a 404 after the first page, no more
                        # records
                        log.debug('404 after first page, no more pages')
                        break
                    else:
                        # Proper 404
                        msg = 'Could not get content. Server responded with 404 Not Found'
                        self._save_gather_error(msg, harvest_job)
                        return None
                else:
                    # This should never happen. Raising just in case.
                    raise

            if not content:
                return None


            try:

                batch_guids = []
                for guid, as_string in self._get_guids_and_datasets(content):
                    '''
                    When ABORT is received from the datanorgeHarvester.py, the dataset is skipped since it is not transport-related
                    NOTE: This way of filtering transport related datasets should be changed when DIFI gets their new API working.
                    With their current API, it is not possible to filter on category, so it must be done manually like this.
                    THIS IS ALSO USED BY GEONORGE
                    '''

                    if (as_string == 'ABORT'):
                        log.debug('Dataset skipped, not relevant'.format(guid.encode('utf8')))
                        continue


                    log.debug('Got identifier: {0}'.format(guid.encode('utf8')))


                    batch_guids.append(guid)

                    if guid not in previous_guids:

                        if guid in guids_in_db:
                            # Dataset needs to be udpated
                            obj = HarvestObject(guid=guid, job=harvest_job,
                                            package_id=guid_to_package_id[guid],
                                            content=as_string,
                                            extras=[HarvestObjectExtra(key='status', value='change')])
                        else:
                            # Dataset needs to be created
                            obj = HarvestObject(guid=guid, job=harvest_job,
                                            content=as_string,
                                            extras=[HarvestObjectExtra(key='status', value='new')])
                        obj.save()
                        ids.append(obj.id)

                if len(batch_guids) > 0:
                    guids_in_source.extend(set(batch_guids) - set(previous_guids))
                else:
                    log.debug('Empty document, no more records')
                    # Empty document, no more ids
                    break

            except ValueError, e:
                msg = 'Error parsing file: {0}'.format(str(e))
                self._save_gather_error(msg, harvest_job)
                return None

            if sorted(previous_guids) == sorted(batch_guids):
                # Server does not support pagination or no more pages
                log.debug('Same content, no more pages')
                break


            page = page + 1

            previous_guids = batch_guids

        # Check datasets that need to be deleted
        guids_to_delete = set(guids_in_db) - set(guids_in_source)
        for guid in guids_to_delete:
            obj = HarvestObject(guid=guid, job=harvest_job,
                                package_id=guid_to_package_id[guid],
                                extras=[HarvestObjectExtra(key='status', value='delete')])
            ids.append(obj.id)
            model.Session.query(HarvestObject).\
                  filter_by(guid=guid).\
                  update({'current': False}, False)
            obj.save()


        return ids

    def fetch_stage(self,harvest_object):
        return True


    def check_resource_existence(self, resource):
        for dataset in logic.action.get.current_package_list_with_resources({'model': model, 'user': self._get_user_name()}, {"limit":sys.maxint,"offset":0}):
            for res in dataset['resources']:
                if(res["url"].strip('/')==resource.strip('/')):
                   return True
        return False #Returned if the resource is not in any existing dataset

    def get_metadata_provenance_for_just_this_harvest(cls, harvest_object, type, excluded_resources):
        dict={}
        dict['activity_ocurred']=datetime.datetime.utcnow().isoformat()
        dict['activity']=type
        dict['harvest_sorce_url']=harvest_object.source.url
        dict['harvest_source_title']=harvest_object.source.title
        dict['harvested_guid']=harvest_object.guid
        dict['excluded_resources']=excluded_resources
        return dict


    def append_provenance_data(self, package_dict, harvest_object, type, excluded_resources):
        for dict in package_dict['extras']:
            if(dict['key']=='metadata_provenance'):
                data_dict=json.loads(dict['value'])
                data_dict.append(self.get_metadata_provenance_for_just_this_harvest(harvest_object, type, excluded_resources))
                dict['value']=json.dumps(data_dict)

        return package_dict


    def import_stage(self,harvest_object):
        log.debug('In DCATHarvester import_stage')
        if not harvest_object:
            log.error('No harvest object received')
            return False

        if self.force_import:
            status = 'change'
        else:
            status = self._get_object_extra(harvest_object, 'status')

        if status == 'delete':
            # Delete package
            context = {'model': model, 'session': model.Session, 'user': self._get_user_name()}

            p.toolkit.get_action('package_delete')(context, {'id': harvest_object.package_id})
            log.info('Deleted package {0} with guid {1}'.format(harvest_object.package_id, harvest_object.guid))

            return True


        if harvest_object.content is None:
            self._save_object_error('Empty content for object %s' % harvest_object.id,harvest_object,'Import')
            return False

        # Get the last harvested object (if any)
        previous_object = model.Session.query(HarvestObject) \
                          .filter(HarvestObject.guid==harvest_object.guid) \
                          .filter(HarvestObject.current==True) \
                          .first()

        # Flag previous object as not current anymore
        if previous_object and not self.force_import:
            previous_object.current = False
            previous_object.add()


        package_dict, dcat_dict = self._get_package_dict(harvest_object)



        if not package_dict:
            return False

        if not package_dict.get('name'):
            package_dict['name'] = self._get_package_name(harvest_object, package_dict['title'])

        # Allow custom harvesters to modify the package dict before creating
        # or updating the package
        package_dict = self.modify_package_dict(package_dict,
                                                dcat_dict,
                                               harvest_object)

        # Unless already set by an extension, get the owner organization (if any)
        # from the harvest source dataset
        if not package_dict.get('owner_org'):
            source_dataset = model.Package.get(harvest_object.source.id)
            if source_dataset.owner_org:
                package_dict['owner_org'] = source_dataset.owner_org

        # Flag this object as the current one
        harvest_object.current = True
        harvest_object.add()

        context = {
            'user': self._get_user_name(),
            'return_id_only': True,
            'ignore_auth': True,
        }

        if status == 'new':

            '''
            This code checks if a resource in the package_dict already exists, if so, the resource is removed from the
            package_dict. If all resources are removed from the dict, the whole dataset already exists, and will
            therefore not be imported. If parts of the dataset does not exist, a new dataset, with the new resources
            will be created.
            '''
            dropped=''
            excluded_resources=[]
            for res in package_dict["resources"]:

                if(self.check_resource_existence(res["url"])):
                    dropped+=res['url']+' '
                    excluded_resources.append(res["url"])
                    package_dict["resources"].remove(res)
            if(not package_dict["resources"]):#If list of resources is empty
                log.info('Dataset with ID '+harvest_object.guid+' and resource'+dropped+' not created, resources already exists')
            else:
                self.append_provenance_data(package_dict,harvest_object,"initial_harvest", excluded_resources)#Adding provenance data to dataset

                package_schema = logic.schema.default_create_package_schema()
                context['schema'] = package_schema

                # We need to explicitly provide a package ID
                package_dict['id'] = unicode(uuid.uuid4())
                package_schema['id'] = [unicode]

                # Save reference to the package on the object
                harvest_object.package_id = package_dict['id']
                harvest_object.add()

                # Defer constraints and flush so the dataset can be indexed with
                # the harvest object id (on the after_show hook from the harvester
                # plugin)
                model.Session.execute('SET CONSTRAINTS harvest_object_package_id_fkey DEFERRED')
                model.Session.flush()

                package_id = p.toolkit.get_action('package_create')(context, package_dict)
                log.info('Created dataset with id %s', package_id)
        elif status == 'change':

            try:

                #This part adds old provenance data to the new package_dict
                provenance_data=""
                #print(logic.action.get.package_show({'model': model, 'user': self._get_user_name()}, {"id":harvest_object.package_id})["extras"])
                database_package=logic.action.get.package_show({'model': model, 'user': self._get_user_name()}, {"id":harvest_object.package_id})
                provenance_data=''
                for key in database_package.get('extras', []):
                    if(key['key']=="metadata_provenance"):
                        provenance_data=key['value']

                provenance_dict=json.loads(provenance_data)

                
                new_exclude=[]
                for res in package_dict.get('resources',[]): #This part ckecks if a resource has been excluded, then it should not be updated into the dataset
                    if((res['url'] in provenance_dict[0]['excluded_resources']) and (self.check_resource_existence(res["url"]))):
                        package_dict['resources'].remove(res)
                        new_exclude.append(res["url"])

                for key in package_dict.get('extras',[]):
                    if(key['key']=='metadata_provenance'):
                        key['value']=(provenance_data)

                self.append_provenance_data(package_dict, harvest_object, "reharvest",new_exclude)  # Adding new provenance data to dataset

                #Update the package
                package_dict['id'] = harvest_object.package_id
                package_id = p.toolkit.get_action('package_update')(context, package_dict)
                log.info('Updated dataset with id %s', package_id)
            except: #If package does not exist, the reason is that it was skipped in an earlier harvest. We try to make a new package where it is tested if it still needs to be skipped
                log.info("Package not updated. Thries to create a new package instead.")

                dropped = ''
                excluded_resources = []
                for res in package_dict["resources"]:

                    if (self.check_resource_existence(res["url"])):
                        dropped += res['url'] + ' '
                        excluded_resources.append(res["url"])
                        package_dict["resources"].remove(res)
                if (not package_dict["resources"]):  # If list of resources is empty
                    log.info(
                        'Dataset with ID ' + harvest_object.guid + ' and resource' + dropped + ' not created, resources already exists')
                else:
                    self.append_provenance_data(package_dict, harvest_object, "initial_harvest",
                                                excluded_resources)  # Adding provenance data to dataset

                    package_schema = logic.schema.default_create_package_schema()
                    context['schema'] = package_schema

                    # We need to explicitly provide a package ID
                    package_dict['id'] = unicode(uuid.uuid4())
                    package_schema['id'] = [unicode]

                    # Save reference to the package on the object
                    harvest_object.package_id = package_dict['id']
                    harvest_object.add()

                    # Defer constraints and flush so the dataset can be indexed with
                    # the harvest object id (on the after_show hook from the harvester
                    # plugin)
                    model.Session.execute('SET CONSTRAINTS harvest_object_package_id_fkey DEFERRED')
                    model.Session.flush()

                    package_id = p.toolkit.get_action('package_create')(context, package_dict)
                    log.info('Created dataset with id %s', package_id)


        model.Session.commit()


        return True
