import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime
from zoneinfo import ZoneInfo
from django.shortcuts import render
from django.core.paginator import Paginator
from .models import HealthData, EmotionData


def _parse_and_validate_sample(sample: dict) -> tuple | None:
    try:
        timestamp_ms = sample.get("ts")
        type = sample.get("type")
        value = sample.get("value")

        # timestamp or value should not be None
        if timestamp_ms is None or value is None:
            return None

        # Convert to float first for broader compatibility
        timestamp_ms = float(timestamp_ms)
        type = str(type)
        value = float(value)

        # convert to ist datetime
        ist_datetime = datetime.fromtimestamp(
            timestamp_ms / 1000, tz=ZoneInfo("Asia/Kolkata")
        )
        return ist_datetime, type, value

    except (ValueError, TypeError):
        # Handle cases where ts or value are not valid numbers
        return None


@csrf_exempt
def upload_health_data(request):
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
        userid = request.POST.get("userid")

        # Ensure the JSON is a dictionary with the correct type
        if not isinstance(data, dict) or data.get("type") != "health_data_batch":
            return JsonResponse({"error": "Invalid JSON format or type."}, status=400)

        samples = data.get("samples", [])
        if not isinstance(samples, list):
            return JsonResponse(
                {"error": "Invalid 'samples' format. It must be a list."}, status=400
            )

        record_count = 0

        for sample in samples:
            parsed_data = _parse_and_validate_sample(sample)
            if parsed_data:
                timestamp, type, value = parsed_data
                HealthData.objects.create(
                    userId=userid,
                    timestamp=timestamp,
                    type=type,
                    value=value,
                )
                record_count += 1

        # apply processing logic as needed for the collected physiological data
        # get a decision in boolean and then return it to the user 0 for not opportune, 1 for opportune
        decision_opportune = True  # Placeholder for actual decision logic

        return JsonResponse(
            {
                "message": f"Successfully processed {record_count} records.",
                "opportune": decision_opportune,
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


@csrf_exempt
def upload_emotion_json(request):
    if request.method != "POST":
        return JsonResponse(
            {"error": "Invalid request. Use POST method."},
            status=400,
        )

    try:
        # Parse raw JSON data from request body
        data = json.loads(request.body)

        # Extract required fields from single emotion object
        userid = data.get("userid")
        timestamp_ms = data.get("timestamp")
        valence = data.get("valence")
        arousal = data.get("arousal")
        type = data.get("type")

        # Validate all required fields are present
        if not all([userid, timestamp_ms, valence is not None, arousal is not None]):
            return JsonResponse(
                {
                    "error": "Missing required fields. Need: userid, timestamp, valence, arousal"
                },
                status=400,
            )

        # Convert and validate userid
        userid = str(userid)
        type = str(type)

        # Convert and validate valence and arousal
        valence = float(valence)
        arousal = float(arousal)

        # get timestamp
        ist_datetime = datetime.fromtimestamp(
            timestamp_ms / 1000, tz=ZoneInfo("Asia/Kolkata")
        )

        # Validate valence and arousal are in range 0-5
        if not (0.0 <= valence <= 5.0) or not (0.0 <= arousal <= 5.0):
            return JsonResponse(
                {"error": "Valence and arousal values must be between 0.0 and 5.0"},
                status=400,
            )

        # Create database record
        record = EmotionData.objects.create(
            userId=userid,
            timestamp=ist_datetime,
            valence=valence,
            arousal=arousal,
            type=type,
        )

        return JsonResponse(
            {
                "message": "Successfully recorded emotion data.",
                "record_id": record.id,
                "processed_data": {
                    "userid": userid,
                    "timestamp": ist_datetime.isoformat(),
                    "valence": valence,
                    "arousal": arousal,
                    "type": type,
                },
            },
            status=201,
        )

    except json.JSONDecodeError:
        return JsonResponse(
            {"error": "Invalid JSON data. Could not decode."}, status=400
        )
    except ValueError as e:
        return JsonResponse({"error": f"Data validation error: {str(e)}"}, status=400)
    except Exception as e:
        # Generic catch-all for other unexpected errors
        return JsonResponse(
            {"error": f"An unexpected server error occurred: {str(e)}"}, status=500
        )


def display_data(request):
    """View to display heart rate data in a table format"""
    page_number = request.GET.get("page", 1)

    heart_rate_data = HealthData.objects.all().order_by("id")

    paginator = Paginator(heart_rate_data, 15)
    page_obj = paginator.get_page(page_number)

    unique_userids = (
        HealthData.objects.values_list("userId", flat=True)
        .distinct()
        .order_by("userId")
    )

    context = {
        "page_obj": page_obj,
        "unique_userids": unique_userids,
        "total_records": heart_rate_data.count(),
    }

    return render(request, "uploader/home.html", context)


def display_emotion_data(request):
    """View to display emotion data in a table format"""
    page_number = request.GET.get("page", 1)

    emotion_data = EmotionData.objects.all().order_by("id")

    paginator = Paginator(emotion_data, 15)
    page_obj = paginator.get_page(page_number)

    unique_userids = (
        EmotionData.objects.values_list("userId", flat=True)
        .distinct()
        .order_by("userId")
    )

    context = {
        "page_obj": page_obj,
        "unique_userids": unique_userids,
        "total_records": emotion_data.count(),
    }

    return render(request, "uploader/emotion.html", context)
