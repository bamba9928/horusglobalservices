import os

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.utils import timezone


class CKEditorUploadStorage(FileSystemStorage):
    """Images envoyees depuis l'editeur CKEditor 5 : media/uploads/AAAA/MM/<nom>.

    Meme arborescence que l'ancien CKEditor 4 (media/uploads/...), donc nginx
    (location /media/) les sert sans changement et les anciens liens restent valides.
    Instanciee sans argument par django_ckeditor_5 (CKEDITOR_5_FILE_STORAGE) :
    MEDIA_ROOT est lu a chaque instanciation, pas a l'import.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("location", os.path.join(settings.MEDIA_ROOT, "uploads"))
        kwargs.setdefault("base_url", settings.MEDIA_URL + "uploads/")
        super().__init__(*args, **kwargs)

    def save(self, name, content, max_length=None):
        subdir = timezone.now().strftime("%Y/%m")
        # basename : aucun chemin fourni par le client ne peut sortir du dossier
        return super().save(f"{subdir}/{os.path.basename(name)}", content, max_length)
