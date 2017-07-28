from django.shortcuts import render
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, HttpResponseServerError, HttpResponseForbidden
from search.forms import SearchForm
from django import forms
from search.models import SearchPreset
from search.templatetags import geo_extras
from goose import settings
from math import sin, cos, atan2, degrees
import overpass
import geopy
from geopy import distance
from operator import itemgetter
import json
from ratelimit.decorators import ratelimit
from collections import OrderedDict
import logging
import pytz
import humanized_opening_hours

geolocator = geopy.geocoders.Nominatim(timeout=2000)

def geojson2dict(geojson, user_latitude, user_longitude):
    """
        Returns a dict from a geojson object, containing the properties
        of the target.
    """
    object_dict = {}
    object_dict['properties'] = geojson['properties']
    object_type = geojson['geometry']['type']
    if object_type == "Point":
        object_dict['osm_meta'] = ('node', geojson['id'])
        object_dict['coordinates'] = (
            geojson['geometry']['coordinates'][1],
            geojson['geometry']['coordinates'][0]
        )
    elif object_type == "LineString":
        object_dict['osm_meta'] = ('way', geojson['id'])
        # Gets the coordinates of the first point of the polygon.
        object_dict['coordinates'] = (
            geojson['geometry']['coordinates'][0][1],
            geojson['geometry']['coordinates'][0][0]
        )
    geolocator_object = geolocator.reverse(object_dict['coordinates'], language="fr")
    object_dict['address'] = ', '.join(geolocator_object.address.split(',')[:5])
    object_dict['distance'] = round(
        distance.vincenty(
        (user_latitude, user_longitude), object_dict['coordinates']).m
    )
    object_dict['bearing'] = get_bearing(
        user_latitude, user_longitude,
        object_dict['coordinates'][0],
        object_dict['coordinates'][1]
    )
    # TODO : Make it independent to timezones?
    opening_hours = object_dict['properties'].get("opening_hours")
    if opening_hours:
        object_dict['opening_jours'] = humanized_opening_hours.HumanizedOpeningHours(opening_hours, "fr", tz=pytz.timezone("Europe/Paris"))
    else:
        object_dict['opening_jours'] = None
    return object_dict

def get_bearing(lat1, lon1, lat2, lon2):
    """
        Returns the direction to go from one set of coordinates to another.
    """
    bearing = atan2(sin(lon2-lon1)*cos(lat2),
        cos(lat1)*sin(lat2)-sin(lat1)*cos(lat2)*cos(lon2-lon1))
    bearing = degrees(bearing)
    bearing = (bearing + 360) % 360
    return round(bearing, 1)

def get_nearest_targets(osm_keys, radius, user_latitude, user_longitude, search_preset, no_private, present_tags):
    """
        Returns a list of dicts with the properties of all results.
    """
    api = overpass.API()
    targets_dicts = []
    targets = []
    response = []
    for line in osm_keys.splitlines():
        # Request both nodes and ways.
        request = (
            '(node[{osm_key}](around:{r},{lat},{lon});'
            'way[{osm_key}](around:{r},{lat},{lon}););'
            ).format(
                osm_key=line, r=radius,
                lat=user_latitude, lon=user_longitude
                )
        response += api.Get(request)['features']
    for element in response:
        if no_private and element["properties"].get("access") == "private":
            continue
        else:
            targets_dicts.append(geojson2dict(element, user_latitude, user_longitude))
    targets_dicts = sorted(targets_dicts, key=itemgetter("distance"))
    for target in targets_dicts:
        rendered_target = geo_extras.render_target(
            target, search_preset,
            user_latitude, user_longitude,
            present_tags=present_tags
        )
        targets.append(rendered_target)
    return targets

def home(request):
    """
        The main page of Goose. Shows the search form, validate it
        and redirect to geo_results if it's correct.
    """
    if request.method == "POST":
        form = SearchForm(request.POST)
        if form.is_valid():
            form.clean()
            user_latitude = form.cleaned_data["user_latitude"]
            user_longitude = form.cleaned_data["user_longitude"]
            calculated_address = form.cleaned_data["calculated_address"]
            request.session["search_form"] = {
                "user_latitude": user_latitude,
                "user_longitude": user_longitude,
                "user_address": calculated_address,
                "calculated_address": calculated_address,
                "radius": form.cleaned_data["radius"],
                "searched_target_id": form.cleaned_data["searched_target"].id,
                "no_private": form.cleaned_data["no_private"],
            }
            return redirect("results")
    else:
        form = SearchForm()
    return render(request, "search/geo.html", locals())

@ratelimit(key='ip', rate="3/m")
def results(request):
    """
        The page where the results are displayed. Initially empty,
        filled with Ajax and the "geo_get_results" view.
    """
    if request.session.get("search_form") is not None:
        was_limited = getattr(request, 'limited', False)
        searched_target_id = request.session["search_form"]["searched_target_id"]
        user_latitude = request.session["search_form"]["user_latitude"]
        user_longitude = request.session["search_form"]["user_longitude"]
        user_estimated_address = request.session["search_form"]["calculated_address"]
        radius = request.session["search_form"]["radius"]
        no_private = request.session["search_form"]["no_private"]
    else:
        return redirect("home")
    return render(request, "search/geo_results.html", {
        "user_coords": (user_latitude, user_longitude),
        "user_estimated_address": user_estimated_address,
        "radius": radius,
        "searched_target_id": searched_target_id,
        "no_private": no_private,
        "was_limited": was_limited,
        })

def render_filters_from_tags(tags, count):
    """
        Returns raw HTML for a block allowing to filter results (uses JS).
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
    tags_names = OrderedDict()
    tags_names["open"] = "Ouvert"
    tags_names["closed"] = "Fermé"
    tags_names["unknown_schedules"] = "Horaires inconnues"
    tags_names["vegetarian:yes"] = "Menu végétarien"
    tags_names["vegetarian:only"] = "Entièrement végétarien"
    tags_names["vegetarian:no"] = "Non végétarien"
    tags_names["vegetarian:unknown"] = "Statut végétarien inconnu"
    tags_names["vegan:yes"] = "Menu végétalien"
    tags_names["vegan:only"] = "Entièrement végétalien"
    tags_names["vegan:no"] = "Non végétalien"
    tags_names["vegan:unknown"] = "Statut végétalien inconnu"
    tags_names["wheelchair:yes"] = "Accessible aux fauteuils roulants"
    tags_names["wheelchair:limited"] = "Accès limité aux fauteuils roulants"
    tags_names["wheelchair:no"] = "Non accessible aux fauteuils roulants"
    tags_names["wheelchair:unknown"] = "Statut des fauteuils roulants inconnu"
    for tag in tags_names:
        if tag in tags:
            n = tags[tag]
            output += '<input type="checkbox" checked onchange="filter_results_handler(this)" name="result_filter" id="filter_{tag}" value="{tag}"><label for="filter_{tag}"> {label} <span class="badge">{n}</span></label><br/>\n'.format(
                tag=tag, label=tags_names[tag], n=n)
    return html.format(count=count, content=output)

@csrf_exempt
def get_results(request):
    """
        Used by Ajax to get results.
    """
    if not request.is_ajax():
        return HttpResponseForbidden("This URL if for Ajax only.")
    else:
        searched_target_id = request.POST["searched_target_id"]
        searched_target = SearchPreset.objects.get(id=searched_target_id)
        radius = request.POST["radius"]
        user_latitude = float(request.POST["user_latitude"])
        user_longitude = float(request.POST["user_longitude"])
        no_private = request.POST["no_private"]
        if no_private == "true":
            no_private = True
        else:
            no_private = False
        
        targets = []
        status = "error"
        err_msg = ""
        debug_msg = ""
        present_tags = {}
        try:
            targets = get_nearest_targets(
                searched_target.osm_keys, radius, user_latitude,
                user_longitude, searched_target, no_private,
                present_tags
            )
            status = "ok"
        except geopy.exc.GeopyError as e:
            err_msg = "Une erreur s'est produite lors de l'acquisition de vos coordonnées. Vous pouvez essayer de recharger la page dans quelques instants."
            debug_msg = str(e)
        except overpass.OverpassError as e:
            err_msg = "Une erreur s'est produite lors de la requête vers les serveurs d'OpenStreetMap. Vous pouvez essayer de recharger la page dans quelques instants."
            debug_msg = str(e)
        except Exception as e:
            err_msg = "Une erreur non prise en charge s'est produite."
            debug_msg = str(e)
        filters = render_filters_from_tags(present_tags, len(targets))
        # Logs the request to make statistics.
        # Doesn't logs if the request comes from an authenticated user,
        # as it is probably an admin.
        if not request.user.is_authenticated():
            logger = logging.getLogger("statistics")
            logger.info(
                "search:{id}:{radius}:{lat}:{lon}".format(
                    id=searched_target_id,
                    radius=radius,
                    # Rounds the stored coordinates for privacy's sake.
                    lat=round(user_latitude),
                    lon=round(user_longitude)
                )
            )
        return HttpResponse(json.dumps({
                "status": status, "content": targets, "err_msg": err_msg,
                "debug_msg": debug_msg, "filters": filters
            }),
            content_type="application/json"
        )

def about(request):
    """
        The about page, providing some informations about the site itself.
    """
    # Logs the request to make statistics.
    logger = logging.getLogger("statistics")
    logger.info("about_page")
    return render(request, "search/about.html")
