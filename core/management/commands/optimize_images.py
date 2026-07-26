"""Normalise les images deja en base au format cible du modele.

Les champs image de Article et Project sont des ResizedImageField qui forcent
le WebP et une taille maximale — mais uniquement au moment de l'upload. Les
fichiers importes avant l'ajout de ces options sont restes tels quels (JPEG
1920x1280 de 582 Ko servis dans une carte de 335 px, par exemple).

Cette commande reconvertit ces fichiers herites et met a jour la base.
Les originaux ne sont pas supprimes : ils sont seulement dereferences, pour
pouvoir revenir en arriere. Utiliser --delete-old pour les effacer.

    python manage.py optimize_images --dry-run
    python manage.py optimize_images
"""

from io import BytesIO
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from PIL import Image, ImageOps

from core.models import Article, Project

# (modele, taille cible) — aligne sur les ResizedImageField de core/models.py
TARGETS = [
    (Article, (1200, 675)),
    (Project, (1200, 900)),
]
QUALITY = 85


class Command(BaseCommand):
    help = "Reconvertit en WebP redimensionne les images heritees (Article, Project)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Affiche ce qui serait fait, sans rien modifier.",
        )
        parser.add_argument(
            "--delete-old",
            action="store_true",
            help="Supprime le fichier d'origine apres conversion.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        delete_old = options["delete_old"]
        total_before = total_after = 0
        converted = skipped = 0

        for model, size in TARGETS:
            label = model._meta.verbose_name_plural
            self.stdout.write(self.style.MIGRATE_HEADING(f"\n{label} (cible {size[0]}x{size[1]} WebP)"))

            for obj in model.objects.exclude(image="").exclude(image__isnull=True):
                field = obj.image

                try:
                    old_bytes = field.size
                    with Image.open(field.path) as img:
                        img.load()
                        width, height = img.size
                        fmt = (img.format or "").upper()
                except (FileNotFoundError, OSError) as exc:
                    self.stdout.write(self.style.WARNING(f"  ! {obj} — illisible ({exc})"))
                    skipped += 1
                    continue

                needs_format = fmt != "WEBP"
                needs_resize = width > size[0] or height > size[1]

                if not (needs_format or needs_resize):
                    self.stdout.write(f"  = {Path(field.name).name} deja conforme")
                    skipped += 1
                    continue

                reasons = []
                if needs_format:
                    reasons.append(f"format {fmt or '?'}")
                if needs_resize:
                    reasons.append(f"{width}x{height}")

                if dry_run:
                    self.stdout.write(
                        f"  ~ {Path(field.name).name} — {', '.join(reasons)}, "
                        f"{old_bytes / 1024:.0f} Ko -> a convertir"
                    )
                    total_before += old_bytes
                    converted += 1
                    continue

                old_path = Path(field.path)
                old_name = field.name

                with Image.open(old_path) as img:
                    img = ImageOps.exif_transpose(img)
                    img.thumbnail(size, Image.LANCZOS)
                    if img.mode not in ("RGB", "RGBA"):
                        img = img.convert("RGB")
                    buffer = BytesIO()
                    img.save(buffer, format="WEBP", quality=QUALITY, method=6)

                new_bytes = buffer.tell()
                # Nom de fichier seul : upload_to prefixe deja le dossier, sinon
                # on obtient portfolio/portfolio/xxx.webp.
                new_name = Path(old_name).with_suffix(".webp").name

                field.save(new_name, ContentFile(buffer.getvalue()), save=True)

                self.stdout.write(
                    "  + {} -> {} ({:.0f} Ko -> {:.0f} Ko, -{:.0f}%)".format(
                        Path(old_name).name,
                        Path(field.name).name,
                        old_bytes / 1024,
                        new_bytes / 1024,
                        (1 - new_bytes / old_bytes) * 100,
                    )
                )

                if delete_old and old_path.exists() and old_path != Path(field.path):
                    old_path.unlink()
                    self.stdout.write(f"    original supprime : {old_path.name}")

                total_before += old_bytes
                total_after += new_bytes
                converted += 1

        self.stdout.write("")
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"[dry-run] {converted} image(s) a convertir, "
                    f"{total_before / 1024:.0f} Ko concernes. Aucune modification."
                )
            )
        else:
            gain = total_before - total_after
            self.stdout.write(
                self.style.SUCCESS(
                    f"{converted} image(s) converties, {skipped} ignoree(s). "
                    f"{total_before / 1024:.0f} Ko -> {total_after / 1024:.0f} Ko "
                    f"(-{gain / 1024:.0f} Ko)"
                )
            )
