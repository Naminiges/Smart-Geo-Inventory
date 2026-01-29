"""
Background Scheduler for Venue Loans
Automatically completes expired venue loans
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def process_venue_loans():
    """Process venue loans - start when time begins, complete when time ends"""
    from app import create_app, db
    from app.models import VenueLoan
    from app.utils.datetime_helper import get_wib_now

    with scheduler.app.app_context():
        try:
            # Get current time in WIB (since start_datetime/end_datetime are stored in WIB)
            now_wib = get_wib_now()
            logger.info(f'Running venue loan scheduler check at WIB: {now_wib}')

            # 1. Start approved loans when start time is reached
            loans_to_start = VenueLoan.query.filter(
                VenueLoan.status == 'approved',
                VenueLoan.start_datetime <= now_wib
            ).all()

            logger.info(f'Found {len(loans_to_start)} approved loans to start')

            started_count = 0
            for loan in loans_to_start:
                try:
                    logger.info(f'Attempting to start venue loan #{loan.id}, start_datetime: {loan.start_datetime}, now_wib: {now_wib}')
                    success, message = loan.start_loan()
                    if success:
                        started_count += 1
                        logger.info(f'Venue loan #{loan.id} started: {message}')
                    else:
                        logger.warning(f'Failed to start venue loan #{loan.id}: {message}')
                except Exception as e:
                    logger.error(f'Error starting venue loan #{loan.id}: {str(e)}')
                    db.session.rollback()

            # 2. Complete active loans when end time is reached
            loans_to_complete = VenueLoan.query.filter(
                VenueLoan.status == 'active',
                VenueLoan.end_datetime < now_wib
            ).all()

            logger.info(f'Found {len(loans_to_complete)} active loans to complete')

            completed_count = 0
            for loan in loans_to_complete:
                try:
                    success, message = loan.complete(auto=True)
                    if success:
                        completed_count += 1
                        logger.info(f'Venue loan #{loan.id} completed: {message}')
                    else:
                        logger.warning(f'Failed to complete venue loan #{loan.id}: {message}')
                except Exception as e:
                    logger.error(f'Error completing venue loan #{loan.id}: {str(e)}')
                    db.session.rollback()

            if started_count > 0 or completed_count > 0:
                logger.info(f'Venue loans processed: {started_count} started, {completed_count} completed')
            else:
                logger.info('No venue loans needed processing in this cycle')

        except Exception as e:
            logger.error(f'Error in process_venue_loans: {str(e)}')


def init_scheduler(app):
    """Initialize and start the scheduler"""
    import os
    # Skip if scheduler is disabled (for testing)
    if os.environ.get('DISABLE_SCHEDULER') == '1':
        logger.info('Scheduler disabled - skipping initialization')
        return

    global scheduler

    # Store app reference for context
    scheduler.app = app

    # Add job to run every 1 minute
    scheduler.add_job(
        func=process_venue_loans,
        trigger=IntervalTrigger(minutes=1),
        id='process_venue_loans',
        name='Process Venue Loans (Start & Complete)',
        replace_existing=True
    )

    # Start the scheduler (only if not already running)
    if not scheduler.running:
        scheduler.start()
        logger.info('Scheduler started - Venue loans will be processed every 1 minute')
    else:
        logger.info('Scheduler already running - skipping start')


def shutdown_scheduler():
    """Shutdown the scheduler"""
    global scheduler
    if scheduler.running:
        scheduler.shutdown()
        logger.info('Scheduler shutdown')
