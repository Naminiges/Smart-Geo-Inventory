from flask import render_template, current_app, url_for
from flask_mail import Message
from app import mail
import os


def get_base_url():
    """Get base URL for email links"""
    server_name = current_app.config.get('SERVER_NAME')
    if server_name:
        scheme = 'https' if current_app.config.get('SESSION_COOKIE_SECURE') else 'http'
        return f"{scheme}://{server_name}"
    # Fallback for development
    return 'http://192.168.100.17:5000'


def send_email(to, subject, template, **kwargs):
    """Send email using Flask-Mail

    Args:
        to: Recipient email address
        subject: Email subject
        template: Template name (without .html extension)
        **kwargs: Context variables for template
    """
    try:
        # Create a simple URL function for templates
        base_url = get_base_url()
        def email_url(endpoint, **values):
            if endpoint == 'procurement.index':
                return f"{base_url}/procurement/"
            elif endpoint == 'procurement.detail' and 'id' in values:
                return f"{base_url}/procurement/{values['id']}"
            elif endpoint == 'procurement.receive' and 'id' in values:
                return f"{base_url}/procurement/{values['id']}/receive"
            elif endpoint == 'stock.index':
                return f"{base_url}/stock/"
            elif endpoint == 'distributions.index':
                return f"{base_url}/distributions/"
            elif endpoint == 'distributions.detail' and 'id' in values:
                return f"{base_url}/distributions/{values['id']}"
            return f"{base_url}/"

        kwargs['url_for'] = email_url
        kwargs['base_url'] = base_url

        msg = Message(
            subject=subject,
            recipients=[to],
            html=render_template(f'emails/{template}.html', **kwargs)
        )
        mail.send(msg)
        current_app.logger.info(f'Email sent to {to}: {subject}')
        return True
    except Exception as e:
        current_app.logger.error(f'Failed to send email to {to}: {str(e)}')
        import traceback
        current_app.logger.error(traceback.format_exc())
        return False


def send_email_to_multiple(recipients, subject, template, **kwargs):
    """Send email to multiple recipients

    Args:
        recipients: List of email addresses
        subject: Email subject
        template: Template name (without .html extension)
        **kwargs: Context variables for template
    """
    try:
        # Create a simple URL function for templates
        base_url = get_base_url()
        def email_url(endpoint, **values):
            if endpoint == 'procurement.index':
                return f"{base_url}/procurement/"
            elif endpoint == 'procurement.detail' and 'id' in values:
                return f"{base_url}/procurement/{values['id']}"
            elif endpoint == 'procurement.receive' and 'id' in values:
                return f"{base_url}/procurement/{values['id']}/receive"
            elif endpoint == 'stock.index':
                return f"{base_url}/stock/"
            elif endpoint == 'distributions.index':
                return f"{base_url}/distributions/"
            elif endpoint == 'distributions.detail' and 'id' in values:
                return f"{base_url}/distributions/{values['id']}"
            return f"{base_url}/"

        kwargs['url_for'] = email_url
        kwargs['base_url'] = base_url

        msg = Message(
            subject=subject,
            recipients=recipients,
            html=render_template(f'emails/{template}.html', **kwargs)
        )
        mail.send(msg)
        current_app.logger.info(f'Email sent to {len(recipients)} recipients: {subject}')
        return True
    except Exception as e:
        current_app.logger.error(f'Failed to send email: {str(e)}')
        import traceback
        current_app.logger.error(traceback.format_exc())
        return False


# ==================== PROCUREMENT NOTIFICATIONS ====================

def notify_procurement_created(procurement):
    """Notify admin when warehouse staff creates a procurement request"""
    from app.models import User

    # Get all admin users who should receive notifications
    admins = User.query.filter_by(role='admin').all()
    admins = [admin for admin in admins if admin.should_receive_email_notifications()]

    if not admins:
        current_app.logger.warning('No active admin found to send procurement notification')
        return False

    recipients = [admin.email for admin in admins]

    return send_email_to_multiple(
        recipients=recipients,
        subject=f'[SAPA PSI] Pengadaan Baru Diajukan - {procurement.procurement_code}',
        template='procurement_created',
        procurement=procurement
    )


def notify_procurement_approved(procurement):
    """Notify warehouse staff when admin approves procurement"""
    creator = procurement.created_by_user

    if not creator or not creator.should_receive_email_notifications():
        return False

    return send_email(
        to=creator.email,
        subject=f'[SAPA PSI] Pengadaan Disetujui - {procurement.procurement_code}',
        template='procurement_approved',
        procurement=procurement
    )


def notify_procurement_rejected(procurement, rejection_reason=None):
    """Notify warehouse staff when admin rejects procurement"""
    creator = procurement.created_by_user

    if not creator or not creator.should_receive_email_notifications():
        return False

    return send_email(
        to=creator.email,
        subject=f'[SAPA PSI] Pengadaan Ditolak - {procurement.procurement_code}',
        template='procurement_rejected',
        procurement=procurement,
        rejection_reason=rejection_reason
    )


def notify_procurement_goods_received(procurement):
    """Notify admin when warehouse staff receives goods"""
    from app.models import User

    # Get all admin users who should receive notifications
    admins = User.query.filter_by(role='admin').all()
    admins = [admin for admin in admins if admin.should_receive_email_notifications()]

    if not admins:
        current_app.logger.warning('No active admin found to send notification')
        return False

    recipients = [admin.email for admin in admins]

    return send_email_to_multiple(
        recipients=recipients,
        subject=f'[SAPA PSI] Barang Diterima - {procurement.procurement_code}',
        template='procurement_goods_received',
        procurement=procurement
    )


def notify_procurement_completed(procurement):
    """Notify warehouse staff and admin when procurement is completed"""
    from app.models import User

    # Notify warehouse staff (creator)
    creator = procurement.created_by_user
    recipients = []

    if creator and creator.should_receive_email_notifications():
        recipients.append(creator.email)

    # Also notify all admins
    admins = User.query.filter_by(role='admin').all()
    for admin in admins:
        if admin.should_receive_email_notifications() and admin.email not in recipients:
            recipients.append(admin.email)

    if not recipients:
        current_app.logger.warning('No active users found to send notification')
        return False

    return send_email_to_multiple(
        recipients=recipients,
        subject=f'[SAPA PSI] Pengadaan Selesai - {procurement.procurement_code}',
        template='procurement_completed',
        procurement=procurement
    )


# ==================== DISTRIBUTION NOTIFICATIONS ====================

def notify_distribution_created(distribution):
    """Notify admin when warehouse staff creates distribution request"""
    from app.models import User

    if not distribution:
        return False

    # Get all admin users who should receive notifications
    admins = User.query.filter_by(role='admin').all()
    admins = [admin for admin in admins if admin.should_receive_email_notifications()]

    if not admins:
        current_app.logger.warning('No active admin found to send distribution notification')
        return False

    recipients = [admin.email for admin in admins]

    # Get distribution group info if available
    batch_code = ''
    if distribution.distribution_group:
        batch_code = distribution.distribution_group.batch_code

    return send_email_to_multiple(
        recipients=recipients,
        subject=f'[SAPA PSI] Distribusi Baru Diajukan - {batch_code or distribution.distribution_code}',
        template='distribution_created',
        distribution=distribution
    )


def notify_distribution_sent(distribution):
    """Notify unit staff when admin sends distribution"""
    from app.models import User
    from app.models import UserUnit

    # Get users assigned to this unit
    unit_users = []
    if distribution.unit:
        unit_users = User.query.join(
            UserUnit, User.id == UserUnit.user_id
        ).filter(
            UserUnit.unit_id == distribution.unit.id
        ).all()
        unit_users = [user for user in unit_users if user.should_receive_email_notifications()]

    if not unit_users:
        current_app.logger.warning(f'No active users found for unit {distribution.unit.name}')
        return False

    recipients = [user.email for user in unit_users]

    return send_email_to_multiple(
        recipients=recipients,
        subject=f'[SAPA PSI] Barang Ditujukan Ke Unit Anda - {distribution.distribution_code}',
        template='distribution_sent',
        distribution=distribution
    )


def notify_distribution_received(distribution):
    """Notify admin when unit staff receives distribution"""
    from app.models import User

    # Get all admin users who should receive notifications
    admins = User.query.filter_by(role='admin').all()
    admins = [admin for admin in admins if admin.should_receive_email_notifications()]

    if not admins:
        current_app.logger.warning('No active admin found to send distribution notification')
        return False

    recipients = [admin.email for admin in admins]

    return send_email_to_multiple(
        recipients=recipients,
        subject=f'[SAPA PSI] Barang Diterima Unit - {distribution.distribution_code}',
        template='distribution_received',
        distribution=distribution
    )


def notify_distribution_rejected(distribution, rejection_reason=None):
    """Notify warehouse staff when admin rejects distribution"""
    # Get draft creator (warehouse staff who created the draft)
    creator = distribution.draft_creator if distribution.draft_created_by else None

    if not creator or not creator.should_receive_email_notifications():
        return False

    batch_code = distribution.distribution_group.batch_code if distribution.distribution_group else distribution.distribution_code

    return send_email(
        to=creator.email,
        subject=f'[SAPA PSI] Distribusi Ditolak - {batch_code}',
        template='distribution_rejected',
        distribution=distribution,
        rejection_reason=rejection_reason
    )


# ==================== ASSET REQUEST NOTIFICATIONS ====================

def notify_asset_request_created(asset_request):
    """Notify admin when unit staff creates asset request"""
    from app.models import User

    # Get all admin users who should receive notifications
    admins = User.query.filter_by(role='admin').all()
    admins = [admin for admin in admins if admin.should_receive_email_notifications()]

    if not admins:
        current_app.logger.warning('No active admin found to send asset request notification')
        return False

    recipients = [admin.email for admin in admins]

    return send_email_to_multiple(
        recipients=recipients,
        subject=f'[SAPA PSI] Permohonan Aset Baru - #{asset_request.id}',
        template='asset_request_created',
        asset_request=asset_request
    )


def notify_asset_request_verified(asset_request):
    """Notify unit staff when admin verifies their request"""
    requester = asset_request.requester

    if not requester or not requester.should_receive_email_notifications():
        return False

    return send_email(
        to=requester.email,
        subject=f'[SAPA PSI] Permohonan Aset Terverifikasi - #{asset_request.id}',
        template='asset_request_verified',
        asset_request=asset_request
    )


def notify_asset_request_rejected(asset_request):
    """Notify unit staff when admin rejects their request"""
    requester = asset_request.requester

    if not requester or not requester.should_receive_email_notifications():
        return False

    return send_email(
        to=requester.email,
        subject=f'[SAPA PSI] Permohonan Aset Ditolak - #{asset_request.id}',
        template='asset_request_rejected',
        asset_request=asset_request
    )


def notify_asset_request_distributing(asset_request):
    """Notify unit staff when warehouse staff starts distribution"""
    requester = asset_request.requester

    if not requester or not requester.should_receive_email_notifications():
        return False

    return send_email(
        to=requester.email,
        subject=f'[SAPA PSI] Permohonan Aset Sedang Didistribusikan - #{asset_request.id}',
        template='asset_request_distributing',
        asset_request=asset_request
    )


def notify_asset_request_verified_to_warehouse(asset_request):
    """Notify warehouse staff when admin verifies asset request"""
    from app.models import User

    # Get all warehouse staff who should receive notifications
    warehouse_staff = User.query.filter_by(role='warehouse_staff').all()
    warehouse_staff = [ws for ws in warehouse_staff if ws.should_receive_email_notifications()]

    if not warehouse_staff:
        current_app.logger.warning('No active warehouse staff found to send notification')
        return False

    recipients = [ws.email for ws in warehouse_staff]

    return send_email_to_multiple(
        recipients=recipients,
        subject=f'[SAPA PSI] Permohonan Aset Terverifikasi - Silakan Distribusikan - #{asset_request.id}',
        template='asset_request_verified_warehouse',
        asset_request=asset_request
    )


def notify_asset_request_completed(asset_request, warehouse_staff_id=None):
    """Notify admin and relevant warehouse staff when unit confirms receipt"""
    from app.models import User

    recipients = []

    # Add admin
    admins = User.query.filter_by(role='admin').all()
    for admin in admins:
        if admin.should_receive_email_notifications():
            recipients.append(admin.email)

    # Add the warehouse staff who handled the distribution
    if warehouse_staff_id:
        warehouse_staff = User.query.get(warehouse_staff_id)
        if warehouse_staff and warehouse_staff.should_receive_email_notifications() and warehouse_staff.email not in recipients:
            recipients.append(warehouse_staff.email)

    if not recipients:
        current_app.logger.warning('No active users found to send completion notification')
        return False

    return send_email_to_multiple(
        recipients=recipients,
        subject=f'[SAPA PSI] Permohonan Aset Selesai - #{asset_request.id}',
        template='asset_request_completed',
        asset_request=asset_request
    )


# Import at the end to avoid circular dependency
from app.models import UserUnit
