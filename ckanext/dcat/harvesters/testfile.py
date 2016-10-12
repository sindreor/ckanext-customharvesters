import json
import urllib
url='https://kartkatalog.geonorge.no/api/search?text=kystverket'
content=urllib.urlopen(url).read()

def _get_guids_and_datasets(content):
    # Todo: Test that this works before using it in other methods!!
    doc = json.loads(content)
    datasets = doc["Results"]
    for dataset in datasets:
        guid = "GEONORGE:" + dataset.get("Uuid")
        as_string = json.dumps(dataset)
        yield guid, as_string

for guid, as_string in _get_guids_and_datasets(content):
    print(guid)
    print(as_string)