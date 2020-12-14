"""
Views for cloudsync app
"""
from celery.result import AsyncResult
from rest_framework.response import Response
from rest_framework.views import APIView


class CeleryTaskStatus(APIView):
    """
    Class based view for checking status of celery tasks.
    """

    def get(self, request, task_id):  # pylint: disable=unused-argument
        """
        Returns the status of a task
        """
        result = AsyncResult(task_id)
        if isinstance(result.info, Exception):
            return Response(
                {
                    "status": result.state,
                    "exception": result.info.__class__.__name__,
                    "args": result.info.args,
                }
            )
        return Response(
            {
                "status": result.state,
                "info": result.info,
            }
        )
