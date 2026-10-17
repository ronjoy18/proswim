from decimal import Decimal
from django.conf import settings
from django.core.mail import send_mail
from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver
from .models import ClientProfile, CoachProfile, Order, ReferralLedger, User, Announcement
from django.core.mail import EmailMultiAlternatives

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

#@receiver(post_save, sender=Order)
#def order_post_save_handler(sender, instance, created, **kwargs):
    # Only run when a new order is created or when marked as paid
    #if created:
  #     subject = f"Booking Confirmation: #{instance.id}"
   #     message = (
    #        f"Hello {instance.user.username},\n\n"
     #       f"Your swimming session request #{instance.id} has been registered.\n"
      #      "Thank you for choosing Proswim Academy!"
       # )
        #recipient_list = [instance.user.email]

        #try:
         #   send_mail(
          #      subject=subject,
           #     message=message,
            #    from_email=settings.DEFAULT_FROM_EMAIL,
             #   recipient_list=recipient_list,
              #  fail_silently=True,
            #)
        #except Exception as e:
         #   print(f"[EMAIL ERROR] Failed to send order email: {e}")

        # 2. Create In-App Notification / Announcement
        # If you have an Announcement or Notification table:
        #Announcement.objects.create(
         #   title="New Order Received",
         #   content=f"Order #{instance.id} registered for {instance.user.username}."
        #)               

#@receiver(post_save, sender=Order)
#def user_creation_notification(sender, instance, created, **kwargs):
 #   if created:
  #      link =f"https://proswim.onrender.com/dashboard/"
   #     subject = f"account created:{instance.user.get_full_name()}"
    #    message= (
     #       f"Hello {instance.user.username}"
      #      f"your proswim account was succefully created, you can click {link} to book services."
       #     f"wish you the best in your swiming journey"
#        #    f"swim like a pro"
 #       )
  #      recipient_list= [instance.user.email]
#
 #       try:
  #          send_mail(
   #             subject=subject,
    #            message=message,
     #           from_email=settings.DEFAULT_FROM_EMAIL,
      #          recipient_list=recipient_list,
       #         fail_silently=True,
        #        )
#        except Exception as e:
 #                   print(f"[EMAIL ERROR] Failed to send order email: {e}")
#
 #       Announcement.objects.create(
  #                  title="New client signed in",
   #                 content=f"Name:{instance.user.get_full_name}, username:{instance.user.username}."
    #            )
                      