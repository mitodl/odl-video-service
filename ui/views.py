import json
from django.views.decorators.http import require_POST
from django.shortcuts import render
from django.http import JsonResponse
from cloudsync.tasks import stream_to_s3


def index(request):
    return render(request, "index.html")


@require_POST
def stream(request):
    db_files = json.loads(request.body.decode('utf-8'))
    results = {
        db_file['name']: stream_to_s3.delay(db_file['link'])
        for db_file in db_files
    }
    return JsonResponse({
        name: result.id
        for name, result in results.items()
    })
