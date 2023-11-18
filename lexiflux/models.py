from django.db import models


class BookPage(models.Model):
    number = models.PositiveIntegerField()
    content = models.TextField()

    class Meta:
        ordering = ["number"]

    def __str__(self):
        return str(self.number)
