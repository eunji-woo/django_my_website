from django.shortcuts import render, redirect


def index(request):
    return redirect('/blog/')

