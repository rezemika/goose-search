from django import template
from django.utils.safestring import mark_safe
from search.models import SearchPreset

register = template.Library()

@register.simple_tag
def render_target(target, search_preset, user_latitude, user_longitude, present_tags=None):
    """
        Return the final HTML rendering for a target.
    """
    
    html = '<li><div role="article" class="geo_search_result_box">{}</div></li>'
    
    content = """\
    {osm_tag}{name}{opening_status}Distance : {distance} mètres
    Direction : {degrees}° {direction}
    
    {address}
    """
    
    if target["properties"].get("name"):
        name = "Nom : {}\n".format(target["properties"]["name"])
    else:
        name = ""
    
    hoh = target['opening_jours']
    oh_content = ""
    opening_status = ""
    if name:
        opening_status += "\n"
    if hoh is not None:
        opening_hours_text = hoh.stringify_week_schedules()
        oh_content = ('<button type="button" class="btn btn-default"'
            ' data-toggle="popover" title="Horaires d\'ouverture"'
            ' data-content="{}" data-html="true"'
            ' data-placement="right">'
            '<span class="glyphicon glyphicon-time inline-icon"'
            ' aria-hidden="true"></span>Horaires d\'ouverture</button>'
            ).format(opening_hours_text.replace("\n", "<br>"))
        if hoh.is_open() is False:
            opening_status += "\n<b>Fermé</b>\n"
    
    osm_link = "http://www.openstreetmap.org/{}/{}".format(
        target['osm_meta'][0],
        target['osm_meta'][1]
    )
    
    content = content.format(
        osm_tag=(
            '<a href="{}"><img class="osm-link-logo" '
            'src="/static/images/osm_logo.png"></a>'
        ).format(osm_link),
        name=name,
        opening_status=opening_status,
        distance=target["distance"],
        degrees=target["bearing"], direction=deg2dir(target["bearing"]),
        address=render_address(target["properties"], target["address"])
    )
    
    properties = search_preset.render_pr(target["properties"])
    # TODO : Make it cleaner.
    if properties:
        content += '\n' + properties
    if oh_content:
        if properties:
            content += '\n'
        content += '\n' + oh_content
        if not properties:
            content += '\n'
    
    route_url = ('https://www.openstreetmap.org/directions?'
        'engine=graphhopper_foot&route={},{};{},{}').format(
        user_latitude, user_longitude,
        target['coordinates'][0], target['coordinates'][1])
    route_link = ('<a href="{}"><span class="glyphicon glyphicon-road'
        ' inline-icon" aria-hidden="true"></span>Itinéraire jusqu\'à ce'
        ' point</a>').format(route_url)
    if properties:
        content += '\n\n' + route_link
    else:
        content += '\n' + route_link
    
    phone_number = target["properties"].get("phone")
    if phone_number:
        content += ('\n\n<a href="tel:{phone_number}"><span'
            ' class="glyphicon glyphicon-phone-alt inline-icon"></span>'
            '{phone_number}</a>').format(phone_number=phone_number)
    
    website = target["properties"].get("website")
    if website:
        if not website.startswith("http"):
            website = "https://" + website
        elif website.startswith("http://"):
            website = website.replace("http://", "https://")
        content += ('\n\n<a href="{website}"><span class="glyphicon'
            ' glyphicon-globe inline-icon"></span>{website}</a>').format(
                website=website)
    content += render_tags(target["properties"], hoh, present_tags)
    return html.format(content)

def render_tags(properties, hoh, present_tags):
    tags = []
    # Opening hours tags
    if hoh is not None:
        if hoh.is_open():
            tags.append("open")
        else:
            tags.append("closed")
    else:
        tags.append("unknown_schedules")
    # Diet tags
    diet = properties.get("diet:vegetarian")
    if diet:
        if diet == "yes":
            tags.append("vegetarian:yes")
        elif diet == "only":
            tags.append("vegetarian:only")
        else:
            tags.append("vegetarian:no")
    else:
        tags.append("vegetarian:unknown")
    diet = properties.get("diet:vegan")
    if diet:
        if diet == "yes":
            tags.append("vegan:yes")
        elif diet == "only":
            tags.append("vegan:only")
        else:
            tags.append("vegetarian:no")
    else:
        tags.append("vegan:unknown")
    # Wheelchairs tags
    wc = properties.get("wheelchair")
    if wc:
        if wc == "yes":
            tags.append("wheelchair:yes")
        elif wc == "limited":
            tags.append("wheelchair:limited")
        elif wc == "no":
            tags.append("wheelchair:no")
    else:
        tags.append("wheelchair:unknown")
    for tag in tags:
        if tag in present_tags.keys():
            present_tags[tag] += 1
        else:
            present_tags[tag] = 1
    return '<span class="result_tags" style="visibility:hidden">{}</span>\n'.format(';'.join(tags))

def render_address(properties, estimated_address):
    """
        Return a human-readable address from targets properties
        and estimated address. (Return its true address if possible.)
    """
    target_address = {}
    target_address["street"] = properties.get("addr:street")
    target_address["housenumber"] = properties.get("addr:housenumber")
    target_address["city"] = properties.get("addr:city")
    target_address["postcode"] = properties.get("addr:postcode")
    if all(target_address.values()):
        address = "Adresse exacte : {}, {}, {} {}".format(
            target_address["housenumber"], target_address["street"],
            target_address["postcode"], target_address["city"])
    elif target_address["housenumber"] and target_address["street"]:
        address = "Adresse exacte : {}, {}".format(
            target_address["housenumber"], target_address["street"])
    else:
        address = "Adresse estimée : {}".format(estimated_address)
    return address

def deg2dir(deg):
    '''
        Return a cardinal direction from a direction (in degrees).
        https://gist.github.com/RobertSudwarts/acf8df23a16afdb5837f
    '''
    dirs = ["N ↑", "NE ↗", "E →", "SE ↘", "S ↓", "SO ↙", "O ←", "NO ↖"]
    ix = int((deg + 22.5)/45)
    return dirs[ix % 8]

@register.filter()
def render_coordinate(coord):
    """
        Return a rounded and stringified number from a float.
        Used to render short GPS coordinates.
    """
    return str(round(coord, 5))

@register.simple_tag
def render_searched_target(st_id, radius, no_private):
    """
        Return a short summary of the current research.
        Used in the "geo_results" view's info block.
    """
    searched_target = SearchPreset.objects.get(id=st_id)
    output = '"{}" dans un rayon de {} mètres.'.format(searched_target.name, radius)
    if no_private == True:
        output += " Exclusion des résultats à accès privé."
    else:
        output += " Inclusion des résultats à accès privé."
    return output

@register.filter()
def render_bool_js(value):
    """
        Return a stringified boolean value, suitable for JS.
    """
    if value is True:
        return "true"
    else:
        return "false"
