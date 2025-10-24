import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime
from zoneinfo import ZoneInfo
from django.shortcuts import render
from django.core.paginator import Paginator
from .models import UploadedJSON as HeartRateData, EmotionData


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


def _parse_and_validate_emotion_sample(sample: dict) -> tuple | None:
    """
    Parses a single emotion sample dictionary, validates its contents,
    and converts the timestamp to a timezone-aware datetime object.
    Returns a tuple of (datetime, valence, arousal) or None if the sample is invalid.
    """
    try:
        timestamp_ms = sample.get("ts")
        valence = sample.get("valence")
        arousal = sample.get("arousal")

        # timestamp, valence, or arousal should not be None
        if timestamp_ms is None or valence is None or arousal is None:
            return None

        # Convert to float for compatibility
        timestamp_ms = float(timestamp_ms)
        valence = float(valence)
        arousal = float(arousal)

        # Validate valence and arousal are in range 0-5
        if not (0.0 <= valence <= 5.0) or not (0.0 <= arousal <= 5.0):
            return None

        # convert to ist datetime
        ist_datetime = datetime.fromtimestamp(
            timestamp_ms / 1000, tz=ZoneInfo("Asia/Kolkata")
        )
        return ist_datetime, valence, arousal

    except (ValueError, TypeError):
        # Handle cases where values are not valid numbers
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


@csrf_exempt
def upload_emotion_json(request):
    """
    Handles POST requests with raw JSON data containing single emotion data (valence & arousal),
    processes the data, and saves it to the database.
    """
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
        timestamp_str = data.get("timestamp")
        type = data.get("type", "periodic")
        valence = data.get("valence")
        arousal = data.get("arousal")

        # Validate all required fields are present
        if not all([userid, timestamp_str, valence is not None, arousal is not None]):
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

        # Validate valence and arousal are in range 0-5
        if not (0.0 <= valence <= 5.0) or not (0.0 <= arousal <= 5.0):
            return JsonResponse(
                {"error": "Valence and arousal values must be between 0.0 and 5.0"},
                status=400,
            )

        # Parse timestamp
        try:
            if isinstance(timestamp_str, str):
                # Handle ISO format timestamps
                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                # Convert to IST timezone
                ist_timezone = ZoneInfo("Asia/Kolkata")
                timestamp = timestamp.astimezone(ist_timezone)
            else:
                return JsonResponse(
                    {
                        "error": "Timestamp must be in ISO format (e.g., '2025-10-21T11:15:00Z')"
                    },
                    status=400,
                )
        except ValueError:
            return JsonResponse(
                {
                    "error": "Invalid timestamp format. Use ISO format (e.g., '2025-10-21T11:15:00Z')"
                },
                status=400,
            )

        # Create database record
        record = EmotionData.objects.create(
            userId=userid,
            timestamp=timestamp,
            valence=valence,
            arousal=arousal,
        )

        # Apply processing logic as needed for the collected emotion data
        # Get a decision in boolean and then return it to the user 0 for not opportune, 1 for opportune
        decision_opportune = True  # Placeholder for actual decision logic

        return JsonResponse(
            {
                "message": "Successfully processed emotion data.",
                "opportune": decision_opportune,
                "record_id": record.id,
                "processed_data": {
                    "userid": userid,
                    "timestamp": timestamp.isoformat(),
                    "valence": valence,
                    "arousal": arousal,
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
