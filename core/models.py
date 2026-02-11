from django.db import models
from django.utils import timezone


class Contact(models.Model):
    """Modèle pour les messages de contact"""

    name = models.CharField(
        max_length=100,
        verbose_name="Nom complet"
    )
    email = models.EmailField(
        verbose_name="Email"
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="Téléphone"
    )
    message = models.TextField(
        verbose_name="Message"
    )
    created_at = models.DateTimeField(
        default=timezone.now,
        verbose_name="Date de réception"
    )
    is_read = models.BooleanField(
        default=False,
        verbose_name="Lu"
    )
    is_responded = models.BooleanField(
        default=False,
        verbose_name="Répondu"
    )

    class Meta:
        verbose_name = "Message de contact"
        verbose_name_plural = "Messages de contact"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.email} ({self.created_at.strftime('%d/%m/%Y')})"