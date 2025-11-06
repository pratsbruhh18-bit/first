from django import template

register = template.Library()

@register.filter
def has_role(user, roles):
    """
    Usage:
    {% if user|has_role:"admin,supervisor,hod" %}
    """
    if not hasattr(user, "role"):
        return False
    return user.role in roles.split(',')
