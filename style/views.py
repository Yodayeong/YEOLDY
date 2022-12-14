from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Style, Style_Review, Photo
from .form import StyleForm, ReviewForm
from products.models import Products
from django.http import HttpResponse
from django.db.models import Q  # 검색 기능
from django.core import serializers
from django.core.serializers.json import DjangoJSONEncoder
from datetime import date, datetime, timedelta
from kakaopay.models import OrderListFinal
from django.http import JsonResponse
import json


def index(request):
    styles = Style.objects.order_by("-pk")
    context = {
        "styles": styles,
    }
    return render(request, "style/index.html", context)


@login_required
def create(request):
    if request.method == "POST":
        print(1)
        style_form = StyleForm(request.POST, request.FILES)
        if style_form.is_valid():
            style = style_form.save(commit=False)
            style.user = request.user
            style.save()
            for img in request.FILES.getlist("imgs"):
                photo = Photo()
                photo.style = style
                photo.image = img
                photo.save()

            now_orderlist = Style.objects.last()
            now_orderlist.orderlists = request.POST.getlist("orders", "")
            now_orderlist.save()
            return redirect("style:index")
    else:
        style_form = StyleForm()
        orderlists = OrderListFinal.objects.filter(user_id=request.user.pk)

        if len(orderlists) == 0:
            orderlist_objects = 0
        else:
            orderlist_final = []
            for orderlist in orderlists:
                if orderlist.product_pk not in orderlist_final:
                    orderlist_final.append(orderlist.product_pk)
            print(orderlist_final)

            orderlist_objects = []
            for orderlist in orderlist_final:
                object = Products.objects.get(pk=orderlist)
                orderlist_objects.append(object)

    context = {
        "style_form": style_form,
        "orderlists": orderlist_objects,
    }
    return render(request, "style/form.html", context)


# 구매한 내역이 없으면, 착용한 제품이 없습니다.


@login_required
def update(request, pk):
    style = Style.objects.get(id=pk)
    photo = style.photo_set.all()
    if request.user == style.user:
        if request.method == "POST":
            photo.delete()
            style_form = StyleForm(request.POST, request.FILES, instance=style)
            if style_form.is_valid():
                style_form.save()
                for img in request.FILES.getlist("imgs"):
                    photo = Photo()
                    photo.style = style
                    photo.image = img
                    photo.save()
                return redirect("style:detail", style.pk)

        else:
            style_form = StyleForm(instance=style)
        context = {
            "style_form": style_form,
            "style": style,
        }

        return render(request, "style/form.html", context)
    else:
        return redirect("style:detail", style.pk)


def detail(request, pk):
    style = Style.objects.get(pk=pk)
    style_hits = get_object_or_404(Style, pk=pk)
    style_image = style.photo_set.all()
    review_form = ReviewForm()
    reviews = style.style_review_set.all().order_by("-pk")
    style_tags = list(str(style.tag).split(", "))

    if len(style.orderlists) == 0:
        products = 0
    else:
        # string으로 받은 orderlists들을 int형으로 바꿔줌
        orderlist_final = []
        temp = ""
        for i in range(len(style.orderlists)):
            if (
                style.orderlists[i] != ","
                and style.orderlists[i] != "'"
                and style.orderlists[i] != "["
                and style.orderlists[i] != " "
                and style.orderlists[i] != "]"
            ):
                temp += style.orderlists[i]
            if style.orderlists[i] == "," or style.orderlists[i] == "]":
                orderlist_final.append(temp)
                temp = ""
        orderlist = list(map(int, orderlist_final))
        products = []
        for id in orderlist:
            product = Products.objects.get(pk=id)
            products.append(product)

    context = {
        "style": style,
        "review_form": review_form,
        "reviews": reviews,
        "style_images": style_image,
        "style_tags": style_tags,
        "products": products
        # "orderlists": orderlists,
    }
    response = render(request, "style/detail.html", context)

    expire_date, now = datetime.now(), datetime.now()
    expire_date += timedelta(days=1)
    expire_date = expire_date.replace(hour=0, minute=0, second=0, microsecond=0)
    expire_date -= now
    max_age = expire_date.total_seconds()

    cookie_value = request.COOKIES.get("hitboard_2", "_")

    if f"_{pk}_" not in cookie_value:
        cookie_value += f"{pk}_"
        response.set_cookie(
            "hitboard_2", value=cookie_value, max_age=max_age, httponly=True
        )
        style_hits.hits += 1
        style_hits.save()
    return response


@login_required
def delete(request, pk):
    style = Style.objects.get(pk=pk)
    if request.user == style.user:
        style.delete()
        return redirect("style:index")
    else:
        return redirect("style:detail", pk)


# @login_required
# def review_create(request, pk):
#     if request.method == "POST":
#         style = Style.objects.get(pk=pk)
#         review_form = ReviewForm(request.POST)
#         if review_form.is_valid():
#             review = review_form.save(commit=False)
#             review.user = request.user
#             review.style = style
#             review.save()
#             return redirect("style:detail", style.pk)


@login_required
def review_create(request, pk):
    style = get_object_or_404(Style, id=pk)
    user = request.POST.get("user")
    content = request.POST.get("content")
    if content:
        review = Style_Review.objects.create(
            style=style,
            content=content,
            user=request.user,
        )
        style.save()
        data = {
            "user": user,
            "content": content,
            "created": "방금 전",
            "review_id": review.id,
        }
        if request.user == style.user:
            data["self_comment"] = "(작성자)"

        return HttpResponse(
            json.dumps(data, cls=DjangoJSONEncoder), content_type="application/json"
        )


@login_required
def review_delete(request, pk):
    style = get_object_or_404(Style, id=pk)
    review_id = request.POST.get("review_id")
    target_review = Style_Review.objects.get(pk=review_id)

    if (
        request.user == target_review.user
        or request.user.level == "1"
        or request.user.level == "0"
    ):
        target_review.deleted = True
        target_review.save()
        style.save()
        data = {
            "review_id": review_id,
        }
        return HttpResponse(
            json.dumps(data, cls=DjangoJSONEncoder), content_type="application/json"
        )


@login_required
def like(request, style_pk):
    style = Style.objects.get(pk=style_pk)

    if request.user in style.like_users.all():
        style.like_users.remove(request.user)
        is_liked = False
    else:
        style.like_users.add(request.user)
        is_liked = True
    context = {"isliked": is_liked}
    return JsonResponse(context)
