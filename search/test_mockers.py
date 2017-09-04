from faker import Faker
import random
fake = Faker("fr_FR")

class FakeGeolocatorObject:
    def __init__(self, coords, address):
        self.latitude = coords[0]
        self.longitude = coords[1]
        self.address = address
        return

def geolocator_object(address=None, coords=None):
    if not address:
        address = fake.address().replace('\n', ', ')
    if not coords:
        coords=(float(fake.longitude()), float(fake.latitude()))
    return FakeGeolocatorObject(coords, address)

def gouv_api_address(coords, address):
    if not coords:
        coords = [float(fake.longitude()), float(fake.latitude())]
    if not address:
        address = fake.address().replace('\n', ', ')
    return [{
        "geometry":
            {
                "type": "Point",
                "coordinates": [coords[1], coords[0]]
            },
        "type": "Feature",
        "properties":
            {
                "distance": random.randint(0, 300),
                "postcode": fake.postcode(),
                "housenumber": fake.building_number(),
                "label": address,
                "city": fake.city()
            }
    }]

def gouv_api_csv(csv):
    output_csv = ''
    for line in csv.splitlines()[1:]:
        output_csv += line
        # Always fills the data of the result used for tests.
        if bool(random.getrandbits(1)) or "-21.9419851,64.14602" in line: #"64,1460200,-21,9419851" in line:
            output_csv += ',' + ','.join([
                str(fake.latitude()),  # "result_latitude"
                str(fake.longitude()),  # "result_longitude"
                fake.address().replace('\n', ' ').replace(',', ' '),  # "result_label"
                str(random.randint(0, 300)),  # "result_distance"
                "housenumber",  # "result_type"
                "44109_XXXX_984eec",  # "result_id"
                fake.building_number(),  # "result_housenumber"
                fake.street_name(),  # "result_name", the name of the street.
                '',  # "result_street", empty in most case.
                fake.postcode(),  # "result_postcode"
                fake.city(),  # "result_city"
                '"' + fake.postcode()[:2] + ' ' + fake.department()[1] + ', ' + fake.region() + '"',  # "result_context"
                fake.postcode()[:2] + str(random.randint(100, 300)),  # "result_citycode"
            ])
        else:
            output_csv += ',,,,,,,,,,,,,'
        output_csv += '\n'
    return output_csv

def result_properties():
    properties = {}
    properties["access"] = "yes"
    if bool(random.getrandbits(1)):
        properties["name"] = fake.company()
    if bool(random.getrandbits(1)):
        properties["phone"] = fake.phone_number()
    if bool(random.getrandbits(1)):
        properties["fee"] = "yes"
    elif bool(random.getrandbits(1)):
        properties["fee"] = "no"
    if bool(random.getrandbits(1)):
        properties["opening_hours"] = "Mo-Su 09:00-19:00"
    elif bool(random.getrandbits(1)):
        properties["opening_hours"] = "Mo-Th 12:30-16:30"
    return properties

def geojsons():
    results = []
    for i in range(8):
        properties = result_properties()
        result = {
            "id": random.randint(1, 10000),
            "geometry": {
                "type": "Point",
                "coordinates": [
                    float(fake.latitude()),
                    float(fake.longitude())
                ]
            },
            "properties": properties
        }
        results.append(result)
    # Appends a constant result for tests.
    results.append({
        "id": 1337,
        "geometry": {
            "type": "Point",
            "coordinates": [64.1460200, -21.9419851]
        },
        "properties": {
            "name": "City Hall of Reykjavik",
            "opening_hours": "Mo-Fr 08:00-19:00",
            "wheelchair": "yes",
            "phone": "+354 411 1111"
        }
    })
    return results
