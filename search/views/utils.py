import geopy
from geopy import distance
import pytz
import humanized_opening_hours
from math import sin, cos, atan2, degrees
from goose import settings
import overpass
from collections import OrderedDict
import requests
import io
import logging
from uuid import uuid4
from django.utils.html import escape

geolocator = geopy.geocoders.Nominatim(timeout=10)
debug_logger = logging.getLogger("DEBUG")

def try_geolocator_reverse(coords):
    """
        Tries many times to get a geolocator object from coordinates,
        or None.
    """
    attempts = 0
    while attempts < settings.GOOSE_META["max_geolocation_attempts"]:
        try:
            position = geolocator.reverse(
                coords, language="fr"
            )
            return position
            break
        except geopy.exc.GeopyError as e:
            attempts += 1
            if attempts == settings.GOOSE_META["max_geolocation_attempts"]:
                debug_logger.error(
                    "Too much geopy errors ({}). Aborting.".format(str(e))
                )
                return None

def try_geolocator_geocode(address):
    """
        Tries many times to get a geolocator object from an address,
        or None.
    """
    attempts = 0
    while attempts < settings.GOOSE_META["max_geolocation_attempts"]:
        try:
            position = geolocator.geocode(
                address, language="fr"
            )
            return position
            break
        except geopy.exc.GeopyError as e:
            attempts += 1
            if attempts == settings.GOOSE_META["max_geolocation_attempts"]:
                debug_logger.error(
                    "Too much geopy errors ({}). Aborting.".format(str(e))
                )
                return None

def get_address(coords=None, address=None, skip_gov_api=False):
    """
        Returns a tuple from a tuple of coordinates or an adress (str).
        
        Will first try to use the french government's API, then the
        Overpass one, except if skip_gov_api is set to True.
        
        Returned tuple : ((lat (float), lon (float)), address (str))
    """
    if (not coords and not address) or (coords and address):
        raise ValueError("One (and only one) of the two params must be given.")
    result = None
    if skip_gov_api is False:
        if coords:
            lat, lon = coords[0], coords[1]
            r = requests.get(
                "https://api-adresse.data.gouv.fr/reverse",
                params={'lat': lat, 'lon': lon}
            ).json()
        else:
            r = requests.get(
                "https://api-adresse.data.gouv.fr/search",
                params={'q': address}
            ).json()
        result = r.get("features")
    if result:
        result_lat, result_lon = (
            result[0]["geometry"]['coordinates'][1],
            result[0]["geometry"]['coordinates'][0]
        )
        # TODO : Improve label.
        result_address = result[0]["properties"]["label"]
    else:
        if coords:
            r = try_geolocator_reverse(coords)
            if not r:
                return None
        else:
            r = try_geolocator_geocode(user_address)
            if not r:
                return None
        result_lat, result_lon = r.latitude, r.longitude
        result_address = r.address.split(',')[:5]
    return ((result_lat, result_lon), result_address)

def get_bearing(coords1, coords2):
    """
        Returns the direction to go from one set of coordinates to another.
    """
    lat1, lon1 = coords1[0], coords1[1]
    lat2, lon2 = coords2[0], coords2[1]
    bearing = atan2(sin(lon2-lon1)*cos(lat2),
        cos(lat1)*sin(lat2)-sin(lat1)*cos(lat2)*cos(lon2-lon1))
    bearing = degrees(bearing)
    bearing = (bearing + 360) % 360
    return round(bearing, 1)

def deg2dir(deg):
    """
        Returns a cardinal direction from a direction (in degrees).
        https://gist.github.com/RobertSudwarts/acf8df23a16afdb5837f
    """
    dirs = ["N ↑", "NE ↗", "E →", "SE ↘", "S ↓", "SO ↙", "O ←", "NO ↖"]
    ix = int((deg + 22.5)/45)
    return dirs[ix % 8]

def get_results(search_preset, user_coords, radius, no_private):
    """
        Returns a list of dicts with the properties of all results.
    """
    debug_logger.debug(
        "Getting results. SearchPreset: {}.".format(search_preset.id)
    )
    api = overpass.API()
    response = []
    results = []
    for line in search_preset.osm_keys.splitlines():
        # Requests both nodes and ways.
        request = (
            '(node[{osm_key}](around:{r},{lat},{lon});'
            'way[{osm_key}](around:{r},{lat},{lon}););'
        ).format(
            osm_key=line, r=radius,
            lat=user_coords[0], lon=user_coords[1]
        )
        attempts = 0
        debug_logger.debug("Requesting '{}'".format(line))
        while attempts < settings.GOOSE_META["max_geolocation_attempts"]:
            try:
                response += api.Get(request)['features']
                debug_logger.debug("Request successfull.")
                break
            except overpass.OverpassError as e:
                attempts += 1
                if attempts == settings.GOOSE_META["max_geolocation_attempts"]:
                    debug_logger.debug(
                        "Error: {}. Raising of 500 error.".format(str(e))
                    )
                    raise e
    for element in response:
        if no_private and element["properties"].get("access") in ["private", "no"]:
            continue
        results.append(Result(str(uuid4()), element, search_preset, user_coords))
    results = sorted(results, key=lambda result: result.distance)
    debug_logger.debug("Got {} result(s).".format(len(results)))
    return results

def render_tag_filter(tags, count):
    """
        Returns a raw HTML form allowing to filter results (uses JS)
        from a dict of tags and the total number of results.
    """
    html = """\
    <div class="panel panel-default">
        <div class="panel-heading" role="tab" id="headingTwo">
            <h4 class="panel-title">
                <a class="collapsed" role="button" data-toggle="collapse" data-parent="#accordion" href="#collapseTwo" aria-expanded="false" aria-controls="collapseTwo">
                        <center>Filtrer les résultats <span class="badge">{count}</span></center>
                </a>
            </h4>
        </div>
        <div id="collapseTwo" class="panel-collapse collapse" role="tabpanel" aria-labelledby="headingTwo">
            <div class="panel-body">
                {content}
            </div>
        </div>
    </div>
    """
    output = ""
    # TODO : Make it cleaner.
    tag_names = OrderedDict()
    tag_names["open"] = "Ouvert"
    tag_names["closed"] = "Fermé"
    tag_names["unknown_schedules"] = "Horaires inconnues"
    tag_names["vegetarian:yes"] = "Menu végétarien"
    tag_names["vegetarian:only"] = "Entièrement végétarien"
    tag_names["vegetarian:no"] = "Non végétarien"
    tag_names["vegetarian:unknown"] = "Statut végétarien inconnu"
    tag_names["vegan:yes"] = "Menu végétalien"
    tag_names["vegan:only"] = "Entièrement végétalien"
    tag_names["vegan:no"] = "Non végétalien"
    tag_names["vegan:unknown"] = "Statut végétalien inconnu"
    tag_names["wheelchair:yes"] = "Accessible aux fauteuils roulants"
    tag_names["wheelchair:limited"] = "Accès limité aux fauteuils roulants"
    tag_names["wheelchair:no"] = "Non accessible aux fauteuils roulants"
    tag_names["wheelchair:unknown"] = "Statut des fauteuils roulants inconnu"
    for tag in tag_names:
        if tag in tags:
            n = tags[tag]
            output += (
                '<input type="checkbox" checked '
                'onchange="filter_results_handler(this)" '
                'name="result_filter" id="filter_{tag}" value="{tag}">'
                '<label for="filter_{tag}"> {label} <span class="badge">'
                '{count}</span></label><br/>\n'
            ).format(
                tag=tag, label=tag_names[tag], count=tags[tag]
            )
    return html.format(count=count, content=output)

def get_all_tags(results):
    """
        Returns a dict of all tags and their occurences from a list
        of results.
    """
    tags_count = {}
    for result in results:
        result_tags = result.get_tags()
        for tag in result_tags:
            if tag in tags_count.keys():
                tags_count[tag] += 1
            else:
                tags_count[tag] = 1
    return tags_count

def get_all_addresses(results):
    """
        Fills the addresses of the given results (list).
        
        Tries first with the french government's API, then with the
        Overpass one for the addresses which couldn't be obtained.
        
        API doc : https://adresse.data.gouv.fr/api
    """
    # Creates a CSV to request the API.
    debug_logger.debug("Getting addresses of results.")
    debug_logger.debug(results)
    csv = "latitude,longitude,uuid\n"
    for result in results:
        if result.default_address is '':
            csv += str(result.coordinates[0]) + ',' + str(result.coordinates[1]) + ',' + result.uuid + '\n'
    debug_logger.debug("CSV created.")
    debug_logger.debug("Content:\n" + csv)
    fake_file = io.StringIO(csv)
    files = {'file': fake_file}
    r = requests.post(
        "https://api-adresse.data.gouv.fr/reverse/csv/",
        files={'data': fake_file}
    )
    debug_logger.debug(
        "Request sent. API returned {} status code. URL: {}".format(
            r.status_code, r.url
        )
    )
    debug_logger.debug('\n' + r.text)
    for csv_line in r.text.splitlines()[1:]:
        parsed_line = csv_line.split(',')
        current_uuid = str(parsed_line[2])
        for result in results:
            if result.uuid != current_uuid:
                continue
            address_data = [
                parsed_line[9],
                parsed_line[10],
                parsed_line[12],
                parsed_line[13]
            ]
            # Checks address_data contains at least one information,
            # and / including the street name.
            if any(address_data) and address_data[1]:
                debug_logger.debug(
                    "The address from '{}' is correct (OSM_ID: {}).".format(
                        csv_line,
                        result.osm_meta[1]
                    )
                )
                address = "Adresse estimée : {housenumber} {street}, {postcode} {city}".format(
                    housenumber=address_data[0],
                    street=address_data[1],
                    postcode=address_data[2],
                    city=address_data[3]
                )
            else:  # If the address is not in France (or in case of error).
                debug_logger.debug(
                    "One or more informations are missing for the address '{}' (OSM_ID: {}).".format(
                        csv_line,
                        result.osm_meta[1]
                    )
                )
                address = get_address(
                    coords=(result.coordinates[0], result.coordinates[1]),
                    skip_gov_api=True
                )
                if not address:
                    debug_logger.error(
                        "The address of result could not be obtained. (OSM_ID: {}).".format(
                            result.osm_meta[1]
                        )
                    )
                else:
                    address = address[1]
                    address = "Adresse estimée : {housenumber} {street}, {postcode} {city}".format(
                        housenumber=address[0],
                        street=address[1],
                        postcode=address[2],
                        city=address[3]
                    )
            result.string_address = address
    debug_logger.debug("Address getting finished successfully.")
    return

class Result:
    """
        A result and its properties.
    """
    def __init__(self, uuid, geojson, search_preset, user_coordinates):
        self.uuid = uuid
        if geojson['geometry']['type'] == "Point":
            self.osm_meta = ("node", geojson["id"])
            self.coordinates = (
                geojson["geometry"]["coordinates"][1],
                geojson["geometry"]["coordinates"][0]
            )
        else:  # Should be "LineString".
            self.osm_meta = ("way", geojson["id"])
            self.coordinates = (
                geojson["geometry"]["coordinates"][0][1],
                geojson["geometry"]["coordinates"][0][0]
            )
        self.user_coords = user_coordinates
        self.search_preset = search_preset
        self.properties = geojson["properties"]
        self.default_address = self.get_default_address()
        self.string_address = ""
        self.distance = round(distance.vincenty(
            (user_coordinates[0], user_coordinates[1]), self.coordinates
        ).m)
        self.bearing = get_bearing(user_coordinates, self.coordinates)
        self.direction = deg2dir(self.bearing)
        # TODO : Make it independent to timezones ?
        oh_field = escape(self.properties.get("opening_hours"))
        self.opening_hours = None
        if oh_field:
            try:
                self.opening_hours = humanized_opening_hours.HumanizedOpeningHours(
                    oh_field, "fr", tz=pytz.timezone("Europe/Paris")
                )
            except humanized_opening_hours.HOHError:
                # TODO : Warn user ?
                debug_logger.error(
                    "Opening hours - HOHError ; OSM_ID: '{id}' ; opening_hours: '{oh}'".format(
                        id=self.osm_meta[1],
                        oh=oh_field
                    )
                )
                self.opening_hours = None
            except Exception as e:
                # TODO : Warn user ?
                debug_logger.error(
                    "Opening hours - Error ; Exception: '{exception}' ; OSM_ID: '{id}' ; opening_hours: '{oh}'".format(
                        exception=str(e),
                        id=self.osm_meta[1],
                        oh=oh_field
                    )
                )
                self.opening_hours = None
        self.tags = []
        return
    
    def get_address(self):
        if self.default_address:
            return self.default_address
        elif self.string_address:
            return self.string_address
        else:
            debug_logger.error(
                "Getting address - Error ; OSM_ID: '{id}' ; Coordinates: {lat}/{lon}".format(
                    id=self.osm_meta[1],
                    lat=self.coordinates[0],
                    lon=self.coordinates[1]
                )
            )
            return "Adresse : Adresse inconnue"
    
    def get_default_address(self):
        address_data = {
            "street": self.properties.get("addr:street"),
            "housenumber": self.properties.get("addr:housenumber"),
            "city": self.properties.get("addr:city"),
            "postcode": self.properties.get("addr:postcode")
        }
        if all(address_data.values()):
            return "Adresse exacte : {}, {}, {} {}".format(
                escape(address_data["housenumber"]),
                escape(address_data["street"]),
                escape(address_data["postcode"]),
                escape(address_data["city"])
            )
        elif address_data["housenumber"] and address_data["street"]:
            return "Adresse exacte : {}, {}".format(
                escape(address_data["housenumber"]),
                escape(address_data["street"])
            )
        else:
            return ''
    
    def get_tags(self):
        """
            Returns a list of all tags present in the result.
        """
        tags = []
        # Opening hours.
        if self.opening_hours is not None:
            if self.opening_hours.is_open():
                tags.append("open")
            else:
                tags.append("closed")
        else:
            tags.append("unknown_schedules")
        # Diet.
        diet = self.properties.get("diet:vegetarian")
        if diet:
            if diet == "yes":
                tags.append("vegetarian:yes")
            elif diet == "only":
                tags.append("vegetarian:only")
            else:
                tags.append("vegetarian:no")
        else:
            tags.append("vegetarian:unknown")
        diet = self.properties.get("diet:vegan")
        if diet:
            if diet == "yes":
                tags.append("vegan:yes")
            elif diet == "only":
                tags.append("vegan:only")
            else:
                tags.append("vegetarian:no")
        else:
            tags.append("vegan:unknown")
        # Wheelchairs.
        wc = self.properties.get("wheelchair")
        if wc:
            if wc == "yes":
                tags.append("wheelchair:yes")
            elif wc == "limited":
                tags.append("wheelchair:limited")
            elif wc == "no":
                tags.append("wheelchair:no")
        else:
            tags.append("wheelchair:unknown")
        self.tags = tags
        return tags
    
    def render(self, render_tags=True, link_to_osm=True, opening_hours=True, oh_in_popover=True, itinerary=True):
        """
            Returns an HTML div (with "result-box" class) displaying
            a result and its properties.
        """
        html = '<div role="article" class="result-box">{}</div>'
        content = ""
        data = []
        name = self.properties.get("name")
        if name:
            data.append("Nom : {}\n".format(escape(name)))
        if self.opening_hours is not None:
            if self.opening_hours.is_open():
                data.append("<b>Ouvert</b>\n")
            else:
                data.append("<b>Fermé</b>\n")
        data.append("Distance : {distance} mètres".format(distance=self.distance))
        data.append("Direction : {degrees}° {direction}\n".format(
            degrees=self.bearing, direction=self.direction
        ))
        
        phone = self.properties.get("phone")
        if phone:
            data.append(
                (
                    '<span class="glyphicon glyphicon-phone-alt '
                    'inline-icon" aria-hidden="true"></span>Téléphone : '
                    '<a href="tel:{phone}">{phone}</a>\n'
                ).format(phone=escape(phone))
            )
        
        data.append(self.get_address())
        
        result_properties = self.search_preset.render_pr(self.properties)
        
        try:
            if opening_hours and self.opening_hours is not None:
                opening_hours_text = self.opening_hours.stringify_week_schedules()
                if oh_in_popover:
                    oh_content = (
                        '<button type="button" class="btn btn-default"'
                        ' data-toggle="popover" title="Horaires d\'ouverture"'
                        ' data-content="{}" data-html="true"'
                        ' data-placement="right">'
                        '<span class="glyphicon glyphicon-time inline-icon"'
                        ' aria-hidden="true"></span>Horaires d\'ouverture</button>'
                    ).format(opening_hours_text.replace("\n", "<br>"))
                else:
                    oh_content = (
                        '<div class="small-box">{}</div>'
                    ).format(opening_hours_text.replace("\n", "<br>"))
                data.append('\n' + oh_content)
        except Exception as e:
            debug_logger.error(
                "Error of HOH ({}) on rendering opening hours of the result (OSM_ID: {}).".format(
                    str(e), self.osm_meta[1]
                )
            )
        
        data.append('\n' + result_properties)
        debug_logger.debug(data)
        # Removes unusefull linebreaks.
        data = [output_data for output_data in data if output_data is not '\n']
        content += '\n'.join(data)
        
        if itinerary:
            itinerary_url = (
                'https://www.openstreetmap.org/directions?'
                'engine=graphhopper_foot&route={},{};{},{}'
            ).format(
                self.user_coords[0], self.user_coords[1],
                self.coordinates[0], self.coordinates[1]
            )
            itinerary_link = (
                '<a href="{}"><span class="glyphicon glyphicon-road'
                ' inline-icon" aria-hidden="true"></span>Itinéraire jusqu\'à ce'
                ' point</a>'
            ).format(itinerary_url)
            content += '\n\n' + itinerary_link
        
        if link_to_osm:
            osm_link = "http://www.openstreetmap.org/{}/{}".format(
                self.osm_meta[0],
                self.osm_meta[1]
            )
            content = (
                '<a href="{}"><img class="osm-link-logo" '
                'src="/static/images/osm_logo.png"></a>'
            ).format(osm_link) + content
        
        if render_tags:
            tags_list = ';'.join(self.tags)
            result_tags = (
                '<span class="result_tags" style="visibility:hidden">{tags}</span>'
            ).format(
                tags=tags_list
            )
            content += result_tags
        
        return html.format(content)
    
    def __str__(self):
        return "<result ({coords}) {distance}m>".format(
            coords=self.coordinates, distance=self.distance
        )
    
    def __repr__(self):
        return self.__str__()
