from datetime import datetime, date, timedelta
import pytz
import re

IST = pytz.timezone("Asia/Kolkata")

def resolve_time_expression(expression: str, reference_dt: datetime = None) -> dict:
    """
    Resolves natural language time references ('today', 'yesterday', 'this morning')
    calibrated to Indian Standard Time (IST).
    """
    if reference_dt is None:
        now_ist = datetime.now(IST)
    else:
        now_ist = reference_dt.astimezone(IST)

    expr = expression.strip().lower()

    if "today" in expr:
        target_date = now_ist.date()
    elif "yesterday" in expr:
        target_date = now_ist.date() - timedelta(days=1)
    elif "last monday" in expr:
        days_behind = (now_ist.weekday() - 0) % 7 or 7
        target_date = now_ist.date() - timedelta(days=days_behind)
    elif "last friday" in expr:
        days_behind = (now_ist.weekday() - 4) % 7 or 7
        target_date = now_ist.date() - timedelta(days=days_behind)
    else:
        # Check for YYYY-MM-DD pattern
        match = re.search(r'\d{4}-\d{2}-\d{2}', expr)
        if match:
            target_date = datetime.strptime(match.group(0), "%Y-%m-%d").date()
        else:
            target_date = now_ist.date()

    start_dt = IST.localize(datetime.combine(target_date, datetime.min.time()))
    end_dt = IST.localize(datetime.combine(target_date, datetime.max.time()))

    return {
        "input_expression": expression,
        "resolved_date": target_date.isoformat(),
        "start_ist": start_dt.isoformat(),
        "end_ist": end_dt.isoformat(),
        "timezone": "Asia/Kolkata"
    }
