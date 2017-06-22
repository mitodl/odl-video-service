"""
Views for cloudsync app
"""
from celery.result import AsyncResult
from django.http import JsonResponse


def status(request, task_id):  # pylint: disable=unused-argument
    """
    Returns the status of a task
    """
    result = AsyncResult(task_id)
    if isinstance(result.info, Exception):
        return JsonResponse({
            "status": result.state,
            "exception": result.info.__class__.__name__,
            "args": result.info.args,
        })
    return JsonResponse({
        "status": result.state,
        "info": result.info,
    })
