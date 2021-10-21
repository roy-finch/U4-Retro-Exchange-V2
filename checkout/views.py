import json

from django.shortcuts import render, reverse, redirect
from django.contrib import messages
from django.conf import settings

import stripe

from products.models import Product
from basket.contexts import basket_contents
from .forms import OrderForm
from .models import Order_Items


def checkout(request):
    """
    This sets up the form for checking out
    and also sets up the stripe payment and view
    """
    stripe_public_key = settings.STRIPE_PUBLIC_KEY
    stripe_secret_key = settings.STRIPE_SECRET_KEY
    basket = request.session.get("basket", [])

    if request.method == "POST":
        form_data = {
            "full_name": request.POST["full_name"],
            "email": request.POST["email"],
            "phone_number": request.POST["phone_number"],
            "country": request.POST["country"],
            "county": request.POST["county"],
            "town_r_city": request.POST["town_r_city"],
            "street_add_line1": request.POST["street_add_line1"],
            "street_add_line2": request.POST["street_add_line2"],
            "postcode": request.POST["postcode"],
        }
        order_form = OrderForm(form_data)
        if order_form.is_valid():
            order = order_form.save(commit=False)
            pid = request.POST.get("client_key").split("_secret")[0]
            order.stripe_pid = pid
            order.original_basket = json.dumps(basket)
            order.save()
            for i in range(0, len(basket)):
                try:
                    product = Product.objects.get(id=basket[i]["pk"])
                    if isinstance(basket[i]["quantity"], int):
                        indiv_items = Order_Items(
                            order=order,
                            product=product,
                            quantity=basket[i]["quantity"],
                            indiv_item_total=(
                                basket[i]["price"]*basket[i]["quantity"])
                        )
                        indiv_items.save()
                except Product.DoesNotExist:
                    messages.error(request, (
                        "One of the items wasn't found,"
                        "please contact us for more information."))
                    order.delete()
                    return redirect(reverse("view_bag"))

            request.session["save_order"] = "save-order" in request.POST
            return redirect(reverse(
                "checkout_success", args=[order.order_number]))

        else:
            messages.error(request, ("Error, problem with form"))
    else:
        if not basket:
            messages.error(request, "Theres nothing in your basket the moment")
            return redirect(reverse("products"))
        current_basket = basket_contents(request)
        total = current_basket["grand_total"]
        stripe_total = round(total * 100)
        stripe.api_key = stripe_secret_key
        intent = stripe.PaymentIntent.create(
            amount=stripe_total,
            currency=settings.STRIPE_CURRENCY
        )

    if not stripe_public_key or not stripe_secret_key:
        messages.warning(request, "Stripe key is not set.")

    order_form = OrderForm()
    template = "checkout/checkout.html"
    context = {
        "order_form": order_form,
        "stripe_public_key": stripe_public_key,
        "client_key": intent.client_secret,
    }

    return render(request, template, context)
