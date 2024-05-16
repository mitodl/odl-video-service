"""
Classes related to models for ODL Video
"""

import datetime

import pytz
from django.db.models import DateTimeField, Manager, Model
from django.db.models.query import QuerySet


def now_in_utc():
    """
    Get the current time in UTC

    Returns:
        datetime.datetime: A datetime object for the current time
    """
    return datetime.datetime.now(tz=pytz.UTC)


class TimestampedModelQuerySet(QuerySet):
    """
    Subclassed QuerySet for TimestampedModelManager
    """

    def update(self, **kwargs):
        """
        Automatically update updated_at timestamp when .update(). This is because .update()
        does not go through .save(), thus will not auto_now, because it happens on the
        database level without loading objects into memory.
        """  # noqa: D402, E501
        if "updated_at" not in kwargs:
            kwargs["updated_at"] = now_in_utc()
        return super().update(**kwargs)


class TimestampedModelManager(Manager):
    """
    Subclassed manager for TimestampedModel
    """

    def update(self, **kwargs):
        """
        Allows access to TimestampedModelQuerySet's update method on the manager
        """  # noqa: D401
        return self.get_queryset().update(**kwargs)

    def get_queryset(self):
        """
        Returns custom queryset
        """  # noqa: D401
        return TimestampedModelQuerySet(self.model, using=self._db)


class TimestampedModel(Model):
    """
    Base model for create/update timestamps
    """

    objects = TimestampedModelManager()
    created_at = DateTimeField(auto_now_add=True)  # UTC  # noqa: DJ012
    updated_at = DateTimeField(auto_now=True)  # UTC

    class Meta:
        abstract = True
