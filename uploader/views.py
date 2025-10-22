import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime
from zoneinfo import ZoneInfo
from django.shortcuts import render
from django.core.paginator import Paginator
from .models import UploadedJSON as HeartRateData


def _parse_and_validate_sample(sample: dict) -> tuple | None:
    """
    Parses a single sample dictionary, validates its contents,
    and converts the timestamp to a timezone-aware datetime object.
    Returns a tuple of (datetime, bpm) or None if the sample is invalid.
    """
    try:
        timestamp_ms = sample.get("ts")
        bpm = sample.get("bpm")

        # timestamp or bpm should not be None
        if timestamp_ms is None or bpm is None:
            return None

        # Convert to float first for broader compatibility
        timestamp_ms = float(timestamp_ms)
        bpm = float(bpm)

        # convert to ist datetime
        ist_datetime = datetime.fromtimestamp(
            timestamp_ms / 1000, tz=ZoneInfo("Asia/Kolkata")
        )
        return ist_datetime, bpm

    except (ValueError, TypeError):
        # Handle cases where ts or bpm are not valid numbers
        return None


@csrf_exempt
def upload_json(request):
    """
    Handles POST requests with a JSON file containing heart rate data,
    processes the data, and saves it to the database.
    """
    if request.method != "POST" or not request.FILES.get("file"):
        return JsonResponse(
            {"error": "Invalid request. Use POST and include a 'file' upload."},
            status=400,
        )

    try:
        json_file = request.FILES["file"]
        data = json.load(json_file)

        # Ensure the JSON is a dictionary with the correct type
        if not isinstance(data, dict) or data.get("type") != "heart_rate_batch":
            return JsonResponse({"error": "Invalid JSON format or type."}, status=400)

        samples = data.get("samples", [])
        if not isinstance(samples, list):
            return JsonResponse(
                {"error": "Invalid 'samples' format. It must be a list."}, status=400
            )

        # Use the provided userid or a default value, ensuring it's an integer
        default_userid = int(request.POST.get("userid", 999))

        created_records_ids = []

        for sample in samples:
            parsed_data = _parse_and_validate_sample(sample)
            if parsed_data:
                timestamp, bpm = parsed_data
                record = HeartRateData.objects.create(
                    userId=default_userid,
                    timestamp=timestamp,
                    hr=bpm,
                )
                created_records_ids.append(record.id)

        # apply processing logic as needed for the collected physiological data
        # get a decision in boolean and then return it to the user 0 for not opportune, 1 for opportune
        decision_opportune = True  # Placeholder for actual decision logic

        return JsonResponse(
            {
                "message": f"Successfully processed {len(created_records_ids)} records.",
                "opportune": decision_opportune,
                "records_created": len(created_records_ids),
                "record_ids": created_records_ids,
            },
            status=201,
        )

    except json.JSONDecodeError:
        return JsonResponse(
            {"error": "Invalid JSON file. Could not decode."}, status=400
        )
    except Exception as e:
        # Generic catch-all for other unexpected errors
        return JsonResponse(
            {"error": f"An unexpected server error occurred: {str(e)}"}, status=500
        )


def display_data(request):
    """View to display heart rate data in a table format"""
    page_number = request.GET.get("page", 1)

    heart_rate_data = HeartRateData.objects.all().order_by("id")

    paginator = Paginator(heart_rate_data, 15)
    page_obj = paginator.get_page(page_number)

    unique_userids = (
        HeartRateData.objects.values_list("userId", flat=True)
        .distinct()
        .order_by("userId")
    )

    context = {
        "page_obj": page_obj,
        "unique_userids": unique_userids,
        "total_records": heart_rate_data.count(),
    }

    return render(request, "uploader/home.html", context)
