from rest_framework.response import Response


def api_response(data=None, message="Request successful", success=True, status=200):
    return Response(
        {
            "success": success,
            "message": message,
            "data": data if data is not None else {},
        },
        status=status,
    )
