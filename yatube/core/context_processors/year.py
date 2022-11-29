from django.utils import timezone


def year(request):
    dt_now = timezone.now().year
    """Добавляет переменную с текущим годом."""
    return {
        'year': dt_now,
    }
