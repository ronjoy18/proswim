from decimal import Decimal
from django.conf import settings
from django.core.mail import send_mail
from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver
from .models import ClientProfile, CoachProfile, Order, ReferralLedger, User


@receiver(post_save, sender=User)
def auto_create_user_profile(sender, instance, created, **kwargs):
    if created:
        if instance.role == User.Role.CLIENT:
            ClientProfile.objects.get_or_create(user=instance)
        elif instance.role == User.Role.COACH:
            CoachProfile.objects.get_or_create(user=instance)


@receiver(m2m_changed, sender=Order.activity.through)
def calculate_order_total_on_service_change(sender, instance, action, **kwargs):
    if action in ["post_add", "post_remove", "post_clear"]:
        total = instance.calculate_cost()
        if instance.total_cost != total:
            instance.total_cost = total
            instance.save(update_fields=["total_cost"])


@receiver(post_save, sender=Order)
def process_order_lifecycle(sender, instance, created, **kwargs):
    if instance.is_paid and instance.status == Order.Status.PENDING:
        Order.objects.filter(id=instance.id).update(status=Order.Status.PAID)

        client = instance.client
        if client.referred_by:
            prior_paid = Order.objects.filter(client=client, is_paid=True).exclude(id=instance.id).exists()
            if not prior_paid:
                referrer = client.referred_by
                bonus = Decimal("10.00")
                referrer.promo_credits += bonus
                referrer.save(update_fields=["promo_credits"])

                ReferralLedger.objects.create(
                    referrer=referrer,
                    referred_client=client,
                    order=instance,
                    bonus_amount=bonus
                )