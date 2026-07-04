from celery import shared_task


@shared_task
def deactivate_inactive_users():
    """
    Auto-deactivation disabled.

    We no longer deactivate users automatically because it
    prevents legitimate users from logging in.
    """
    return "Auto-deactivation is disabled."