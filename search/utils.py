import geopy
from geopy import distance
import pytz
import humanized_opening_hours
from math import sin, cos, atan2, degrees
from goose import settings
import overpass
from collections import namedtuple, Counter, OrderedDict
import requests
import io
import logging
from uuid import uuid4
from django.utils.html import escape
from django.template.loader import render_to_string
from goose import settings
from search import test_mockers
from django.utils.translation import ugettext as _
from django.utils.translation import get_language

geolocator = geopy.geocoders.Nominatim(timeout=10)
debug_logger = logging.getLogger("DEBUG")

def try_geolocator_reverse(coords):
    """
        Tries many times to get a geolocator object from coordinates,
        or None.
    """
    if settings.TESTING:
        return test_mockers.geolocator_object(coords=coords)
    attempts = 0
    while attempts < settings.GOOSE_META["max_geolocation_attempts"]:
        try:
            position = geolocator.reverse(
                coords, language=get_language().split('-')[0]
            )
            return position
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
    if settings.TESTING:
        return test_mockers.geolocator_object(address=address)
    attempts = 0
    while attempts < settings.GOOSE_META["max_geolocation_attempts"]:
        try:
            position = geolocator.geocode(
                address, language=get_language().split('-')[0]
            )
            return position
        except geopy.exc.GeopyError as e:
            attempts += 1
            if attempts == settings.GOOSE_META["max_geolocation_attempts"]:
                debug_logger.error(
                    "Too much geopy errors ({}). Aborting.".format(str(e))
                )
                return None

def get_address(coords=None, address=None, skip_gov_api=False, mocking_parameters=None):
    """
        Returns a tuple from a tuple of coordinates or an adress (str).
        
        Will first try to use the french government's API, then the
        Overpass one, except if skip_gov_api is set to True.
        
        Returned tuple : ((lat (float), lon (float)), address (str))
    """
    if mocking_parameters == "invalid_address":
        return None
    if (not coords and not address) or (coords and address):
        raise ValueError("One (and only one) of the two params must be given.")
    result = None
    if skip_gov_api is False:
        if settings.TESTING:
            result = test_mockers.gouv_api_address(coords, address)
        elif coords:
            lat, lon = coords[0], coords[1]
            r = requests.get(
                "https://api-adresse.data.gouv.fr/reverse",
                params={'lat': lat, 'lon': lon}
            ).json()
            result = r.get("features")
        else:
            r = requests.get(
                "https://api-adresse.data.gouv.fr/search",
                params={'q': address}
            ).json()
            result = r.get("features")
    result_is_valid = False
    if result:
        result_lat, result_lon = (
            # # Gets the first result, cause the API returns
            # a list of one element.
            result[0]["geometry"]['coordinates'][1],
            result[0]["geometry"]['coordinates'][0]
        )
        # TODO : Improve label.
        result_address = result[0]["properties"]["label"]
        result_is_valid = all((result_lat, result_lon, result_address))
        # Dirty patch to fix a weird problem with the API.
        try:
            housenumber = result[0]["properties"]["housenumber"]
            if len(housenumber) == 4 and housenumber.startswith('90'):
                result_is_valid = False
        except KeyError:
            pass
    if not result or not result_is_valid:
        if coords:
            r = try_geolocator_reverse(coords)
            if not r or (r.latitude == r.longitude == 0.0 and r.address == None):
                return None
        else:
            r = try_geolocator_geocode(address)
            if not r or (r.latitude == r.longitude == 0.0 and r.address == None):
                return None
        result_lat, result_lon = r.latitude, r.longitude
        result_address = ', '.join(r.address.split(',')[:5])
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

def get_permalink(request, use_get_params, search_preset_id, user_latitude, user_longitude, radius, no_private):
    permalink = request.build_absolute_uri()
    if not use_get_params:
        permalink += "?sp={}&lat={}&lon={}&radius={}&no_private={}".format(
            search_preset_id,
            user_latitude,
            user_longitude,
            radius,
            {True: '1', False: '0'}.get(no_private, False)
        )
    return permalink

def get_results(search_preset, user_coords, radius, no_private, timezone_name):
    """
        Returns a list of dicts with the properties of all results.
    """
    debug_logger.debug(
        "Getting results. SearchPreset: {}.".format(search_preset.id)
    )
    api = overpass.API()
    response = []
    results = []
    request = '('
    for line in search_preset.osm_keys.splitlines():
        # Requests both nodes and ways.
        request += (
            'node[{osm_key}](around:{r},{lat},{lon});'
            'way[{osm_key}](around:{r},{lat},{lon});'
        ).format(
            osm_key=line, r=radius,
            lat=user_coords[0], lon=user_coords[1]
        )
    request += ');'
    attempts = 0
    debug_logger.debug("Requesting '{}'".format(line))
    while attempts < settings.GOOSE_META["max_geolocation_attempts"]:
        if settings.TESTING:
            response = test_mockers.geojsons()
            break
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
        results.append(Result(str(uuid4()), element, search_preset, user_coords, timezone_name))
    results = sorted(results, key=lambda result: result.distance)
    debug_logger.debug("Got {} result(s).".format(len(results)))
    return results

def render_filter_panel(results):
    """
        Returns a raw HTML form allowing to filter results (uses JS)
        from a dict of tags and the total number of results.
    """
    tags = []
    for result in results:
        tags.extend(result.tags)
    tags = OrderedDict(sorted(Counter(tags).items(), key=lambda t: t[0][2]))
    if not tags:
        return ''
    
    Tag = namedtuple("Tag", ["slug_name", "label", "count"])
    renderable_tags = []
    for tag, count in tags.items():
        t = Tag(
            slug_name=tag[0],
            label=tag[1],
            count=count,
        )
        renderable_tags.append(t)
    
    count = len(results)
    html = render_to_string(
        "search/filter_panel.part.html",
        {
            "tags": renderable_tags,
            "count": count,
        }
    )
    return html

def parse_csv_data(result, csv_line, address_data):
    """
        Parses a line of the CSV obtained by
        the function 'get_all_addresses'.
    """
    # Checks address_data contains at least one information,
    # and / including the street name.
    # Dirty patch to fix a weird problem with the API.
    valid = True
    if len(address_data[0]) == 4 and address_data[0].startswith('90'):
        valid = False
    if all(address_data) and valid:
        debug_logger.debug(
            "The address from '{}' is full (OSM_ID: {}).".format(
                csv_line,
                result.osm_meta[1]
            )
        )
        address = _('Adresse estimée : <span itemprop="streetAddress">{housenumber} {street}</span>, <span itemprop="postalCode">{postcode}</span> <span itemprop="addressLocality">{city}</span>').format(
            housenumber=address_data[0],
            street=address_data[1],
            postcode=address_data[2],
            city=address_data[3]
        )
    elif address_data[0] and address_data[1] and valid:
        debug_logger.debug(
            "The address from '{}' is usable (but not full) (OSM_ID: {}).".format(
                csv_line,
                result.osm_meta[1]
            )
        )
        address = _('Adresse estimée : <span itemprop="streetAddress">{housenumber}, {street}</span>').format(
            housenumber=address_data[0],
            street=address_data[1]
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
        )[1]
        if not address:
            return ''
        address = _("Adresse estimée : {}").format(address)
    return address

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
    if settings.TESTING:
        csv_returned = test_mockers.gouv_api_csv(csv)
        debug_logger.debug("Mocker returned CSV.")
        debug_logger.debug('\n' + csv_returned)
        csv_returned = csv_returned.splitlines()
    else:
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
        csv_returned = r.text.splitlines()[1:]
    for csv_line in csv_returned:
        parsed_line = csv_line.split(',')
        current_uuid = parsed_line[2]
        for result in results:
            if str(result.uuid) != str(current_uuid):
                continue
            address_data = [
                parsed_line[9],
                parsed_line[10],
                parsed_line[12],
                parsed_line[13]
            ]
            result.string_address = parse_csv_data(result, csv_line, address_data)
    debug_logger.debug("Address getting finished successfully.")
    return

class Result:
    """
        A result and its properties.
    """
    def __init__(self, uuid, geojson, search_preset, user_coordinates, timezone_name):
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
        self.string_address = ''
        self.distance = round(distance.vincenty(
            (user_coordinates[0], user_coordinates[1]), self.coordinates
        ).m)
        self.bearing = get_bearing(user_coordinates, self.coordinates)
        self.direction = deg2dir(self.bearing)
        oh_field = self.properties.get("opening_hours")
        self.opening_hours = None
        lang = get_language().split('-')[0]
        if lang not in ["fr", "en"]:
            lang = "en"
        if oh_field:
            try:
                self.opening_hours = humanized_opening_hours.HumanizedOpeningHours(
                    oh_field, lang, tz=pytz.timezone(timezone_name)
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
        self.tags = self.get_tags()
        self.renderable_tags = [t[0] for t in self.tags]
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
            return _("Adresse : Adresse inconnue")
    
    def get_default_address(self):
        address_data = {
            "street": self.properties.get("addr:street"),
            "housenumber": self.properties.get("addr:housenumber"),
            "city": self.properties.get("addr:city"),
            "postcode": self.properties.get("addr:postcode")
        }
        if all(address_data.values()):
            return _('Adresse exacte : <span itemprop="streetAddress">{housenumber} {street}</span>, <span itemprop="postalCode">{postcode}</span> <span itemprop="addressLocality">{city}</span>').format(
                housenumber=escape(address_data["housenumber"]),
                street=escape(address_data["street"]),
                postcode=escape(address_data["postcode"]),
                city=escape(address_data["city"])
            )
        elif address_data["housenumber"] and address_data["street"]:
            return _('Adresse exacte : <span itemprop="streetAddress">{housenumber}, {street}</span>').format(
                housenumber=escape(address_data["housenumber"]),
                street=escape(address_data["street"])
            )
        else:
            return ''
    
    def get_tags(self):
        """
            Returns a list of all tags present in the result.
        """
        tags = []
        
        # Specific tags.
        for filter in self.search_preset.filters.all():
            tag = filter.parse_result(self)
            if tag:
                tags.append(tag)
        
        # Universal tags.
        # Uses three letters to order filters.
        ## Opening hours.
        if self.opening_hours is not None:
            if self.opening_hours.is_open():
                tags.append(("open", _("Ouvert"), 'AAA'))
            else:
                tags.append(("closed", _("Fermé"), 'AAB'))
        else:
            tags.append(("unknown_schedules", _("Horaires inconnues"), 'AAC'))
        
        ## Wheelchairs.
        wc = self.properties.get("wheelchair")
        if wc:
            if wc == "yes":
                tags.append((
                    "wheelchair_yes",
                    _("Accessible aux fauteuils roulants"),
                    'ZBA'
                ))
            elif wc == "limited":
                tags.append((
                    "wheelchair_limited",
                    _("Accès limité aux fauteuils roulants"),
                    'ZBB'
                ))
            elif wc == "no":
                tags.append((
                    "wheelchair_no",
                    _("Non accessible aux aux fauteuils roulants"),
                    'ZBC'
                ))
        else:
            tags.append((
                "wheelchair_unknown",
                _("Accessibilité aux fauteuils roulants inconnue"),
                'ZBD'
            ))
        return tags
    
    def render(self, render_tags=True, link_to_osm=True, opening_hours=True, oh_in_popover=True, itinerary=True):
        """
            Returns an HTML div (with "result-box" class) displaying
            a result and its properties.
        """
        html = '<div role="article" class="result-box">{}</div>'
        content = ''
        data = []
        name = self.properties.get("name")
        if name:
            data.append((_("Nom : {}") + '\n').format(escape(name)))
        if self.opening_hours is not None:
            if self.opening_hours.is_open():
                data.append('<b>' + _("Ouvert") + '</b>\n')
            else:
                data.append('<b>' + _("Fermé") + '</b>\n')
        data.append(_("Distance : {distance} mètres").format(distance=self.distance))
        data.append((_("Direction : {degrees}° {direction}") + '\n').format(
            degrees=self.bearing, direction=self.direction
        ))
        
        phone = self.properties.get("phone")
        if phone:
            phone_string = _("Téléphone : ")
            data.append(
                (
                    '<span class="glyphicon glyphicon-phone-alt '
                    'inline-icon" aria-hidden="true"></span>{phone_string}'
                    '<a href="tel:{phone}">{phone}</a>\n'
                ).format(phone_string=phone_string, phone=escape(phone))
            )
        
        data.append(self.get_address())
        
        result_properties = self.search_preset.render_pr(self.properties)
        
        try:
            if opening_hours and self.opening_hours is not None:
                opening_hours_text = self.opening_hours.stringify_week_schedules()
                if oh_in_popover:
                    oh_string = _("Horaires d'ouverture")
                    oh_content = (
                        '<button type="button" class="btn btn-default"'
                        ' data-toggle="popover" title="Horaires d\'ouverture"'
                        ' data-content="{}" data-html="true"'
                        ' data-placement="right">'
                        '<span class="glyphicon glyphicon-time inline-icon"'
                        ' aria-hidden="true"></span>{oh_string}</button>'
                    ).format(opening_hours_text.replace("\n", "<br>"), oh_string=oh_string)
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
            itinerary_string = _("Itinéraire jusqu'à ce point")
            itinerary_link = (
                '<a href="{}"><span class="glyphicon glyphicon-road'
                ' inline-icon" aria-hidden="true"></span>{itinerary_string}</a>'
            ).format(itinerary_url, itinerary_string=itinerary_string)
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
