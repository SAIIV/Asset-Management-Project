"""{% advice_card asset %}: the AI #3 card on the asset page, kept in the ai app."""

from django import template

register = template.Library()


@register.inclusion_tag("ai/_advice.html", takes_context=True)
def advice_card(context, asset):
    from ..advice import load_advice
    from ..models import AIRecord

    request = context["request"]
    advice, answered = None, None
    record_id = request.GET.get("advice", "")
    if record_id.isdigit():
        advice = load_advice(int(record_id), asset)
        if advice is not None:
            answered = AIRecord.objects.filter(pk=advice.record_id).values_list("decision", flat=True).first()
    return {"asset": asset, "advice": advice, "answered": answered, "csrf_token": context.get("csrf_token"),
            "request": request}
