from celery.result import AsyncResult
from django.http import JsonResponse


def status(request, task_id):
    result = AsyncResult(task_id)
    return JsonResponse({
        "status": result.state,
        "info": result.info,
    })
