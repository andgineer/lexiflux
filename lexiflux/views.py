from django.core.paginator import Paginator
from django.shortcuts import render
from .models import BookPage


def articles(request):
    """
    Fetch paginated articles and render them.
    """
    page_number = request.GET.get('page', 1)
    paginator = Paginator(BookPage.objects.all(), 2)
    page_obj = paginator.get_page(page_number)

    return render(request, 'book.html', {'page_obj': page_obj})
