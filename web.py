"""Local web UI: sliders on the left, live results on the right.

The page asks this server to run model.simulate on every slider move, so the
model stays the single source of truth (no second copy of the logic in JS).
"""

import json
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from model import GRACE_MONTHS, SUPPORT_MONTH_LIMIT, last_aid_month, simulate

UI_FILE = Path(__file__).with_name("ui.html")

# key, label, min, max, step, unit, group
FIELDS = [
    ("monthly_pay", "Loan per support month", 0, 850, 10, "€", "Student loan"),
    ("aid_months", "Kela support months", 1, 57, 1, "months", "Student loan"),
    ("repayment_years", "Repayment plan, from first draw", 3, 30, 1, "years", "Student loan"),
    ("euribor", "12-month Euribor", 0, 8, 0.05, "%", "Rates and fees"),
    ("margin", "Bank margin", 0, 2, 0.05, "%", "Rates and fees"),
    ("debit_fee", "Fee per instalment", 0, 10, 0.5, "€", "Rates and fees"),
    ("arrangement_fee", "Arrangement fee", 0, 50, 1, "€", "Rates and fees"),
    ("growth", "Fund growth per year", -5, 15, 0.1, "%", "Investing"),
    ("fund_fee", "Fund fee per year", 0, 3, 0.05, "%", "Investing"),
    ("starting_pot", "Investments you already have", 0, 200000, 500, "€", "Investing"),
    ("living_cost_yearly", "Living costs per year", 0, 36000, 250, "€", "Living during studies"),
    ("kela_grant", "Kela grant per support month", 0, 800, 5, "€", "Living during studies"),
]
DEGREES = [(0, "No lainahyvitys"), (180, "180 credits"), (300, "300 credits")]
LIMITS = {key: (lo, hi) for key, _, lo, hi, *_ in FIELDS}


def clamp(value, lo, hi):
    return max(lo, min(hi, value))


def run(query):
    """Parse query-string params (untrusted), clamp them, simulate. Returns a JSON-able dict."""
    p = {}
    for key, (lo, hi) in LIMITS.items():
        try:
            p[key] = clamp(float(query[key][0]), lo, hi)
        except (KeyError, ValueError, IndexError):
            raise ValueError(f"missing or invalid value for {key}")
    try:
        degree = int(float(query.get("degree", ["0"])[0]))
    except ValueError:
        degree = 0
    degree = degree if degree in SUPPORT_MONTH_LIMIT else None
    p["aid_months"] = int(p["aid_months"])

    study_end = last_aid_month(p["aid_months"])
    min_years = (study_end + GRACE_MONTHS) // 12 + 1
    if min_years > 30:
        raise ValueError("Too many support months: the repayment must fit in the 30-year guarantee")
    years = int(max(p["repayment_years"], min_years))

    rows, s = simulate(p["monthly_pay"], p["aid_months"], years, p["euribor"] + p["margin"],
                       p["growth"], p["fund_fee"], p["debit_fee"], p["arrangement_fee"], degree,
                       p["starting_pot"], p["living_cost_yearly"], p["kela_grant"])
    warnings = []
    if degree and p["aid_months"] > SUPPORT_MONTH_LIMIT[degree]:
        warnings.append(f"Kela allows {SUPPORT_MONTH_LIMIT[degree]} support months for {degree} credits.")
    if s["living_shortfall"] > 0:
        warnings.append(f"The fund runs dry: {s['living_shortfall']:,.0f} € of living costs are not covered.")
    return {
        "rows": [[r.month, round(r.disbursed, 2), round(r.investment, 2), round(r.total_interest, 2),
                  round(r.outstanding, 2), round(r.in_hand, 2), round(r.grant_total, 2)] for r in rows],
        "summary": {k: round(v, 2) if isinstance(v, float) else v for k, v in s.items()},
        "repayment_years": years,
        "min_repayment_years": min_years,
        "warnings": warnings,
    }


def make_page(defaults):
    config = {
        "fields": [dict(key=k, label=lab, min=lo, max=hi, step=st, unit=u, group=g, value=defaults[k])
                   for k, lab, lo, hi, st, u, g in FIELDS],
        "degrees": [{"value": v, "label": lab} for v, lab in DEGREES],
        "degree": defaults.get("degree", 0),
    }
    blob = json.dumps(config).replace("<", "\\u003c")
    return UI_FILE.read_text(encoding="utf-8").replace("/*CONFIG*/", blob).encode("utf-8")


def make_handler(page, port):
    allowed_hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}

    class Handler(BaseHTTPRequestHandler):
        def _send(self, status, body, content_type):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.headers.get("Host") not in allowed_hosts:   # blocks DNS-rebinding
                return self._send(403, b"forbidden", "text/plain")
            url = urlparse(self.path)
            if url.path == "/":
                return self._send(200, page, "text/html; charset=utf-8")
            if url.path == "/api/simulate":
                try:
                    body, status = run(parse_qs(url.query)), 200
                except ValueError as err:
                    body, status = {"error": str(err)}, 400
                return self._send(status, json.dumps(body).encode(), "application/json")
            self._send(404, b"not found", "text/plain")

        def log_message(self, *args):
            pass

    return Handler


def serve(defaults, open_browser=True):
    """Start the UI on a free local port and block until Ctrl+C."""
    server = ThreadingHTTPServer(("127.0.0.1", 0), BaseHTTPRequestHandler)
    port = server.server_address[1]
    server.RequestHandlerClass = make_handler(make_page(defaults), port)
    url = f"http://127.0.0.1:{port}/"
    print(f"\nLive sliders at {url}   (Ctrl+C to stop)")
    if open_browser:
        threading.Timer(0.3, webbrowser.open, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()
