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

        ckan.plugins = dcat dcat_rdf_harvester dcat_json_harvester dcat_json_interface geonorgeHarvester

## How to harvest data
