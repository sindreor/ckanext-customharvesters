# ckanext-customharvesters


This extension is a modification of the already existing extension that can be found here [https://github.com/ckan/ckanext-dcat](https://github.com/ckan/ckanext-dcat). The extension provides functionality for logging data about harvest activity done on each dataset, and functionality that checks if the dataset already exists based on its resources. It alse extends the original extension by adding two custom harvesters which are adapted for harvesting data from [http://data.norge.no](http://data.norge.no)and [http://geonorge.no](http://geonorge.no).


## Contents

- [Overview](#overview)
- [Installation](#installation)
- [How to harvest data](#how-to-harvest-data)



## Installation

1.  Install ckanext-harvest ([https://github.com/ckan/ckanext-harvest#installation](https://github.com/ckan/ckanext-harvest#installation)) (Only if you want to use the RDF harvester)

2.  Install the extension on your virtualenv:

        (pyenv) $ pip install -e git+https://github.com/sindreor/ckanext-customharvesters.git#egg=ckanext-customharvesters

3.  Install the extension requirements:

        (pyenv) $ pip install -r ckanext-customharvesters/requirements.txt

4.  Enable the required plugins in your ini file:

        ckan.plugins = dcat dcat_rdf_harvester dcat_json_harvester dcat_json_interface geonorgeHarvester datanorgeHarvester

5. Restart apache:
	   sudo service apache2 restart

## How to harvest data

First you need to create a harvest source which is using one of the harvesters from this extension. This can be done at http://yourIP/harvest. 

After the harvest source is created, you need to create a harvest job. This is done by clicking at the created harvest source, and then choosing "reharvest"

When a harvest job is started by a user in the Web UI, or by a scheduled
harvest, the harvest is started by the ``harvester run`` command. This is the
normal method in production systems and scales well.

In this case, the harvesting extension uses two different queues: one that
handles the gathering and another one that handles the fetching and importing.
To start the consumers run the following command (make sure you have your
python environment activated)::

      (pyenv) $ paster --plugin=ckanext-harvest harvester gather_consumer --config=/etc/ckan/default/production.ini

On another terminal, run the following command::

      (pyenv) $ paster --plugin=ckanext-harvest harvester fetch_consumer --config=/etc/ckan/default/production.ini

Finally, on a third console, run the following command to start any
pending harvesting jobs::

      (pyenv) $ paster --plugin=ckanext-harvest harvester run --config=/etc/ckan/default/production.ini
