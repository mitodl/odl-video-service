"""Factories for techtv2ovs"""

from factory import Faker, SubFactory
from factory.django import DjangoModelFactory
from factory.fuzzy import FuzzyInteger, FuzzyText

from techtv2ovs.models import TechTVCollection, TechTVVideo
from ui.factories import CollectionFactory, VideoFactory


class TechTVCollectionFactory(DjangoModelFactory):
    """
    Factory for a TechTVCollection
    """

    id = FuzzyInteger(low=1)
    name = FuzzyText(prefix="TTV Collection")
    description = Faker("text")
    owner_email = FuzzyText(suffix="@mit.edu")
    collection = SubFactory(CollectionFactory)

    class Meta:
        model = TechTVCollection


class TechTVVideoFactory(DjangoModelFactory):
    """
    Factory for a TechTVVideo
    """

    ttv_id = FuzzyInteger(low=1)
    ttv_collection = SubFactory(TechTVCollectionFactory)
    title = FuzzyText(prefix="TTV Video ")
    description = Faker("text")
    external_id = FuzzyText()
    video = SubFactory(VideoFactory)

    class Meta:
        model = TechTVVideo
