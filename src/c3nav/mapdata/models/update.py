import logging
import os
import pickle
from contextlib import contextmanager, suppress

from django.conf import settings
from django.core.cache import cache
from django.db import models, transaction
from django.utils.http import int_to_base36
from django.utils.timezone import make_naive
from django.utils.translation import ugettext_lazy as _

from c3nav.mapdata.tasks import process_map_updates


class MapUpdate(models.Model):
    """
    A map update. created whenever mapdata is changed.
    """
    datetime = models.DateTimeField(auto_now_add=True, db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT)
    type = models.CharField(max_length=32)
    processed = models.BooleanField(default=False)

    class Meta:
        verbose_name = _('Map update')
        verbose_name_plural = _('Map updates')
        default_related_name = 'mapupdates'
        get_latest_by = 'datetime'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.was_processed = self.processed

    @classmethod
    def last_update(cls):
        last_update = cache.get('mapdata:last_update', None)
        if last_update is not None:
            return last_update
        with cls.lock():
            last_update = cls.objects.latest()
            result = last_update.to_tuple
            cache.set('mapdata:last_update', result, 60)
        return result

    @classmethod
    def last_processed_update(cls):
        last_processed_update = cache.get('mapdata:last_processed_update', None)
        if last_processed_update is not None:
            return last_processed_update
        with cls.lock():
            last_processed_update = cls.objects.filter(processed=True).latest()
            result = last_processed_update.to_tuple
            cache.set('mapdata:last_processed_update', result, 60)
        return result

    @property
    def to_tuple(self):
        return self.pk, int(make_naive(self.datetime).timestamp())

    @property
    def cache_key(self):
        return self.build_cache_key(self.pk, int(make_naive(self.datetime).timestamp()))

    @classmethod
    def current_cache_key(cls, request=None):
        return cls.build_cache_key(*cls.last_update())

    @classmethod
    def current_processed_cache_key(cls, request=None):
        return cls.build_cache_key(*cls.last_processed_update())

    @staticmethod
    def build_cache_key(pk, timestamp):
        return int_to_base36(pk)+'_'+int_to_base36(timestamp)

    @classmethod
    @contextmanager
    def lock(cls):
        with transaction.atomic():
            yield cls.objects.select_for_update().earliest()

    def _changed_geometries_filename(self):
        return os.path.join(settings.CACHE_ROOT, 'changed_geometries', 'update_%d.pickle' % self.pk)

    @classmethod
    def process_updates(cls):
        logger = logging.getLogger('c3nav')

        with transaction.atomic():
            new_updates = tuple(cls.objects.filter(processed=False).select_for_update(nowait=True))
            if not new_updates:
                return ()

            from c3nav.mapdata.utils.cache.changes import changed_geometries
            changed_geometries.reset()

            logger.info('Recalculating altitude areas...')

            from c3nav.mapdata.models import AltitudeArea
            AltitudeArea.recalculate()

            logger.info('%.3f m² of altitude areas affected.' % changed_geometries.area)

            last_processed_update = cls.objects.filter(processed=True).latest().to_tuple

            for new_update in new_updates:
                logger.info('Applying changed geometries from MapUpdate #%(id)s (%(type)s)...' %
                            {'id': new_update.pk, 'type': new_update.type})
                try:
                    new_changes = pickle.load(open(new_update._changed_geometries_filename(), 'rb'))
                except FileNotFoundError:
                    logger.warning('changed_geometries pickle file not found.')
                else:
                    logger.info('%.3f m² affected by this update.' % new_changes.area)
                    changed_geometries.combine(new_changes)
                new_update.processed = True
                new_update.save()

            logger.info('%.3f m² of geometries affected in total.' % changed_geometries.area)

            changed_geometries.save(last_processed_update, new_updates[-1].to_tuple)

            logger.info('Rebuilding level render data...')

            from c3nav.mapdata.render.renderdata import LevelRenderData
            LevelRenderData.rebuild()

            logger.info('Rebuilding router...')
            from c3nav.routing.router import Router
            Router.rebuild()

            transaction.on_commit(
                lambda: cache.delete('mapdata:last_processed_update')
            )

            return new_updates

    def save(self, **kwargs):
        new = self.pk is None
        if not new and (self.was_processed or not self.processed):
            raise TypeError

        super().save(**kwargs)

        with suppress(FileExistsError):
            os.mkdir(os.path.dirname(self._changed_geometries_filename()))

        from c3nav.mapdata.utils.cache.changes import changed_geometries
        pickle.dump(changed_geometries, open(self._changed_geometries_filename(), 'wb'))

        if new:
            transaction.on_commit(
                lambda: cache.delete('mapdata:last_update')
            )
            if settings.HAS_CELERY:
                transaction.on_commit(
                    lambda: process_map_updates.delay()
                )
