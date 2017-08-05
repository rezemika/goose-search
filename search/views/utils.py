import geopy
from geopy import distance
import pytz
import humanized_opening_hours
from math import sin, cos, atan2, degrees
from goose import settings
import overpass
from collections import OrderedDict

geolocator = geopy.geocoders.Nominatim(timeout=2000)

def get_string_address(properties, coordinates):
    """
        Returns a human-readable address from the properties of
        a POI and its coordinates.
    """
    address_data = {
        "street": properties.get("addr:street"),
        "housenumber": properties.get("addr:housenumber"),
        "city": properties.get("addr:city"),
        "postcode": properties.get("addr:postcode")
    }
    if all(address_data.values()):
        address = "Adresse exacte : {}, {}, {} {}".format(
            address_data["housenumber"], address_data["street"],
            address_data["postcode"], address_data["city"]
        )
    elif address_data["housenumber"] and address_data["street"]:
        address = "Adresse exacte : {}, {}".format(
            address_data["housenumber"], address_data["street"]
        )
    else:
        geolocator_object = geolocator.reverse(coordinates, language="fr")
        estimated_address = ', '.join(geolocator_object.address.split(',')[:5])
        address = "Adresse estimée : {}".format(estimated_address)
    return address

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
        while attempts < settings.GOOSE_META["max_geolocation_attempts"]:
            try:
                response += api.Get(request)['features']
                break
            except overpass.OverpassError as e:
                attempts += 1
                if attempts == settings.GOOSE_META["max_geolocation_attempts"]:
                    raise e
    for element in response:
        if no_private and element["properties"].get("access") in ["private", "no"]:
            continue
        results.append(Result(element, search_preset, user_coords))
    results = sorted(results, key=lambda result: result.distance)
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

class Result:
    """
        A result and its properties.
    """
    def __init__(self, geojson, search_preset, user_coordinates):
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
        self.string_address = get_string_address(self.properties, self.coordinates)
        self.distance = round(distance.vincenty(
            (user_coordinates[0], user_coordinates[1]), self.coordinates
        ).m)
        self.bearing = get_bearing(user_coordinates, self.coordinates)
        self.direction = deg2dir(self.bearing)
        # TODO : Make it independent to timezones ?
        oh_field = self.properties.get("opening_hours")
        self.opening_hours = None
        if oh_field:
            try:
                self.opening_hours = humanized_opening_hours.HumanizedOpeningHours(
                    oh_field, "fr", tz=pytz.timezone("Europe/Paris")
                )
            except humanized_opening_hours.HOHError:
                # TODO : Log and warn user.
                self.opening_hours = None
        self.tags = []
        return
    
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
    
    def render(self, render_tags=True, link_to_osm=True, opening_hours=True, itinerary=True):
        """
            Returns an HTML div (with "result-box" class) displaying
            a result and its properties.
        """
        html = '<div role="article" class="result-box">{}</div>'
        content = ""
        data = []
        name = self.properties.get("name")
        if name:
            data.append("Nom : {}\n".format(self.properties["name"]))
        if self.opening_hours is not None:
            if self.opening_hours.is_open():
                data.append("<b>Ouvert</b>\n")
            else:
                data.append("<b>Fermé</b>\n")
        data.append("Distance : {distance} mètres".format(distance=self.distance))
        data.append("Direction : {degrees}° {direction}\n".format(
            degrees=self.bearing, direction=self.direction
        ))
        data.append(self.string_address)
        
        result_properties = self.search_preset.render_pr(self.properties)
        
        if opening_hours and self.opening_hours is not None:
            opening_hours_text = self.opening_hours.stringify_week_schedules()
            oh_content = ('<button type="button" class="btn btn-default"'
                ' data-toggle="popover" title="Horaires d\'ouverture"'
                ' data-content="{}" data-html="true"'
                ' data-placement="right">'
                '<span class="glyphicon glyphicon-time inline-icon"'
                ' aria-hidden="true"></span>Horaires d\'ouverture</button>'
            ).format(opening_hours_text.replace("\n", "<br>"))
            data.append('\n' + oh_content)
        
        data.append('\n' + result_properties)
        
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
