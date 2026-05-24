from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404

from .models import Review
from .serializers import ReviewSerializer
from .tasks import analyze_pull_request


@api_view(["GET"])
def health_check(request):
    return Response({
        "status": "ok",
        "message": "Backend Running"
    })


@csrf_exempt
@api_view(["POST"])
def review_pr(request):
    diff_content = request.data.get("diff")
    repository_name = request.data.get("repository_name")
    pr_number = request.data.get("pr_number")

    if not diff_content:
        return Response({
            "error": "Diff content required"
        }, status=400)

    review = Review.objects.create(
        repository_name=repository_name,
        pr_number=pr_number,
        diff_content=diff_content,
        status="pending"
    )

    analyze_pull_request.delay(str(review.id))

    return Response({
        "review_id": review.id,
        "status": "pending"
    })


@api_view(["GET"])
def get_review(request, review_id):
    review = get_object_or_404(Review, id=review_id)
    serializer = ReviewSerializer(review)

    return Response(serializer.data)