import datetime


def year(request):
    dt_now = datetime.datetime.now().year
    """Добавляет переменную с текущим годом."""
    return {
        'year': dt_now,
    }
