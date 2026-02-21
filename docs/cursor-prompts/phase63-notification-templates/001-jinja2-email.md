# Prompt 001 — Jinja2 in delivery_worker + Email Sender Upgrade

## Add to `services/delivery_worker/requirements.txt`

```
jinja2>=3.1.0
```

## Update `services/delivery_worker/email_sender.py`

Read the file fully first.

Replace `.format(**kwargs)` template rendering with Jinja2:

```python
from jinja2 import Environment, BaseLoader, TemplateError

_jinja_env = Environment(loader=BaseLoader(), autoescape=False)

def render_template(template_str: str, variables: dict) -> str:
    """Render a Jinja2 template string with the given variables.
    Falls back to raw string on TemplateError (logs warning).
    """
    try:
        tmpl = _jinja_env.from_string(template_str)
        return tmpl.render(**variables)
    except TemplateError as e:
        # Log and fall back to raw template
        import logging
        logging.getLogger(__name__).warning(f"Template render error: {e}")
        return template_str
```

Replace the two existing template rendering lines (subject and body) with calls to `render_template()`.

**Add new template variables** to the existing `template_vars` dict:
```python
template_vars["site_id"] = payload.get("site_id", "")
template_vars["summary"] = payload.get("summary", payload.get("message", ""))
template_vars["status"] = payload.get("status", "OPEN")
template_vars["details"] = payload.get("details", {})
template_vars["severity_label"] = {
    0: "CRITICAL", 1: "CRITICAL", 2: "WARNING", 3: "INFO"
}.get(payload.get("severity", 3), "UNKNOWN")
```

**Backwards compatibility**: Existing `.format()`-style templates like `[{severity}] {alert_type}: {device_id}` should still work because Jinja2 ignores `{...}` (uses `{{ ... }}`). However, add a migration note: existing templates using `{var}` syntax will NOT be auto-converted. Document in .env.example.

## Acceptance Criteria

- [ ] `jinja2>=3.1.0` in delivery_worker requirements.txt
- [ ] `render_template()` using Jinja2 in email_sender.py
- [ ] New variables: site_id, summary, status, details, severity_label
- [ ] TemplateError falls back gracefully (no crash)
- [ ] Existing tests still pass
