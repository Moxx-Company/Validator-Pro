import sys
sys.path.append('.')
from database import SessionLocal
from models import Subscription
import datetime

# Check webhook logs for the pending payment
with SessionLocal() as db:
    sub = db.query(Subscription).filter(Subscription.id == 7).first()
    if sub:
        print(f'Subscription #{sub.id} details:')
        print(f'  Status: {sub.status}')
        print(f'  Created: {sub.created_at}')
        print(f'  Address: {sub.payment_address}')
        print(f'  Currency: {sub.payment_currency_crypto}')
        print(f'  Amount: {sub.payment_amount_crypto} {sub.payment_currency_crypto}')
        print(f'  USD Value: ${sub.amount_usd}')
        
        # Calculate time since creation
        time_diff = datetime.datetime.utcnow() - sub.created_at
        minutes = int(time_diff.total_seconds() / 60)
        print(f'  Time since creation: {minutes} minutes ago')