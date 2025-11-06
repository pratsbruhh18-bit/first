from celery import shared_task
from django.core.mail import send_mail
from django.utils import timezone
from django.conf import settings
from .models import Task
import logging

logger = logging.getLogger(__name__)

@shared_task
def send_due_soon_reminders():
    """
    Sends reminder emails for all tasks due within 24 hours
    to both creators (user) and assigned users.
    """
    now = timezone.now().date()  # match your DateField precision
    soon = now + timezone.timedelta(days=1)

    tasks_due_soon = (
        Task.objects.filter(
            completed=False,
            due_date__lte=soon,
            due_date__gte=now,
        )
        .select_related("user")
        .prefetch_related("assigned_to")
    )

    total_emails = 0
    total_tasks = 0

    for task in tasks_due_soon:
        # Skip if no due_date
        if not task.due_date:
            continue

        recipient_emails = set()

        # Add creator
        if task.user and task.user.email:
            recipient_emails.add(task.user.email)

        # Add assigned users
        for assignee in task.assigned_to.all():
            if assignee.email:
                recipient_emails.add(assignee.email)

        if not recipient_emails:
            logger.warning(f"⚠️ No valid emails for task '{task.title}'")
            continue

        subject = f"Reminder: Task '{task.title}' is due soon!"
        message = (
            f"Hello,\n\n"
            f"Your task '{task.title}' is due on {task.due_date.strftime('%Y-%m-%d')}.\n"
            f"Please make sure to complete it on time.\n\n"
            f"Regards,\nTask Manager System"
        )

        try:
            send_mail(
                subject,
                message,
                getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@taskmanager.local"),
                list(recipient_emails),
                fail_silently=False,
            )
            total_emails += len(recipient_emails)
            total_tasks += 1
            logger.info(f"✅ Sent reminder for '{task.title}' → {recipient_emails}")
        except Exception as e:
            logger.error(f"❌ Failed to send email for '{task.title}': {e}")

    logger.info(f"📨 {total_emails} emails sent for {total_tasks} due tasks.")
    return f"{total_emails} emails sent for {total_tasks} due tasks."
