"""Email templates for subscription expiry notifications."""

EXPIRY_SUBJECT_TEMPLATE = (
    "[Action Required] Your OpsConductor subscription expires in {days_remaining} day(s)"
)

EXPIRY_HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head><style>
  body {{ font-family: Arial, sans-serif; color: #333; }}
  .header {{ background: #1a56db; color: white; padding: 20px; }}
  .content {{ padding: 20px; }}
  .footer {{ font-size: 12px; color: #999; padding: 20px; }}
</style></head>
<body>
  <div class="header"><h2>Subscription Expiry Notice</h2></div>
  <div class="content">
    <p>Dear {tenant_name},</p>
    <p>Your OpsConductor/Pulse subscription <strong>{subscription_id}</strong>
       will expire in <strong>{days_remaining} day(s)</strong> on
       <strong>{term_end}</strong>.</p>
    <p>Current status: <strong>{status}</strong></p>
    <p>To avoid service interruption, please renew your subscription before the expiry date.</p>
    <p>If you have questions, please contact your account manager.</p>
  </div>
  <div class="footer">OpsConductor/Pulse - Tenant: {tenant_id}</div>
</body>
</html>
"""

EXPIRY_TEXT_TEMPLATE = """
Subscription Expiry Notice

Dear {tenant_name},

Your OpsConductor/Pulse subscription {subscription_id} will expire in
{days_remaining} day(s) on {term_end}.

Current status: {status}

Please renew before expiry to avoid service interruption.

Tenant: {tenant_id}
"""

GRACE_SUBJECT_TEMPLATE = (
    "[Urgent] Your OpsConductor subscription has expired - grace period active"
)

GRACE_HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; color: #333;">
  <h2 style="color: #c81e1e;">Subscription Expired - Grace Period Active</h2>
  <p>Dear {tenant_name},</p>
  <p>Your subscription <strong>{subscription_id}</strong> expired on
     <strong>{term_end}</strong>.</p>
  <p>You are currently in a <strong>14-day grace period</strong> ending on
     <strong>{grace_end}</strong>. After this date, your account will be suspended.</p>
  <p>Please renew immediately to maintain access.</p>
  <p>Tenant: {tenant_id}</p>
</body>
</html>
"""
