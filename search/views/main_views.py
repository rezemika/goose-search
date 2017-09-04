from django.shortcuts import render
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, HttpResponseForbidden
from django.utils.html import escape
from search.models import SearchPreset
from search.forms import SearchForm
from ratelimit.decorators import ratelimit
from search.views import utils
import geopy
import overpass
import logging
import json

debug_logger = logging.getLogger("DEBUG")

def home(request):
    """
        The main page of Goose. Shows the search form, validate it
        and redirect to "results" if it's correct.
    """
    base_template = "base.html"
    if request.method == "POST":
        form = SearchForm(request.POST)
        if form.is_valid():
            form.clean()
            user_latitude = form.cleaned_data["latitude"]
            user_longitude = form.cleaned_data["longitude"]
            calculated_address = form.cleaned_data["calculated_address"]
            request.session["search_form"] = {
                "user_latitude": user_latitude,
                "user_longitude": user_longitude,
                "user_address": calculated_address,
                "radius": form.cleaned_data["radius"],
                "search_preset_id": form.cleaned_data["search_preset"].id,
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
    if request.session.get("search_form") is None:
        return redirect("home")
    was_limited = getattr(request, 'limited', False)
    search_preset_id = request.session["search_form"]["search_preset_id"]
    search_preset = SearchPreset.objects.get(id=search_preset_id)
    user_latitude = request.session["search_form"]["user_latitude"]
    user_longitude = request.session["search_form"]["user_longitude"]
    user_address = escape(request.session["search_form"]["user_address"])
    radius = request.session["search_form"]["radius"]
    no_private = request.session["search_form"]["no_private"]
    search_description = '"{}" dans un rayon de {} mètres.'.format(search_preset.name, radius)
    if no_private is True:
        search_description += " Exclusion des résultats à accès privé."
    else:
        search_description += " Inclusion des résultats à accès privé."
    return render(request, "search/geo_results.html", {
        "user_coords": (user_latitude, user_longitude),
        "user_address": user_address,
        "radius": radius,
        "search_preset_id": search_preset_id,
        "no_private": no_private,
        "was_limited": was_limited,
        "search_description": search_description
        }
    )

@csrf_exempt
def get_results(request):
    """
        Used by Ajax to get the results.
    """
    if not request.is_ajax():
        return HttpResponseForbidden("This URL if for Ajax only.")
    debug_logger.debug("----- A new request is coming! -----")
    search_preset_id = request.POST["search_preset_id"]
    search_preset = SearchPreset.objects.get(id=search_preset_id)
    radius = request.POST["radius"]
    user_latitude = float(request.POST["user_latitude"])
    user_longitude = float(request.POST["user_longitude"])
    no_private = request.POST["no_private"]
    if no_private == "true":
        no_private = True
    else:
        no_private = False
    rendered_results = []
    status = "error"
    err_msg = ""
    debug_msg = ""
    tags_filter = ""
    try:
        results = utils.get_results(
            search_preset, (user_latitude, user_longitude), radius,
            no_private
        )
        utils.get_all_addresses(results)
        for result in results:
            tags_count = utils.get_all_tags(results)
            tags_filter = utils.render_tag_filter(tags_count, len(results))
            rendered_results.append("<li>" + result.render() + "</li>")
        status = "ok"
        debug_logger.debug("Request successfull!")
    except geopy.exc.GeopyError as e:
        err_msg = "Une erreur s'est produite lors de l'acquisition de vos coordonnées. Vous pouvez essayer de recharger la page dans quelques instants."
        debug_msg = str(e)
        debug_logger.debug("Geopy error: {}".format(str(e)))
    except overpass.OverpassError as e:
        err_msg = "Une erreur s'est produite lors de la requête vers les serveurs d'OpenStreetMap. Vous pouvez essayer de recharger la page dans quelques instants."
        debug_msg = str(e)
        debug_logger.debug("Overpass error: {}".format(str(e)))
    except Exception as e:
        err_msg = "Une erreur non prise en charge s'est produite."
        debug_msg = str(e)
        debug_logger.debug("Unhandled error: {}".format(str(e)))
    # Logs the request to make statistics.
    # Doesn't logs if the request comes from an authenticated user,
    # as it is probably an admin.
    if not request.user.is_authenticated():
        logger = logging.getLogger("statistics")
        logger.info(
            "search:{id}:{radius}:{lat}:{lon}".format(
                id=search_preset_id,
                radius=radius,
                # Rounds the stored coordinates for privacy's sake.
                lat=round(user_latitude),
                lon=round(user_longitude)
            )
        )
    return HttpResponse(json.dumps({
            "status": status, "content": rendered_results, "err_msg": err_msg,
            "debug_msg": debug_msg, "filters": tags_filter
        }),
        content_type="application/json"
    )

# Higher ratelimit, because users of light version may have
# network troubles (like load interruptions).
@ratelimit(key='ip', rate="10/m")
def light_home(request):
    """
        The main page of the light version of Goose.
        The results are displayed on the same page
        to avoid a redirection.
    """
    base_template = "base_light.html"
    if request.method != "POST":
        form = SearchForm()
        return render(request, "search/geo.html", locals())
    form = SearchForm(request.POST)
    was_limited = getattr(request, 'limited', False)
    if was_limited:
        limit_error = (
            "<center><em>Trop peu de requêtes ont été faites en trop "
            "peu de temps. Merci d'attendre quelques secondes avant "
            "de raffraichir la page.</em></center>"
        )
        return render(request, "search/geo.html", locals())
    if not form.is_valid():
        return render(request, "search/geo.html", locals())
    form.clean()
    search_preset = form.cleaned_data["search_preset"]
    user_latitude = form.cleaned_data["latitude"]
    user_longitude = form.cleaned_data["longitude"]
    user_address = escape(form.cleaned_data["calculated_address"])
    radius = form.cleaned_data["radius"]
    no_private = form.cleaned_data["no_private"]
    user_coords = (user_latitude, user_longitude)
    search_description = '"{}" dans un rayon de {} mètres.'.format(search_preset.name, radius)
    if no_private is True:
        search_description += " Exclusion des résultats à accès privé."
    else:
        search_description += " Inclusion des résultats à accès privé."
    rendered_results = []
    status = "error"
    err_msg = ""
    try:
        results = utils.get_results(
            search_preset, user_coords, radius,
            no_private
        )
        utils.get_all_addresses(results)
        for result in results:
            rendered_results.append(str(
                "<li>" + result.render(
                    render_tags=False, oh_in_popover=False
                ).replace('\n', '<br/>') + "</li>"
            ))
        status = "ok"
        debug_logger.debug("Request successfull!")
    except geopy.exc.GeopyError as e:
        err_msg = "Une erreur s'est produite lors de l'acquisition de vos coordonnées. Vous pouvez essayer de recharger la page dans quelques instants."
        debug_logger.debug("Geopy error: {}".format(str(e)))
    except overpass.OverpassError as e:
        err_msg = "Une erreur s'est produite lors de la requête vers les serveurs d'OpenStreetMap. Vous pouvez essayer de recharger la page dans quelques instants."
        debug_logger.debug("Overpass error: {}".format(str(e)))
    except Exception as e:
        err_msg = "Une erreur non prise en charge s'est produite."
        debug_logger.debug("Unhandled error: {}".format(str(e)))
    # Logs the request to make statistics.
    # Doesn't logs if the request comes from an authenticated user,
    # as it is probably an admin.
    if not request.user.is_authenticated():
        logger = logging.getLogger("statistics")
        logger.info(
            "search:{id}:{radius}:{lat}:{lon}".format(
                id=search_preset.id,
                radius=radius,
                # Rounds the stored coordinates for privacy's sake.
                lat=round(user_latitude),
                lon=round(user_longitude)
            )
        )
    
    return render(request, "search/light_results.html", {
        "results": rendered_results, "user_coords": user_coords,
        "user_address": user_address, "search_description": search_description,
        "status": status, "err_msg": err_msg
    })

def about(request):
    """
        The about page, providing some informations about the site itself.
    """
    if "/light/" in request.path:
        base_template = "base_light.html"
    else:
        base_template = "base.html"
    # Logs the request to make statistics.
    logger = logging.getLogger("statistics")
    logger.info("about_page")
    return render(request, "search/about.html", {"base_template": base_template})
