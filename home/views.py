from django.shortcuts import render


def index(request):
    """ A view for the index page, """
    return render(request, "home/index.html")
