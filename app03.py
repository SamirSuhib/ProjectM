import streamlit as st
import pandas as pd
import matplotlib.dates as mdates
import matplotlib as mpl
import matplotlib.pyplot as plt
import hashlib, io, os
from datetime import date, timedelta
from typing import Optional
from supabase import create_client, Client

# =============================================================================
# DB SCHEMA MIGRATION (run once):
#
#   ALTER TABLE bookings
#       ADD COLUMN IF NOT EXISTS transport_required BOOLEAN DEFAULT FALSE,
#       ADD COLUMN IF NOT EXISTS assigned_truck     VARCHAR(10),
#       ADD COLUMN IF NOT EXISTS assigned_worker    VARCHAR(50),
#       ADD COLUMN IF NOT EXISTS trips_count        INTEGER DEFAULT 1,
#       ADD COLUMN IF NOT EXISTS total_duration_min INTEGER DEFAULT 55,
#       ADD COLUMN IF NOT EXISTS end_time_slot      VARCHAR(20),
#       ADD COLUMN IF NOT EXISTS delivery_plan_id   INTEGER;
#
#   ALTER TABLE farmers
#       ADD COLUMN IF NOT EXISTS phone   VARCHAR(30),
#       ADD COLUMN IF NOT EXISTS address TEXT,
#       ADD COLUMN IF NOT EXISTS email   VARCHAR(100),
#       ADD COLUMN IF NOT EXISTS notes   TEXT,
#       ADD COLUMN IF NOT EXISTS active  BOOLEAN DEFAULT TRUE;
#
#   CREATE TABLE IF NOT EXISTS delivery_plans (
#       plan_id            SERIAL PRIMARY KEY,
#       farmer_id          INTEGER NOT NULL REFERENCES farmers(farmer_id),
#       manure_form        VARCHAR(10) NOT NULL,
#       manure_type_id     INTEGER REFERENCES manure_types(manure_type_id),
#       total_quantity     NUMERIC(10,2) NOT NULL,
#       start_date         DATE NOT NULL,
#       end_date           DATE NOT NULL,
#       daily_quantity     NUMERIC(10,2),
#       transport_required BOOLEAN DEFAULT FALSE,
#       assigned_worker    VARCHAR(50),
#       notes              TEXT,
#       status             VARCHAR(20) DEFAULT 'active',
#       created_at         TIMESTAMP DEFAULT NOW()
#   );
#
#   ALTER TABLE bookings
#       ADD CONSTRAINT fk_delivery_plan
#       FOREIGN KEY (delivery_plan_id) REFERENCES delivery_plans(plan_id);
# =============================================================================

# =============================================================================
# AUTHENTICATION
# Set credentials via env vars or .streamlit/secrets.toml:
#   ADMIN_USERNAME / ADMIN_PASSWORD_HASH   (sha256 hex)
#   OPERATOR_USERNAME / OPERATOR_PASSWORD_HASH
#
# secrets.toml example:
#   [auth]
#   admin_user    = "admin"
#   admin_hash    = "<sha256 of password>"
#   operator_user = "operator"
#   operator_hash = "<sha256 of password>"
#
# Get hash: python3 -c "import hashlib; print(hashlib.sha256(b'yourpassword').hexdigest())"
# =============================================================================

def _hash(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

def _get_users() -> dict:
    users = {}
    try:
        if hasattr(st, "secrets") and "auth" in st.secrets:
            s = st.secrets["auth"]
            if s.get("admin_user"):
                users[s["admin_user"]] = (s.get("admin_hash",""), "admin")
            if s.get("operator_user"):
                users[s["operator_user"]] = (s.get("operator_hash",""), "operator")
    except Exception:
        pass  # No secrets.toml — fall through to env vars / defaults
    au = os.getenv("ADMIN_USERNAME",         "admin")
    ah = os.getenv("ADMIN_PASSWORD_HASH",    _hash("admin123"))
    ou = os.getenv("OPERATOR_USERNAME",      "operator")
    oh = os.getenv("OPERATOR_PASSWORD_HASH", _hash("plant2024"))
    if au not in users: users[au] = (ah, "admin")
    if ou not in users: users[ou] = (oh, "operator")
    return users

def login_page():
    st.set_page_config(page_title="BioLogix — Sign In", layout="centered", page_icon="🌿")
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    * { font-family: 'Inter', sans-serif !important; }

    [data-testid="stAppViewContainer"] {
        background: linear-gradient(135deg, #0a1628 0%, #0d2137 50%, #0a1f1a 100%);
        min-height: 100vh;
    }
    [data-testid="stMain"] { background: transparent !important; }

    .login-card {
        background: rgba(255,255,255,0.04);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 20px;
        padding: 48px 40px;
        box-shadow: 0 25px 60px rgba(0,0,0,0.5);
    }
    .login-logo {
        display: flex; align-items: center; gap: 12px;
        margin-bottom: 8px;
    }
    .login-logo-icon {
        width: 48px; height: 48px; border-radius: 12px;
        background: linear-gradient(135deg, #22c55e, #16a34a);
        display: flex; align-items: center; justify-content: center;
        font-size: 24px;
    }
    .login-title   { font-size: 1.8rem; font-weight: 700; color: #f0fdf4; margin: 0; }
    .login-sub     { font-size: 0.85rem; color: #64748b; margin-bottom: 32px; }
    .login-heading { font-size: 1rem; font-weight: 600; color: #94a3b8; margin-bottom: 20px; }

    [data-testid="stTextInput"] > div > div > input {
        background: rgba(255,255,255,0.06) !important;
        border: 1px solid rgba(255,255,255,0.12) !important;
        border-radius: 10px !important;
        color: #f1f5f9 !important;
        font-size: 0.9rem !important;
        padding: 12px 16px !important;
        transition: border-color 0.2s;
    }
    [data-testid="stTextInput"] > div > div > input:focus {
        border-color: #22c55e !important;
        box-shadow: 0 0 0 3px rgba(34,197,94,0.15) !important;
    }
    label { color: #94a3b8 !important; font-size: 0.82rem !important; font-weight: 500 !important; }

    [data-testid="baseButton-primary"] {
        background: linear-gradient(135deg, #16a34a, #15803d) !important;
        border: none !important; border-radius: 10px !important;
        color: #ffffff !important; font-weight: 600 !important;
        font-size: 0.9rem !important; padding: 12px !important;
        box-shadow: 0 4px 15px rgba(22,163,74,0.4) !important;
        transition: all 0.2s !important;
    }
    [data-testid="baseButton-primary"]:hover {
        background: linear-gradient(135deg, #22c55e, #16a34a) !important;
        box-shadow: 0 6px 20px rgba(22,163,74,0.5) !important;
        transform: translateY(-1px) !important;
    }
    </style>
    """, unsafe_allow_html=True)

    col = st.columns([1, 1.4, 1])[1]
    with col:
        st.markdown("""
        <div class="login-card">
          <div class="login-logo">
            <div class="login-logo-icon">🌿</div>
            <p class="login-title">BioLogix</p>
          </div>
          <p class="login-sub">Biomethane Plant — Logistics & Delivery Management</p>
          <p class="login-heading">SIGN IN TO CONTINUE</p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        with st.form("login_form"):
            username = st.text_input("USERNAME", placeholder="Enter your username")
            password = st.text_input("PASSWORD", type="password", placeholder="Enter your password")
            ok_btn   = st.form_submit_button("Sign In →", use_container_width=True, type="primary")
        if ok_btn:
            users = _get_users()
            if username in users and users[username][0] == _hash(password):
                st.session_state["authenticated"] = True
                st.session_state["username"]      = username
                st.session_state["role"]          = users[username][1]
                st.rerun()
            else:
                st.error("Invalid username or password.")
        st.markdown("<p style='text-align:center;color:#475569;font-size:0.75rem;margin-top:16px'>"
                    "admin / admin123 &nbsp;·&nbsp; operator / plant2024</p>",
                    unsafe_allow_html=True)

if not st.session_state.get("authenticated"):
    login_page()
    st.stop()

# =============================================================================
# MATPLOTLIB
# =============================================================================
mpl.rcParams.update({"font.size":9,"axes.titlesize":11,"axes.labelsize":9,
                     "xtick.labelsize":8,"ytick.labelsize":8,"legend.fontsize":8})

# =============================================================================
# PLANT CONSTANTS
# =============================================================================
LIQUID_STORAGE_CAPACITY_M3  = 1900
DAILY_LIQUID_OUTFLOW_M3     = 200
LIQUID_INITIAL_STOCK_M3     = 500
SOLID_STORAGE_CAPACITY_TONS = 2000
DAILY_SOLID_OUTFLOW_TONS    = 200   # adjustable in sidebar
SOLID_INITIAL_STOCK_TONS    = 0
LIQUID_TRUCK_CAPACITY_M3    = 27
SOLID_TRUCK_CAPACITY_TONS   = 27
TRUCKS                      = {"liquid":"LKW1","solid":"LKW2"}
WORKERS                     = ["Worker 1","Worker 2"]
TRIP_DURATION_MIN           = 55
TIME_SLOTS = [
    "07:00-08:00","08:00-09:00","09:00-10:00","10:00-11:00",
    "11:00-12:00","12:00-13:00","13:00-14:00","14:00-15:00",
    "15:00-16:00","16:00-17:00","17:00-18:00","18:00-19:00",
]

# =============================================================================
# DATABASE  (Supabase REST client — works on Streamlit Cloud, no port 5432)
# =============================================================================
@st.cache_resource
def get_supabase() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

# ---------------------------------------------------------------------------
# The three helper functions below keep the same signatures as before so that
# every other line in the app works without any changes.
# They call Supabase's PostgREST RPC endpoint which accepts raw SQL via the
# "pg_query" postgres function — OR we use the supabase-py query builder.
#
# Simplest universal approach: use supabase.rpc() with a raw-SQL postgres
# function. We create that function once in Supabase SQL Editor (see README).
# ---------------------------------------------------------------------------

def _run_sql(query: str, params: dict = None):
    """Execute any SQL via the run_sql Postgres function through Supabase RPC.
    Safely inlines :param values directly into the SQL string before sending.
    """
    import re
    sb = get_supabase()

    if params:
        def replacer(m):
            key = m.group(1)
            if key not in params:
                return m.group(0)
            val = params[key]
            if val is None:
                return "NULL"
            if isinstance(val, bool):
                return "TRUE" if val else "FALSE"
            if isinstance(val, (int, float)):
                return str(val)
            escaped = str(val).replace("'", "''")
            return f"\'{escaped}\'"
        sql = re.sub(r":([a-zA-Z_][a-zA-Z0-9_]*)", replacer, query)
    else:
        sql = query

    import re as _re
    query_type = sql.strip().upper()[:6]
    is_write = query_type in ('INSERT', 'UPDATE', 'DELETE')

    if is_write:
        result = sb.rpc("run_sql_write", {"query": sql}).execute()
    else:
        result = sb.rpc("run_sql", {"query": sql}).execute()
    return result.data

def fetch_df(q: str, p: dict = None) -> pd.DataFrame:
    """Run SELECT query, return DataFrame."""
    try:
        rows = _run_sql(q, p)
        if rows:
            return pd.DataFrame(rows)
        return pd.DataFrame()
    except Exception as e:
        raise RuntimeError(f"DB error: {e}")

def exec_one(q: str, p: dict = None, fetchone: bool = False):
    """Run INSERT / UPDATE / DELETE (optionally return first row)."""
    try:
        rows = _run_sql(q, p)
        if fetchone:
            # rows may be a list of dicts, a single dict, or wrapped jsonb
            if isinstance(rows, list) and len(rows) > 0:
                first = rows[0]
                if isinstance(first, dict):
                    return tuple(first.values())
            elif isinstance(rows, dict):
                return tuple(rows.values())
        return None
    except Exception as e:
        raise RuntimeError(f"DB error: {e}")

def scalar(q: str, p: dict = None):
    """Run a query that returns a single value."""
    try:
        rows = _run_sql(q, p)
        if rows:
            return list(rows[0].values())[0]
        return None
    except Exception as e:
        raise RuntimeError(f"DB error: {e}")

# =============================================================================
# STORAGE HELPERS — single source of truth, used by all tabs
# =============================================================================

# =============================================================================
# STORAGE HELPERS — single DB fetch, all calculations in memory
# =============================================================================

@st.cache_data(ttl=30)  # cache for 30 seconds — refreshes after any booking change
def _fetch_booked_schedule() -> dict:
    """
    Fetch ALL booked deliveries in one query, return as dict:
      { (date_str, 'liquid'): total_m3, (date_str, 'solid'): total_t, ... }
    """
    try:
        df = fetch_df("""
            SELECT delivery_date::text AS d, manure_form, COALESCE(SUM(expected_tons),0) AS qty
            FROM bookings
            WHERE status='booked'
            GROUP BY delivery_date, manure_form
            ORDER BY delivery_date
        """)
        result = {}
        for _, row in df.iterrows():
            result[(row["d"], row["manure_form"])] = float(row["qty"])
        return result
    except Exception:
        return {}


def _level_on_date(target: date, form: str,
                   schedule: dict,
                   extra_date: str = None, extra_qty: float = 0.0) -> float:
    """
    Pure in-memory calculation of storage level at END of target date.
    schedule = output of _fetch_booked_schedule()
    extra_date / extra_qty = a hypothetical delivery not yet in DB.
    """
    today   = date.today()
    days    = max(0, (target - today).days + 1)
    outflow = DAILY_LIQUID_OUTFLOW_M3 if form == "liquid" else DAILY_SOLID_OUTFLOW_TONS
    initial = LIQUID_INITIAL_STOCK_M3  if form == "liquid" else SOLID_INITIAL_STOCK_TONS

    # Sum all booked deliveries from today up to target
    total_in = 0.0
    cur = today
    while cur <= target:
        d_str = cur.strftime("%Y-%m-%d")
        total_in += schedule.get((d_str, form), 0.0)
        if extra_date and d_str == extra_date:
            total_in += extra_qty
        cur += timedelta(days=1)

    return initial + total_in - (outflow * days)


def storage_ok(target: date, qty: float, form: str,
               schedule: dict = None) -> tuple:
    """
    Returns (feasible, worst_level, available_on_target, first_overflow_date).
    - available_on_target = space free on the target date BEFORE this booking
    - Scans target → target+60 with the extra qty to find any future overflow
    - Also scans today → target-1 to detect pre-existing overflows from existing bookings
    """
    if schedule is None:
        schedule = _fetch_booked_schedule()
    cap       = LIQUID_STORAGE_CAPACITY_M3 if form == "liquid" else SOLID_STORAGE_CAPACITY_TONS
    target_ds = target.strftime("%Y-%m-%d")
    today     = date.today()

    before    = _level_on_date(target, form, schedule)
    available = max(0.0, cap - before)

    first_overflow = None
    worst_level    = -999999.0

    # Check from today forward (includes days before target) to catch pre-existing overflow
    horizon_end = target + timedelta(days=60)
    cur = today
    while cur <= horizon_end:
        lv = _level_on_date(cur, form, schedule,
                            extra_date=target_ds, extra_qty=qty)
        if lv > worst_level:
            worst_level = lv
        if lv > cap and first_overflow is None:
            first_overflow = cur.strftime("%Y-%m-%d")
        cur += timedelta(days=1)

    return (first_overflow is None, worst_level, available, first_overflow)


def any_future_overflow(form: str, horizon: int = 60,
                        schedule: dict = None) -> tuple:
    """Check existing bookings for future overflow. Returns (exists, date, level)."""
    if schedule is None:
        schedule = _fetch_booked_schedule()
    cap   = LIQUID_STORAGE_CAPACITY_M3 if form == "liquid" else SOLID_STORAGE_CAPACITY_TONS
    today = date.today()
    for i in range(horizon):
        d  = today + timedelta(days=i)
        lv = _level_on_date(d, form, schedule)
        if lv > cap:
            return (True, d.strftime("%Y-%m-%d"), lv)
    return (False, None, 0.0)


def projected_liquid_level(target: date, extra: float = 0.0,
                            excl_id: int = None) -> float:
    """Backwards-compat wrapper — uses in-memory schedule."""
    sched = _fetch_booked_schedule()
    extra_date = target.strftime("%Y-%m-%d") if extra else None
    return _level_on_date(target, "liquid", sched,
                          extra_date=extra_date, extra_qty=extra)


def projected_solid_level(target: date, extra: float = 0.0,
                           excl_id: int = None) -> float:
    """Backwards-compat wrapper — uses in-memory schedule."""
    sched = _fetch_booked_schedule()
    extra_date = target.strftime("%Y-%m-%d") if extra else None
    return _level_on_date(target, "solid", sched,
                          extra_date=extra_date, extra_qty=extra)


def build_forecast_df(days: int = 14) -> pd.DataFrame:
    """Day-by-day forecast — single DB fetch, all maths in memory."""
    schedule = _fetch_booked_schedule()  # ONE query for everything
    rows     = []
    today    = date.today()

    for i in range(days):
        d     = today + timedelta(days=i)
        d_str = d.strftime("%Y-%m-%d")
        li    = schedule.get((d_str, "liquid"), 0.0)
        si    = schedule.get((d_str, "solid"),  0.0)
        ll    = _level_on_date(d, "liquid", schedule)
        sl    = _level_on_date(d, "solid",  schedule)
        lf    = max(0.0, ll)
        sf    = max(0.0, sl)
        liq_flag = ("🔴 OVERFLOW" if ll > LIQUID_STORAGE_CAPACITY_M3
                    else ("🟡 HIGH" if lf / LIQUID_STORAGE_CAPACITY_M3 > 0.85 else "🟢 OK"))
        sol_flag = ("🔴 OVERFLOW" if sl > SOLID_STORAGE_CAPACITY_TONS
                    else ("🟡 HIGH" if sf / SOLID_STORAGE_CAPACITY_TONS > 0.85 else "🟢 OK"))
        rows.append({
            "Date":              d_str,
            "Day":               d.strftime("%a"),
            "Liquid In (m³)":    round(li, 1),
            "−Liquid Out (m³)":  DAILY_LIQUID_OUTFLOW_M3,
            "Liquid Level (m³)": round(lf, 1),
            "Liquid Fill %":     round(lf / LIQUID_STORAGE_CAPACITY_M3 * 100, 1),
            "Liquid Status":     liq_flag,
            "Solid In (t)":      round(si, 1),
            "−Solid Out (t)":    DAILY_SOLID_OUTFLOW_TONS,
            "Solid Level (t)":   round(sf, 1),
            "Solid Fill %":      round(sf / SOLID_STORAGE_CAPACITY_TONS * 100, 1),
            "Solid Status":      sol_flag,
        })
    return pd.DataFrame(rows)


# =============================================================================
# TRIP / TRUCK HELPERS
# =============================================================================
def calc_trips(vol, form):
    cap = LIQUID_TRUCK_CAPACITY_M3 if form=="liquid" else SOLID_TRUCK_CAPACITY_TONS
    return max(1, -(-int(vol)//int(cap)))

def calc_dur(trips):
    return trips * TRIP_DURATION_MIN

def slots_needed(trips):
    return max(1, -(-(trips*TRIP_DURATION_MIN)//60))

def get_slots_from(start, n):
    if start not in TIME_SLOTS: return [start]
    i = TIME_SLOTS.index(start)
    return TIME_SLOTS[i:i+n]

def truck_conflicts(d_str, truck, start_slot, n_slots, excl_id=None):
    slots = get_slots_from(start_slot, n_slots)
    if len(slots) < n_slots:
        return [f"Need {n_slots} slots but only {len(slots)} remain in working day"]
    ec  = "AND booking_id != :excl" if excl_id else ""
    out = []
    for s in slots:
        p = {"date":d_str,"slot":s,"truck":truck}
        if excl_id: p["excl"] = excl_id
        try:
            if int(scalar(f"SELECT COUNT(*) FROM bookings WHERE delivery_date=:date "
                          f"AND time_slot=:slot AND assigned_truck=:truck "
                          f"AND status!='cancelled' {ec}", p) or 0) > 0:
                out.append(s)
        except Exception:
            pass
    return out

def get_truck_schedule(d: date) -> pd.DataFrame:
    try:
        return fetch_df("""
            SELECT b.booking_id, b.time_slot,
                   COALESCE(b.assigned_truck,'N/A')       AS truck,
                   COALESCE(b.assigned_worker,'—')        AS worker,
                   f.name AS farmer, b.manure_form, b.expected_tons,
                   COALESCE(b.transport_required,FALSE)   AS transport_required,
                   COALESCE(b.trips_count,1)              AS trips_count,
                   COALESCE(b.total_duration_min,55)      AS total_duration_min,
                   COALESCE(b.end_time_slot,b.time_slot)  AS end_time_slot,
                   b.status
            FROM bookings b JOIN farmers f ON f.farmer_id=b.farmer_id
            WHERE b.delivery_date=:d AND b.status!='cancelled'
            ORDER BY b.time_slot, b.assigned_truck
        """, {"d": d.strftime("%Y-%m-%d")})
    except Exception:
        return pd.DataFrame()

def build_plan_bookings(farmer_id, manure_form, manure_type_id,
                        total_qty, start_date, end_date,
                        preferred_slot, transport_required, assigned_worker):
    """
    Split total_qty across working days.
    Checks per day (cumulatively):
      1. Storage feasibility (forward 60 days)
      2. Truck slot availability (in-memory sim so same-plan earlier days block later ones)
      3. Driver 240-min/day limit (DB + in-memory accumulator)
    Returns (ok_list, ov_skip, cf_skip).
    """
    cap   = LIQUID_TRUCK_CAPACITY_M3 if manure_form=="liquid" else SOLID_TRUCK_CAPACITY_TONS
    truck = TRUCKS.get(manure_form) if transport_required else None
    wdays = [start_date + timedelta(days=i)
             for i in range((end_date - start_date).days + 1)
             if (start_date + timedelta(days=i)).weekday() != 6]
    if not wdays:
        return [], [], []

    dq       = total_qty / len(wdays)
    tpd      = max(1, -(-int(dq) // int(cap)))
    actual_d = min(tpd * cap, total_qty)
    ok_list  = []
    ov_skip  = []
    cf_skip  = []
    remaining = total_qty

    # In-memory simulation schedules
    sim_schedule     = dict(_fetch_booked_schedule())   # storage
    sim_truck_slots  = {}   # { (d_str, slot): True } — truck slots taken this plan
    sim_worker_mins  = {}   # { d_str: minutes_already_assigned_this_plan }

    for d in wdays:
        if remaining <= 0:
            break
        day_qty = min(actual_d, remaining)
        d_str   = d.strftime("%Y-%m-%d")

        # ── 1. Recalculate trips for this day_qty ──────────────────────────
        trips    = max(1, -(-int(day_qty) // int(cap)))
        dur      = calc_dur(trips)
        ns       = slots_needed(trips)
        blocked  = get_slots_from(preferred_slot, ns)
        end_slot = blocked[-1] if blocked else preferred_slot

        # ── 2. Storage check ───────────────────────────────────────────────
        ok, lv_after, available, first_ov = storage_ok(d, day_qty, manure_form, sim_schedule)
        if not ok or first_ov:
            if available <= 0:
                ov_skip.append({"date": d_str, "reason": "Storage full — no space"})
                remaining -= day_qty
                continue
            else:
                # Cap to available space
                day_qty  = round(available, 2)
                trips    = max(1, -(-int(day_qty) // int(cap)))
                dur      = calc_dur(trips)
                ns       = slots_needed(trips)
                blocked  = get_slots_from(preferred_slot, ns)
                end_slot = blocked[-1] if blocked else preferred_slot
                ov_skip.append({"date": d_str,
                                "reason": f"Capped to {day_qty:.1f} (overflow {first_ov})"})

        # ── 3. Truck slot check (DB + in-memory plan slots) ───────────────
        if transport_required and truck:
            # DB conflicts
            db_cf = truck_conflicts(d_str, truck, preferred_slot, ns)
            # In-memory conflicts (from earlier days in this plan)
            mem_cf = [s for s in blocked if sim_truck_slots.get((d_str, s))]
            all_cf = list(set(db_cf + mem_cf))
            if all_cf:
                cf_skip.append({"date": d_str,
                                "reason": f"{truck} slot conflict: {', '.join(all_cf)}"})
                remaining -= day_qty
                continue

            # ── 4. Driver 240-min/day limit ───────────────────────────────
            try:
                db_mins = int(scalar(
                    """SELECT COALESCE(SUM(COALESCE(total_duration_min,:dd)),0)
                       FROM bookings WHERE delivery_date=:d AND assigned_worker=:w
                       AND status!='cancelled'""",
                    {"d": d_str, "w": assigned_worker, "dd": TRIP_DURATION_MIN}) or 0)
            except Exception:
                db_mins = 0
            plan_mins = sim_worker_mins.get(d_str, 0)
            total_mins = db_mins + plan_mins + dur
            if total_mins > 240:
                remaining_min = 240 - db_mins - plan_mins
                if remaining_min >= TRIP_DURATION_MIN:
                    # Can do fewer trips
                    max_trips = remaining_min // TRIP_DURATION_MIN
                    day_qty   = round(min(max_trips * cap, day_qty), 2)
                    trips     = max_trips
                    dur       = calc_dur(trips)
                    ns        = slots_needed(trips)
                    blocked   = get_slots_from(preferred_slot, ns)
                    end_slot  = blocked[-1] if blocked else preferred_slot
                    cf_skip.append({"date": d_str,
                                    "reason": f"{assigned_worker} capped to {trips} trip(s) "
                                              f"(driver limit: {db_mins+plan_mins}+{dur}=240 min)"})
                else:
                    cf_skip.append({"date": d_str,
                                    "reason": f"{assigned_worker} fully booked "
                                              f"({db_mins+plan_mins} min used, needs {dur} min)"})
                    remaining -= day_qty
                    continue

        # ── Accept this day ────────────────────────────────────────────────
        ok_list.append({
            "farmer_id":              farmer_id,
            "delivery_date":          d_str,
            "time_slot":              preferred_slot,
            "status":                 "booked",
            "expected_tons":          round(day_qty, 2),
            "manure_form":            manure_form,
            "planned_manure_type_id": manure_type_id,
            "transport_required":     transport_required,
            "assigned_truck":         truck,
            "assigned_worker":        assigned_worker if transport_required else None,
            "trips_count":            trips,
            "total_duration_min":     dur,
            "end_time_slot":          end_slot,
        })

        # Update all simulation dicts so subsequent days see this booking
        key = (d_str, manure_form)
        sim_schedule[key] = sim_schedule.get(key, 0.0) + day_qty

        if transport_required and truck:
            for s in blocked:
                sim_truck_slots[(d_str, s)] = True
            sim_worker_mins[d_str] = sim_worker_mins.get(d_str, 0) + dur

        remaining -= day_qty

    return ok_list, ov_skip, cf_skip

# =============================================================================
# PAGE CONFIG + CSS
# =============================================================================
st.set_page_config(page_title="BioLogix", layout="wide", page_icon="🌿",
                   initial_sidebar_state="expanded")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* ── Reset & Base ──────────────────────────────────────────────────────── */
* { font-family: 'Inter', sans-serif !important; box-sizing: border-box; }

[data-testid="stAppViewContainer"] {
    background: #0b1120 !important;
}
[data-testid="stMain"] > div {
    background: #0b1120 !important;
    padding-top: 0 !important;
}
[data-testid="stHeader"] { background: transparent !important; }

/* ── Sidebar ────────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: #0f172a !important;
    border-right: 1px solid #1e293b !important;
}
[data-testid="stSidebar"] > div { padding: 20px 16px !important; }
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] span { color: #94a3b8 !important; font-size: 0.82rem !important; }
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 { color: #e2e8f0 !important; font-size: 0.85rem !important;
                                font-weight: 600 !important; letter-spacing: 0.05em;
                                text-transform: uppercase; }
[data-testid="stSidebar"] hr { border-color: #1e293b !important; margin: 12px 0 !important; }

/* ── Sidebar collapse/expand toggle button ──────────────────────────────── */
[data-testid="stSidebarCollapsedControl"] {
    background: #1e293b !important;
    border: 1px solid #334155 !important;
    border-radius: 50% !important;
    width: 36px !important;
    height: 36px !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.4) !important;
    transition: all 0.2s !important;
    position: relative !important;
}
[data-testid="stSidebarCollapsedControl"]:hover {
    background: #22c55e !important;
    border-color: #22c55e !important;
}
/* Hide the material icon text by making it transparent and zero size */
[data-testid="stSidebarCollapsedControl"] span {
    font-size: 0 !important;
    color: transparent !important;
}
[data-testid="stSidebarCollapsedControl"] button {
    font-size: 0 !important;
    color: transparent !important;
}
/* Replace with ☰ using pseudo on the inner button */
[data-testid="stSidebarCollapsedControl"] button::after {
    content: "☰" !important;
    font-size: 16px !important;
    color: #94a3b8 !important;
    font-family: Arial, sans-serif !important;
    position: absolute !important;
    top: 50% !important;
    left: 50% !important;
    transform: translate(-50%, -50%) !important;
}
[data-testid="stSidebarCollapsedControl"]:hover button::after {
    color: #ffffff !important;
}

/* ── Sidebar metrics ────────────────────────────────────────────────────── */
[data-testid="stSidebar"] [data-testid="stMetric"] {
    background: #1e293b !important;
    border: 1px solid #334155 !important;
    border-radius: 10px !important;
    padding: 10px 14px !important;
    margin-bottom: 6px !important;
}
[data-testid="stSidebar"] [data-testid="stMetricLabel"] { color: #64748b !important; font-size: 0.72rem !important; }
[data-testid="stSidebar"] [data-testid="stMetricValue"] { color: #f1f5f9 !important; font-size: 1.1rem !important; font-weight: 700 !important; }

/* ── Main metrics ────────────────────────────────────────────────────────── */
[data-testid="stMetric"] {
    background: #1e293b !important;
    border: 1px solid #334155 !important;
    border-radius: 12px !important;
    padding: 16px 20px !important;
    transition: border-color 0.2s, box-shadow 0.2s;
}
[data-testid="stMetric"]:hover {
    border-color: #22c55e !important;
    box-shadow: 0 0 0 1px rgba(34,197,94,0.2) !important;
}
[data-testid="stMetricLabel"] { color: #64748b !important; font-size: 0.76rem !important;
                                  font-weight: 500 !important; letter-spacing: 0.03em; text-transform: uppercase; }
[data-testid="stMetricValue"] { color: #f1f5f9 !important; font-size: 1.5rem !important; font-weight: 700 !important; }
[data-testid="stMetricDelta"]  { font-size: 0.78rem !important; }

/* ── Typography ─────────────────────────────────────────────────────────── */
h1 { color: #f1f5f9 !important; font-size: 1.6rem !important; font-weight: 700 !important; }
h2 { color: #e2e8f0 !important; font-size: 1.2rem !important; font-weight: 600 !important; }
h3 { color: #cbd5e1 !important; font-size: 1rem !important; font-weight: 600 !important; }
h4 { color: #94a3b8 !important; font-size: 0.85rem !important; font-weight: 600 !important;
     text-transform: uppercase; letter-spacing: 0.05em; }
p, label, .stMarkdown, span { color: #94a3b8 !important; font-size: 0.87rem !important; }
strong { color: #e2e8f0 !important; }
hr { border-color: #1e293b !important; margin: 16px 0 !important; }

/* ── Tabs ────────────────────────────────────────────────────────────────── */
[data-baseweb="tab-list"] {
    background: #1e293b !important;
    border-radius: 12px !important;
    padding: 4px !important;
    gap: 2px !important;
    border: 1px solid #334155 !important;
}
[data-baseweb="tab"] {
    border-radius: 8px !important;
    padding: 8px 18px !important;
    color: #64748b !important;
    font-weight: 500 !important;
    font-size: 0.82rem !important;
    transition: all 0.15s !important;
}
[data-baseweb="tab"]:hover { color: #94a3b8 !important; background: #334155 !important; }
[aria-selected="true"] {
    background: linear-gradient(135deg, #166534, #15803d) !important;
    color: #dcfce7 !important; font-weight: 600 !important;
    box-shadow: 0 2px 8px rgba(22,101,52,0.4) !important;
}

/* ── Buttons ─────────────────────────────────────────────────────────────── */
[data-testid="baseButton-primary"] {
    background: linear-gradient(135deg, #16a34a, #15803d) !important;
    border: none !important; border-radius: 8px !important;
    color: #fff !important; font-weight: 600 !important; font-size: 0.85rem !important;
    box-shadow: 0 2px 8px rgba(22,163,74,0.35) !important;
    transition: all 0.15s !important;
}
[data-testid="baseButton-primary"]:hover {
    background: linear-gradient(135deg, #22c55e, #16a34a) !important;
    box-shadow: 0 4px 14px rgba(22,163,74,0.45) !important;
    transform: translateY(-1px) !important;
}
[data-testid="baseButton-primary"]:disabled {
    background: #1e293b !important;
    color: #475569 !important; box-shadow: none !important;
    transform: none !important; cursor: not-allowed !important;
}
[data-testid="baseButton-secondary"] {
    background: transparent !important;
    border: 1px solid #334155 !important; border-radius: 8px !important;
    color: #94a3b8 !important; font-weight: 500 !important;
    transition: all 0.15s !important;
}
[data-testid="baseButton-secondary"]:hover {
    border-color: #22c55e !important; color: #22c55e !important;
}

/* ── Form inputs ─────────────────────────────────────────────────────────── */
[data-testid="stTextInput"] > div > div > input,
[data-testid="stNumberInput"] input,
[data-testid="stTextArea"] textarea {
    background: #1e293b !important; color: #f1f5f9 !important;
    border: 1px solid #334155 !important; border-radius: 8px !important;
    font-size: 0.87rem !important; transition: border-color 0.2s, box-shadow 0.2s !important;
}
[data-testid="stTextInput"] > div > div > input:focus,
[data-testid="stNumberInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {
    border-color: #22c55e !important;
    box-shadow: 0 0 0 3px rgba(34,197,94,0.12) !important;
    outline: none !important;
}

/* ── Selects / Dropdowns ─────────────────────────────────────────────────── */
[data-baseweb="select"] > div {
    background: #1e293b !important; border: 1px solid #334155 !important;
    border-radius: 8px !important; color: #f1f5f9 !important;
}
[data-baseweb="select"] > div:focus-within {
    border-color: #22c55e !important;
    box-shadow: 0 0 0 3px rgba(34,197,94,0.12) !important;
}
[data-baseweb="popover"] { background: #1e293b !important; border: 1px solid #334155 !important; border-radius: 10px !important; }
[role="option"] { color: #e2e8f0 !important; }
[role="option"]:hover { background: #334155 !important; }

/* ── Radio buttons ───────────────────────────────────────────────────────── */
[data-testid="stRadio"] label { color: #94a3b8 !important; }
[data-testid="stRadio"] [data-testid="stMarkdownContainer"] p { color: #94a3b8 !important; }

/* ── DataFrames / Tables ─────────────────────────────────────────────────── */
[data-testid="stDataFrame"] {
    background: #1e293b !important; border-radius: 12px !important;
    border: 1px solid #334155 !important; overflow: hidden !important;
}
[data-testid="stDataFrame"] thead th {
    background: #0f172a !important; color: #64748b !important;
    font-size: 0.75rem !important; text-transform: uppercase !important;
    letter-spacing: 0.05em !important; border-bottom: 1px solid #334155 !important;
}
[data-testid="stDataFrame"] tbody td { color: #e2e8f0 !important; font-size: 0.84rem !important; }
[data-testid="stDataFrame"] tbody tr:hover td { background: rgba(34,197,94,0.05) !important; }

/* ── Alerts ──────────────────────────────────────────────────────────────── */
[data-testid="stAlert"] { border-radius: 10px !important; font-size: 0.85rem !important; border-left-width: 3px !important; }
[data-testid="stAlert"][data-baseweb="notification"] { background: #0f172a !important; }

/* ── Progress bar ────────────────────────────────────────────────────────── */
[data-testid="stProgress"] > div > div { background: #22c55e !important; border-radius: 99px !important; }
[data-testid="stProgress"] > div { background: #1e293b !important; border-radius: 99px !important; }

/* ── Checkbox ────────────────────────────────────────────────────────────── */
[data-testid="stCheckbox"] label { color: #94a3b8 !important; }

/* ── Scrollbar ───────────────────────────────────────────────────────────── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: #0b1120; }
::-webkit-scrollbar-thumb { background: #334155; border-radius: 99px; }
::-webkit-scrollbar-thumb:hover { background: #475569; }

/* ── Custom components ───────────────────────────────────────────────────── */
.page-header {
    display: flex; align-items: center; justify-content: space-between;
    padding: 16px 0 12px; border-bottom: 1px solid #1e293b; margin-bottom: 20px;
}
.page-header-left { display: flex; align-items: center; gap: 14px; }
.app-logo {
    width: 38px; height: 38px; border-radius: 10px;
    background: linear-gradient(135deg, #22c55e, #15803d);
    display: flex; align-items: center; justify-content: center;
    font-size: 18px; flex-shrink: 0;
}
.app-name { font-size: 1.2rem; font-weight: 700; color: #f1f5f9 !important; margin: 0; }
.app-sub  { font-size: 0.75rem; color: #475569 !important; margin: 0; }

.status-bar {
    display: flex; align-items: center; gap: 6px;
    background: #1e293b; border: 1px solid #334155;
    border-radius: 10px; padding: 10px 16px; margin-bottom: 16px;
    flex-wrap: wrap;
}
.status-item { display: flex; align-items: center; gap: 6px; font-size: 0.82rem; color: #94a3b8; }
.status-val  { font-weight: 600; color: #f1f5f9; }
.status-sep  { color: #334155; }
.dot-green   { width: 8px; height: 8px; border-radius: 50%; background: #22c55e; flex-shrink: 0; }
.dot-yellow  { width: 8px; height: 8px; border-radius: 50%; background: #f59e0b; flex-shrink: 0; }
.dot-red     { width: 8px; height: 8px; border-radius: 50%; background: #ef4444; flex-shrink: 0; }

.section-title {
    font-size: 0.72rem; font-weight: 600; color: #475569;
    text-transform: uppercase; letter-spacing: 0.08em;
    margin: 0 0 10px; padding-bottom: 6px;
    border-bottom: 1px solid #1e293b;
}
.user-badge {
    display: inline-flex; align-items: center; gap: 8px;
    background: #1e293b; border: 1px solid #334155; border-radius: 20px;
    padding: 6px 14px; font-size: 0.8rem; color: #94a3b8;
}
.user-badge .role-tag {
    background: rgba(34,197,94,0.15); color: #22c55e;
    border-radius: 20px; padding: 1px 8px; font-size: 0.7rem; font-weight: 600;
}
.card {
    background: #1e293b; border: 1px solid #334155; border-radius: 12px;
    padding: 20px; margin-bottom: 12px;
}
.info-row { display: flex; gap: 8px; align-items: center; margin-bottom: 6px; }
.info-label { font-size: 0.75rem; color: #475569; font-weight: 500; min-width: 120px; }
.info-val   { font-size: 0.85rem; color: #e2e8f0; font-weight: 500; }
</style>""", unsafe_allow_html=True)

# =============================================================================
# =============================================================================
# SIDEBAR
# =============================================================================
# Inject JS to replace the keyboard_double_arr icon with a hamburger symbol
st.markdown("""
<script>
function fixSidebarButton() {
    const btns = window.parent.document.querySelectorAll('[data-testid="stSidebarCollapsedControl"] button');
    btns.forEach(btn => {
        btn.innerHTML = '&#9776;';
        btn.style.fontSize = '18px';
        btn.style.color = '#94a3b8';
        btn.style.background = 'none';
        btn.style.border = 'none';
        btn.style.cursor = 'pointer';
    });
}
// Run on load and watch for DOM changes
fixSidebarButton();
const observer = new MutationObserver(fixSidebarButton);
observer.observe(window.parent.document.body, { childList: true, subtree: true });
</script>
""", unsafe_allow_html=True)

with st.sidebar:
    uname = st.session_state.get('username','?')
    role  = st.session_state.get('role','operator')
    st.markdown(
        f'<div class="user-badge"><span>\U0001f464 {uname}</span>'
        f'<span class="role-tag">{role.upper()}</span></div>',
        unsafe_allow_html=True)
    if st.button('Sign out', key='logout', use_container_width=True):
        st.session_state.clear(); st.rerun()
    st.markdown('<p class="section-title" style="margin-top:16px">Plant Configuration</p>', unsafe_allow_html=True)
    st.metric('Vorgrube capacity', f'{LIQUID_STORAGE_CAPACITY_M3} m\u00b3')
    st.metric('Liquid outflow',    f'{DAILY_LIQUID_OUTFLOW_M3} m\u00b3/day')
    st.metric('Solid storage',     f'{SOLID_STORAGE_CAPACITY_TONS} t')
    st.markdown('<p class="section-title" style="margin-top:16px">Current Stock</p>', unsafe_allow_html=True)
    LIQUID_INITIAL_STOCK_M3  = st.number_input('Liquid level now (m\u00b3)',
        min_value=0, max_value=LIQUID_STORAGE_CAPACITY_M3,  value=500, step=10, key='liq_s')
    SOLID_INITIAL_STOCK_TONS = st.number_input('Solid level now (t)',
        min_value=0, max_value=SOLID_STORAGE_CAPACITY_TONS, value=0,   step=10, key='sol_s')
    st.markdown('<p class="section-title" style="margin-top:16px">Daily Outflow</p>', unsafe_allow_html=True)
    DAILY_SOLID_OUTFLOW_TONS = st.number_input('Solid outflow (t/day)',
        min_value=0, max_value=500, value=200, step=5, key='sol_out')
    st.markdown('<p class="section-title" style="margin-top:16px">Fleet & Workers</p>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="card" style="padding:10px 14px;margin-bottom:6px">'
        f'<div style="font-size:.8rem;font-weight:600;color:#22c55e">LKW 1 \u2014 Liquid</div>'
        f'<div style="font-size:.75rem;color:#64748b">{LIQUID_TRUCK_CAPACITY_M3} m\u00b3/trip \u00b7 {TRIP_DURATION_MIN} min</div></div>'
        f'<div class="card" style="padding:10px 14px;margin-bottom:6px">'
        f'<div style="font-size:.8rem;font-weight:600;color:#22c55e">LKW 2 \u2014 Solid</div>'
        f'<div style="font-size:.75rem;color:#64748b">{SOLID_TRUCK_CAPACITY_TONS} t/trip \u00b7 {TRIP_DURATION_MIN} min</div></div>',
        unsafe_allow_html=True)
    for w in WORKERS:
        st.markdown(
            f'<div class="card" style="padding:8px 14px;display:flex;align-items:center;gap:8px;margin-bottom:4px">'
            f'<div style="font-size:.82rem;font-weight:600;color:#e2e8f0">{w}</div>'
            f'<div style="font-size:.72rem;color:#475569;margin-left:auto">50% driver</div></div>',
            unsafe_allow_html=True)

# =============================================================================
# HEADER + STORAGE STATUS BAR
# =============================================================================
st.markdown(
    '<div class="page-header">'
    '<div class="page-header-left">'
    '<div class="app-logo">\U0001f33f</div>'
    '<div><p class="app-name">BioLogix</p>'
    '<p class="app-sub">Biomethane Plant \u2014 Logistics & Delivery Management</p>'
    '</div></div></div>', unsafe_allow_html=True)

hc1, hc2, hc3 = st.columns([1, 3, 0.3])
with hc1:
    selected_date = st.date_input('Working date', key='shared_date', label_visibility='collapsed')
    date_str      = selected_date.strftime('%Y-%m-%d')
    st.markdown(f"<p style='font-size:.75rem;color:#475569;margi
