# Task 1: Fix CSRF Cookie — Set httpOnly=True

## Context

`services/ui_iot/app.py` sets the CSRF cookie with `httponly=False` so that the JavaScript layer can read it. This is a security mistake: if any XSS occurs, the attacker can extract the CSRF token from `document.cookie` and use it to forge authenticated requests.

The correct pattern is:
- Set the CSRF cookie as `httponly=True` so JavaScript cannot read it.
- Expose the CSRF token value via a custom response header (e.g., `X-CSRF-Token`) on the session/login endpoint. The frontend reads it once from the header and stores it in memory (not localStorage or a readable cookie).

## Actions

1. Read `services/ui_iot/app.py` in full, paying attention to every `set_cookie` call involving `csrf_token` or `CSRF_COOKIE_NAME`.

2. In every `set_cookie` call for the CSRF cookie, change `httponly=False` to `httponly=True`.

3. Find the endpoint(s) that set the CSRF cookie (likely the session endpoint or login callback). After setting the cookie, also add the CSRF token value to the response as a custom header:
   ```python
   response.headers["X-CSRF-Token"] = csrf_token
   ```

4. Search the file for any other place the CSRF token is written to a non-httpOnly cookie. Fix all occurrences.

5. Do not change any frontend files in this task (handled in Task 4).

6. Do not change any other logic.

## Verification

```bash
grep -n 'httponly.*False\|httponly=False' services/ui_iot/app.py
# Must return zero results for CSRF cookie calls

grep -n 'X-CSRF-Token' services/ui_iot/app.py
# Must show the header being set on the session endpoint
```
