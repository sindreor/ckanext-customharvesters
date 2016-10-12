import logging

log = logging.getLogger(__name__)


def dcat_to_ckan(dcat_dict):

    package_dict = {}

    package_dict['title'] = dcat_dict.get('title')
    #package_dict['notes'] = dcat_dict.get('description')
    # Modification from here_____________________
    for description in dcat_dict.get('description', []):
        package_dict['notes'] = description.get('value')
        # Modification ends_________________________

    package_dict['url'] = dcat_dict.get('landingPage')


    package_dict['tags'] = []
    for keyword in dcat_dict.get('keyword', []):
        #Modification_______________________________
        tag = ''
        validationstring = '._-'
        for letter in keyword:
            if (letter.isalnum() or letter in validationstring):
                tag += letter
            elif (letter == ' '):
                tag += '_'
        package_dict['tags'].append({'name': tag})
        #____________________________________________
    package_dict['extras'] = []
    for key in ['issued', 'modified']:
        package_dict['extras'].append({'key': 'dcat_{0}'.format(key), 'value': dcat_dict.get(key)})

    package_dict['extras'].append({'key': 'guid', 'value': dcat_dict.get('id')})#Changed from 'identifier' to 'id'

    dcat_publisher = dcat_dict.get('publisher')
    if isinstance(dcat_publisher, basestring):
        package_dict['extras'].append({'key': 'dcat_publisher_name', 'value': dcat_publisher})
    elif isinstance(dcat_publisher, dict) and dcat_publisher.get('name'):
        package_dict['extras'].append({'key': 'dcat_publisher_name', 'value': dcat_publisher.get('name')})
        package_dict['extras'].append({'key': 'dcat_publisher_email', 'value': dcat_publisher.get('mbox')})

    package_dict['extras'].append({
        'key': 'language',
        'value': ','.join(dcat_dict.get('language', []))
    })


    package_dict['resources'] = []
    for distribution in dcat_dict.get('distribution', []):
        resource = {
            'name': distribution.get('title'),
            #Modification from here_____________________
            #'description': distribution.get('description'),
            #Modification end___________________________
            'url': distribution.get('downloadURL') or distribution.get('accessURL'),
            'format': distribution.get('format'),
        }
        # Modification from here______________________________
        # for description in distribution.get('description', []):
        #   resource['description'] = description.get('value')
        # Modification ends__________________________________

        if distribution.get('byteSize'):
            try:
                resource['size'] = int(distribution.get('byteSize'))
            except ValueError:
                pass
        package_dict['resources'].append(resource)
    package_dict["extras"].append({'key':'metadata_provenance', 'value':"[]"})
    return package_dict

def geonorge_to_CKANpackage(json_dict):
    package_dict={}
    package_dict['title']=json_dict['Title']
    package_dict['notes']=json_dict['Abstract']
    package_dict['url']=json_dict['ShowDetailsUrl']
    package_dict['tags']=[]
    package_dict['tags'].append({'name':json_dict['Theme']})
    package_dict['extras']=[]
    package_dict['extras'].append({'key': 'Organisasjon', 'value': json_dict['Organization']})
    package_dict['extras'].append({'key': 'Nettside til organisasjon', 'value': json_dict['OrganizationUrl']})
    package_dict['extras'].append({'key': 'Type', 'value': json_dict['Type']})
    package_dict['resources']=[]
    try:
        resource={
            'name':json_dict['Title'],
            'description': json_dict['Abstract'],
            'url': json_dict['DistributionUrl'],
            'format': json_dict['Type']
             }
        package_dict['resources'].append(resource)
    except:
        log.debug('The dataset has no resources, added only as reference to geonorge.no')
    package_dict["extras"].append({'key': 'metadata_provenance', 'value': "[]"})
    return package_dict

def ckan_to_dcat(package_dict):

    dcat_dict = {}

    dcat_dict['title'] = package_dict.get('title')
    dcat_dict['description'] = package_dict.get('notes')
    dcat_dict['landingPage'] = package_dict.get('url')


    dcat_dict['keyword'] = []
    for tag in package_dict.get('tags', []):
        dcat_dict['keyword'].append(tag['name'])


    dcat_dict['publisher'] = {}

    for extra in package_dict.get('extras', []):
        if extra['key'] in ['dcat_issued', 'dcat_modified']:
            dcat_dict[extra['key'].replace('dcat_', '')] = extra['value']

        elif extra['key'] == 'language':
            dcat_dict['language'] = extra['value'].split(',')

        elif extra['key'] == 'dcat_publisher_name':
            dcat_dict['publisher']['name'] = extra['value']

        elif extra['key'] == 'dcat_publisher_email':
            dcat_dict['publisher']['mbox'] = extra['value']

        elif extra['key'] == 'guid':
            dcat_dict['identifier'] = extra['value']

    if not dcat_dict['publisher'].get('name') and package_dict.get('maintainer'):
        dcat_dict['publisher']['name'] = package_dict.get('maintainer')
        if package_dict.get('maintainer_email'):
            dcat_dict['publisher']['mbox'] = package_dict.get('maintainer_email')

    dcat_dict['distribution'] = []
    for resource in package_dict.get('resources', []):
        distribution = {
            'title': resource.get('name'),
            'description': resource.get('description'),
            'format': resource.get('format'),
            'byteSize': resource.get('size'),
            # TODO: downloadURL or accessURL depending on resource type?
            'accessURL': resource.get('url'),
        }
        dcat_dict['distribution'].append(distribution)

    return dcat_dict
