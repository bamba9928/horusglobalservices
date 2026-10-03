from django.contrib.staticfiles.apps import StaticFilesConfig


class ProjectStaticFilesConfig(StaticFilesConfig):
    """collectstatic sans les fichiers SOURCE de la compilation Tailwind.

    static/src/input.css (et l'ancien static/css/input.css) contiennent `@import "tailwindcss"` :
    ce n'est pas un fichier statique mais une directive de build. Le stockage a empreintes
    (ManifestStaticFilesStorage) la prend pour une reference CSS et fait echouer collectstatic.
    Seul output.css, produit par `npm run build:css`, doit etre publie.
    """

    ignore_patterns = StaticFilesConfig.ignore_patterns + ["input.css"]
