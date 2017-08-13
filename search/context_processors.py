from goose import settings
from git import Repo

def get_git_version():
    """
        Gets the git version of the site.
        From https://github.com/zestedesavoir/zds-site/blob/dev/zds/utils/context_processor.py
    """
    try:
        repo = Repo(settings.BASE_DIR)
        branch = repo.active_branch
        commit = repo.head.commit.hexsha
        name = u"{0}/{1}".format(branch, commit[:7])
        github_url = "https://github.com/rezemika/goose-search/"
        return {"name": name, "github_url": github_url, "version_url": github_url + "tree/{}".format(commit)}
    except (KeyError, TypeError):
        return {"name": "", "github_url": github_url, "version_url": ""}

def meta_processor(request):
    """
        Adds the GOOSE_META variable and the current version
        to all templates.
    """
    meta = settings.GOOSE_META
    return {"GOOSE_META": meta, "VERSION": get_git_version()}
