from collections import OrderedDict
from django.db import models
from django.utils.translation import ugettext_lazy as _
from shapely.geometry import JOIN_STYLE, CAP_STYLE, mapping

from c3nav.mapdata.models.geometry.base import GeometryFeature, GeometryFeatureBase
from c3nav.mapdata.utils.json import format_geojson


SPACE_FEATURE_TYPES = OrderedDict()


class SpaceFeatureBase(GeometryFeatureBase):
    def __new__(mcs, name, bases, attrs):
        cls = super().__new__(mcs, name, bases, attrs)
        if not cls._meta.abstract:
            SPACE_FEATURE_TYPES[name.lower()] = cls
        return cls


class SpaceFeature(GeometryFeature, metaclass=SpaceFeatureBase):
    """
    a map feature that has a geometry and belongs to a space
    """
    space = models.ForeignKey('mapdata.Space', on_delete=models.CASCADE, verbose_name=_('space'))

    class Meta:
        abstract = True

    def get_geojson_properties(self):
        result = super().get_geojson_properties()
        result['space'] = self.space.id
        return result


class StuffedArea(SpaceFeature):
    """
    A slow area with many tables or similar. Avoid it from routing by slowing it a bit down
    """
    geomtype = 'polygon'

    class Meta:
        verbose_name = _('Stuffed Area')
        verbose_name_plural = _('Stuffed Areas')
        default_related_name = 'stuffedareas'


class Stair(SpaceFeature):
    """
    A stair
    """
    geomtype = 'polyline'

    class Meta:
        verbose_name = _('Stair')
        verbose_name_plural = _('Stairs')
        default_related_name = 'stairs'

    def to_geojson(self):
        result = super().to_geojson()
        original_geometry = result['geometry']
        draw = self.geometry.buffer(0.05, join_style=JOIN_STYLE.mitre, cap_style=CAP_STYLE.flat)
        result['geometry'] = format_geojson(mapping(draw))
        result['original_geometry'] = original_geometry
        return result

    def to_shadow_geojson(self):
        shadow = self.geometry.parallel_offset(0.03, 'right', join_style=JOIN_STYLE.mitre)
        shadow = shadow.buffer(0.019, join_style=JOIN_STYLE.mitre, cap_style=CAP_STYLE.flat)
        return OrderedDict((
            ('type', 'Feature'),
            ('properties', OrderedDict((
                ('type', 'shadow'),
                ('original_type', self.__class__.__name__.lower()),
                ('original_id', self.id),
                ('space', self.space.id),
            ))),
            ('geometry', format_geojson(mapping(shadow), round=False)),
        ))


class Obstacle(SpaceFeature):
    """
    An obstacle
    """
    geomtype = 'polygon'

    class Meta:
        verbose_name = _('Obstacle')
        verbose_name_plural = _('Obstacles')
        default_related_name = 'obstacles'


class LineObstacle(SpaceFeature):
    """
    An obstacle that is a line with a specific width
    """
    width = models.DecimalField(_('obstacle width'), max_digits=4, decimal_places=2, default=0.15)

    geomtype = 'polyline'

    class Meta:
        verbose_name = _('Line Obstacle')
        verbose_name_plural = _('Line Obstacles')
        default_related_name = 'lineobstacles'

    @property
    def buffered_geometry(self):
        return self.geometry.buffer(self.width / 2, join_style=JOIN_STYLE.mitre, cap_style=CAP_STYLE.flat)

    def to_geojson(self):
        result = super().to_geojson()
        original_geometry = result['geometry']
        result['geometry'] = format_geojson(mapping(self.buffered_geometry))
        result['original_geometry'] = original_geometry
        return result

    def get_geojson_properties(self):
        result = super().get_geojson_properties()
        result['width'] = float(self.width)
        return result