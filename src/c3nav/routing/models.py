import threading
from collections import OrderedDict

from django import forms
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext_lazy as _

from c3nav.mapdata.fields import JSONField
from c3nav.mapdata.models import MapUpdate, WayType


class RouteOptions(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, primary_key=True)
    data = JSONField(default={})

    class Meta:
        verbose_name = _('Route options')
        verbose_name_plural = _('Route options')
        default_related_name = 'routeoptions'

    fields_cached = None
    fields_cache_key = None
    fields_cache_lock = threading.Lock()

    @classmethod
    def build_fields(cls):
        fields = OrderedDict()
        fields['walk_speed'] = forms.ChoiceField(
            label=_('Walk speed'),
            choices=(('slow', _('slow')), ('default', _('default')), ('fast', _('fast'))),
            initial='default'
        )

        for waytype in WayType.objects.all():
            choices = []
            choices.append(('allow', _('allow')))
            if waytype.up_separate:
                choices.append(('avoid_up', _('avoid upwards')))
                choices.append(('avoid_down', _('avoid downwards')))
                choices.append(('avoid', _('avoid completely')))
            else:
                choices.append(('avoid', _('avoid')))
            fields['waytype_%d' % waytype.pk] = forms.ChoiceField(
                label=waytype.title_plural,
                choices=tuple(choices),
                initial='allow'
            )

        return fields

    @classmethod
    def get_fields(cls):
        cache_key = MapUpdate.current_cache_key()
        if cls.fields_cache_key != cache_key:
            with cls.fields_cache_lock:
                cls.fields_cache_key = cache_key
                cls.fields_cached = cls.build_fields()
        return cls.fields_cached

    @staticmethod
    def get_cache_key(pk):
        return 'routing:options:user:%d' % pk

    @classmethod
    def get_for_user(cls, user):
        cache_key = cls.get_cache_key(user.pk)
        result = cache.get(cache_key, None)
        if result:
            return result

        try:
            result = user.routeoptions
        except AttributeError:
            result = None

        if result:
            cache.set(cache_key, result, 900)

        return result

    @classmethod
    def get_for_request(cls, request):
        session_options = request.session.get('route_options', None)
        user_options = None
        if request.user.is_authenticated:
            user_options = cls.get_for_user(request.user)

        if session_options and not user_options:
            user_options = session_options
            user_options.user = request.user
            user_options.save()
            request.session.pop('session_options')

        options = cls(request=request)
        options.update(user_options or session_options or {}, ignore_errors=True)
        return options

    def __init__(self, *args, request=None, **kwargs):
        super().__init__(*args, **kwargs)
        new_data = OrderedDict()
        for name, field in self.get_fields().items():
            value = self.data.get(name)
            if value is None or value not in dict(field.choices):
                value = field.initial
            new_data[name] = value
        self.data = new_data

        self.request = request

    def __getitem__(self, key):
        try:
            return self.data[key]
        except AttributeError:
            return self.get_fields()[key].initial

    def update(self, value_dict, ignore_errors=False):
        if not value_dict:
            return
        fields = self.get_fields()
        for key, value in value_dict.items():
            field = fields.get(key)
            if not field:
                if ignore_errors:
                    continue
                raise ValidationError(_('Unknown route option: %s') % key)
            if value is None or value not in dict(field.choices):
                if ignore_errors:
                    continue
                raise ValidationError(_('Invalid value for route option %s.') % key)
            self.data[key] = value

    def __setitem__(self, key, value):
        self.update({key: value})

    def save(self, *args, **kwargs):
        if self.request is None or self.request.user.is_authenticated:
            self.user = self.request.user
            super().save(*args, **kwargs)

        self.request.session['route_options'] = self
