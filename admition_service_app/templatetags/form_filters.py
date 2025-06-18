# myapp/templatetags/form_filters.py
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def field_type(field):
    return field.field.widget.__class__.__name__.lower()


@register.filter(name='add_class')
def add_class(field, css_class):
    return field.as_widget(attrs={'class': css_class, 'placeholder': field.label})

@register.filter(name='floating_input')
def floating_input(field):
    attrs = {
        'class': 'form-control',
        'placeholder': field.label or field.name
    }
    return field.as_widget(attrs=attrs)