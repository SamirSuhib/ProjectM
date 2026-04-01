import streamlit as st
import pandas as pd
import matplotlib.dates as mdates
import matplotlib as mpl
import matplotlib.pyplot as plt


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

{}


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

/* ── Sidebar metrics ────────────────────────────────────────────────────── */
[data-testid="stSidebar"] [data-testid="stMetric"] {
    background: #1e293b !important;
    border: 1px solid #334155 !important;
    border-radius: 10px !important;
    padding: 10px 14px !important;
    margin-bottom: 6px !important;



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

hc1, hc2 = st.columns([1, 3])
with hc1:
    selected_date = st.date_input('Working date', key='shared_date', label_visibility='collapsed')
    date_str      = selected_date.strftime('%Y-%m-%d')
    st.markdown(f"<p style='font-size:.75rem;color:#475569;margin-top:-8px'>\U0001f4c5 {selected_date.strftime('%A, %d %B %Y')}</p>", unsafe_allow_html=True)
with hc2:
    try:
        ln  = max(0, projected_liquid_level(selected_date))
        sn  = max(0, projected_solid_level(selected_date))
        lp  = ln/LIQUID_STORAGE_CAPACITY_M3*100
        sp  = sn/SOLID_STORAGE_CAPACITY_TONS*100
        lcd = 'dot-red' if lp>90 else 'dot-yellow' if lp>75 else 'dot-green'
        scd = 'dot-red' if sp>90 else 'dot-yellow' if sp>75 else 'dot-green'
        lfl = max(0, LIQUID_STORAGE_CAPACITY_M3-ln)
        st.markdown(
            f'<div class="status-bar">'
            f'<div class="status-item"><div class="{lcd}"></div><span>Liquid</span>'
            f'<span class="status-val">{ln:.0f}\u202f/\u202f{LIQUID_STORAGE_CAPACITY_M3} m\u00b3</span>'
            f'<span style="color:#334155;font-size:.75rem">({lp:.0f}%)</span></div>'
            f'<span class="status-sep">|</span>'
            f'<div class="status-item"><div class="{scd}"></div><span>Solid</span>'
            f'<span class="status-val">{sn:.0f}\u202f/\u202f{SOLID_STORAGE_CAPACITY_TONS} t</span>'
            f'<span style="color:#334155;font-size:.75rem">({sp:.0f}%)</span></div>'
            f'<span class="status-sep">|</span>'
            f'<div class="status-item"><span>Free liquid</span>'
            f'<span class="status-val">{lfl:.0f} m\u00b3</span></div>'
            f'<span class="status-sep">|</span>'
            f'<div class="status-item"><span style="color:#475569;font-size:.75rem">{date_str}</span></div>'
            f'</div>', unsafe_allow_html=True)
    except Exception:
        pass


tab1,tab2,tab3,tab4,tab5,tab6,tab7,tab8 = st.tabs([
    "📋 Book Slot","🚛 Record Delivery","📆 Daily Schedule","🚚 Truck Calendar",
    "🏭 Storage Forecast","📊 Capacity Report","📦 Delivery Plans","👨‍🌾 Manage Farmers"
])

# ── TAB 1 — BOOK SLOT ────────────────────────────────────────────────────────
with tab1:
    st.subheader("📋 Create a Booking")
    st.caption("For multi-day deliveries use the 📦 Delivery Plans tab.")
    try:
        farmers = fetch_df("SELECT farmer_id,name FROM farmers ORDER BY name")
        mts     = fetch_df("SELECT manure_type_id,name FROM manure_types ORDER BY name")
    except Exception as e:
        st.error(f"DB error: {e}"); farmers = mts = pd.DataFrame()

    if farmers.empty:
        st.warning("No farmers found — add them in 'Manage Farmers' first.")
    else:
        fm = dict(zip(farmers["name"], farmers["farmer_id"]))
        mm = dict(zip(mts["name"],     mts["manure_type_id"]))

        c1,c2,c3 = st.columns(3)
        with c1:
            st.markdown("**Farmer & Schedule**")
            b_farmer = st.selectbox("👨\u200d🌾 Farmer",   list(fm.keys()),   key="b_farmer")
            b_date   = st.date_input("📅 Delivery date",                        key="b_date")
            if b_date.weekday() == 6:
                st.error("❌ Sunday is closed — please select Mon–Sat.")
            b_slot   = st.selectbox("🕐 Time slot",         TIME_SLOTS,        key="b_slot")
        with c2:
            st.markdown("**Manure**")
            b_type  = st.selectbox("🐄 Type",               list(mm.keys()),   key="b_type")
            b_form  = st.selectbox("💧 Form",               ["liquid","solid"], key="b_form")
            b_unit  = "m³" if b_form=="liquid" else "t"
            cap_val = LIQUID_STORAGE_CAPACITY_M3 if b_form=="liquid" else SOLID_STORAGE_CAPACITY_TONS
            _avail  = max(0.0, storage_ok(b_date, 0.0, b_form)[2])
            b_qty   = st.number_input(
                f"📦 Quantity ({b_unit})",
                min_value=0.1,
                max_value=float(max(0.1, _avail)) if _avail > 0 else 0.1,
                value=min(27.0, float(max(0.1, _avail))),
                step=1.0, key="b_qty",
                help=f"Max available on this date: {_avail:.0f} {b_unit}"
            )
        with c3:
            st.markdown("**Transport**")
            b_tr     = st.radio("🚛 Needed?",
                                ["Nein — own transport", "Ja — Plant LKW"],
                                key="b_tr")
            needs_tr = b_tr.startswith("Ja")
            b_worker = (st.selectbox("👷 Worker", WORKERS, key="b_worker")
                        if needs_tr else None)
            if not needs_tr:
                st.success("✅ Farmer brings own transport")

        # Storage check
        ok, lv_after, available, first_ov = storage_ok(b_date, b_qty, b_form)
        already_ov, already_ov_date, already_ov_lv = any_future_overflow(b_form)

        st.markdown("---")
        st.markdown("**📊 Storage feasibility**")
        sc1,sc2,sc3,sc4 = st.columns(4)
        sc1.metric("Current level",   f"{max(0, cap_val-available):.0f} {b_unit}")
        sc2.metric("Available space", f"{available:.0f} {b_unit}",
                   delta="⚠️ tight" if 0 < available < b_qty*1.3 else None,
                   delta_color="inverse" if available < b_qty else "normal")
        sc3.metric("Level after",     f"{max(0,lv_after):.0f} {b_unit}",
                   delta="🔴 OVERFLOW" if not ok else "✅ OK",
                   delta_color="inverse" if not ok else "normal")
        sc4.metric("Capacity",        f"{cap_val} {b_unit}")

        if already_ov:
            st.warning(f"⚠️ Existing bookings already overflow on **{already_ov_date}** "
                       f"({already_ov_lv:.0f} {b_unit}). Cancel some bookings first.")
        if available <= 0:
            st.error(f"🚫 Storage FULL on {b_date} — choose a later date.")
        elif not ok or first_ov:
            st.error(f"❌ Overflow starting **{first_ov or b_date}** "
                     f"(peak {lv_after:.0f} {b_unit}). "
                     f"Max safely bookable: **{available:.0f} {b_unit}**.")

        # Trip info + worker check
        _worker_ok = True
        _wb = 0
        if needs_tr:
            trips   = calc_trips(b_qty, b_form)
            dur     = calc_dur(trips)
            ns      = slots_needed(trips)
            cap_per = LIQUID_TRUCK_CAPACITY_M3 if b_form=="liquid" else SOLID_TRUCK_CAPACITY_TONS
            blocked = get_slots_from(b_slot, ns)
            ti1,ti2,ti3,ti4 = st.columns(4)
            ti1.metric("Trips needed",     trips)
            ti2.metric("Total truck time", f"{dur} min")
            ti3.metric("Slots blocked",    ns)
            ti4.metric("Last load",        f"{b_qty-(trips-1)*cap_per:.1f} {b_unit}")
            st.caption(f"🚛 {TRUCKS[b_form]} | Slots: **{', '.join(blocked)}**")

            # Live truck conflict check
            _truck_cf = truck_conflicts(b_date.strftime("%Y-%m-%d"), TRUCKS[b_form], b_slot, ns)
            if _truck_cf:
                st.error(f"❌ **{TRUCKS[b_form]} is already booked** on slots: "
                         f"{', '.join(_truck_cf)}. Choose a different time slot.")
                _worker_ok = False

            try:
                _wb = int(scalar("""SELECT COALESCE(SUM(COALESCE(total_duration_min,:dd)),0)
                    FROM bookings WHERE delivery_date=:d AND assigned_worker=:w
                    AND status!='cancelled'""",
                    {"d": b_date.strftime("%Y-%m-%d"), "w": b_worker,
                     "dd": TRIP_DURATION_MIN}) or 0)
                pct_w = min((_wb+dur)/240*100, 100)
                ic    = "🔴" if pct_w>90 else "🟡" if pct_w>60 else "🟢"
                if _wb + dur > 240:
                    st.error(f"❌ **{b_worker}** only has {240-_wb} min left today "
                             f"(50% rule = 240 min/day). This delivery needs {dur} min. "
                             f"Assign the other worker or reduce quantity.")
                    _worker_ok = False
                else:
                    st.progress(int(pct_w),
                                text=f"{ic} {b_worker}: {_wb}+{dur}={_wb+dur}/240 min")
            except Exception:
                pass

        st.divider()
        _truck_blocked = needs_tr and bool(
            truck_conflicts(b_date.strftime("%Y-%m-%d"), TRUCKS[b_form], b_slot,
                            slots_needed(calc_trips(b_qty, b_form))))
        _btn_blocked = ((not ok) or (available <= 0) or (b_date.weekday() == 6)
                        or bool(first_ov) or not _worker_ok or _truck_blocked)
        if b_date.weekday() == 6:
            st.error("❌ Cannot book on Sunday.")
        if st.button("📌 Confirm Booking", key="book_btn", type="primary",
                     disabled=_btn_blocked):
            b_ds = b_date.strftime("%Y-%m-%d")
            try:
                errs = []
                ok2, lv2, av2, fov2 = storage_ok(b_date, b_qty, b_form)
                if not ok2 or fov2:
                    errs.append(f"❌ Overflow on {fov2 or b_ds}: peak {lv2:.0f} > {cap_val}.")
                trips = dur = ns = 0; atr = None
                if needs_tr:
                    trips = calc_trips(b_qty, b_form); dur = calc_dur(trips)
                    ns    = slots_needed(trips);       atr = TRUCKS[b_form]
                    cf    = truck_conflicts(b_ds, atr, b_slot, ns)
                    if cf: errs.append(f"❌ {atr} conflict: {', '.join(cf)}")
                    try:
                        wb2 = int(scalar("""SELECT COALESCE(SUM(COALESCE(total_duration_min,:dd)),0)
                            FROM bookings WHERE delivery_date=:d AND assigned_worker=:w
                            AND status!='cancelled'""",
                            {"d":b_ds,"w":b_worker,"dd":TRIP_DURATION_MIN}) or 0)
                        if wb2 + dur > 240:
                            errs.append(f"❌ {b_worker} has only {240-wb2} min left "
                                        f"(needs {dur} min). Assign the other worker.")
                    except Exception:
                        pass
                if errs:
                    for e in errs: st.error(e)
                else:
                    bsl = get_slots_from(b_slot, ns) if needs_tr else []
                    row = exec_one("""
                        INSERT INTO bookings
                          (farmer_id,delivery_date,time_slot,status,expected_tons,
                           manure_form,planned_manure_type_id,transport_required,
                           assigned_truck,assigned_worker,trips_count,
                           total_duration_min,end_time_slot)
                        VALUES (:fid,:dt,:slot,'booked',:qty,:form,:tid,
                                :tr,:truck,:worker,:trips,:dur,:end)
                        RETURNING booking_id
                    """, {"fid":int(fm[b_farmer]),"dt":b_ds,"slot":b_slot,
                          "qty":float(b_qty),"form":b_form,"tid":int(mm[b_type]),
                          "tr":needs_tr,"truck":atr,"worker":b_worker,
                          "trips":trips,"dur":dur,"end":bsl[-1] if bsl else b_slot},
                        fetchone=True)
                    bid = row[0] if row else "?"
                    st.success(f"✅ Booking **#{bid}** — {b_farmer} | "
                               f"{b_form.title()} {b_qty:.0f} {b_unit} | " +
                               (f"🚛 {atr}/{b_worker} | {trips}×{TRIP_DURATION_MIN}min"
                                if needs_tr else "🚜 Own transport"))
                    _fetch_booked_schedule.clear()
            except Exception as ex:
                st.error(f"❌ {ex}")


# ── TAB 2 — RECORD DELIVERY ──────────────────────────────────────────────────
with tab2:
    st.subheader("🚛 Record Delivery or Cancel Booking")
    try:
        ob = fetch_df("""
            SELECT b.booking_id, f.name AS farmer, b.delivery_date, b.time_slot,
                   b.expected_tons, b.manure_form,
                   COALESCE(b.assigned_truck,'own') AS truck,
                   COALESCE(b.assigned_worker,'—')  AS worker,
                   mt.name AS planned_type, b.status
            FROM bookings b JOIN farmers f ON f.farmer_id=b.farmer_id
            LEFT JOIN manure_types mt ON mt.manure_type_id=b.planned_manure_type_id
            WHERE b.status='booked' ORDER BY b.delivery_date, b.time_slot
        """)
        mtd = fetch_df("SELECT manure_type_id,name FROM manure_types ORDER BY name")
    except Exception as e:
        st.error(f"DB error: {e}"); ob = pd.DataFrame(); mtd = pd.DataFrame()

    if ob.empty:
        st.info("📭 No open bookings.")
    else:
        st.dataframe(ob, use_container_width=True, hide_index=True)
        mm2 = dict(zip(mtd["name"], mtd["manure_type_id"]))
        bids= ob["booking_id"].tolist()
        st.markdown("#### ✅ Record a Delivery")
        r1,r2,r3 = st.columns(3)
        with r1: d_bid = st.selectbox("Booking ID",      bids,            key="d_bid")
        with r2: d_mt  = st.selectbox("Manure type",     list(mm2.keys()),key="d_mt")
        with r3: d_qty = st.number_input("Actual qty",   min_value=0.1,
                                         max_value=500.0, value=20.0,     key="d_qty")
        if st.button("✅ Record delivery", key="rec_btn", type="primary"):
            try:
                exec_one("INSERT INTO deliveries (booking_id,manure_type_id,quantity_tons) "
                         "VALUES (:bid,:mid,:qty)",
                         {"bid":int(d_bid),"mid":int(mm2[d_mt]),"qty":float(d_qty)})
                exec_one("UPDATE bookings SET status='completed' WHERE booking_id=:bid",
                         {"bid":int(d_bid)})
                st.success("✅ Delivery recorded."); st.rerun()
            except Exception as e: st.error(f"❌ {e}")
        st.divider()
        st.markdown("#### ❌ Cancel a Booking")
        cb = st.selectbox("Booking ID", bids, key="cb")
        if st.button("🗑️ Cancel", key="canc_btn"):
            try:
                exec_one("UPDATE bookings SET status='cancelled' WHERE booking_id=:id",
                         {"id":int(cb)})
                st.success(f"✅ Booking #{cb} cancelled."); _fetch_booked_schedule.clear(); st.rerun()
            except Exception as e: st.error(f"❌ {e}")

# ── TAB 3 — DAILY SCHEDULE ───────────────────────────────────────────────────
with tab3:
    st.subheader(f"📆 Daily Schedule — {date_str}")
    try:
        sc = fetch_df("""
            SELECT b.booking_id, b.time_slot, f.name AS farmer,
                   b.manure_form, mt.name AS type,
                   b.expected_tons, COALESCE(d.quantity_tons,0) AS actual,
                   COALESCE(b.transport_required,FALSE)        AS transport,
                   COALESCE(b.assigned_truck,'own')            AS truck,
                   COALESCE(b.assigned_worker,'—')             AS worker,
                   COALESCE(b.trips_count,1)                   AS trips,
                   b.status
            FROM bookings b JOIN farmers f ON f.farmer_id=b.farmer_id
            LEFT JOIN deliveries d ON d.booking_id=b.booking_id
            LEFT JOIN manure_types mt ON mt.manure_type_id=b.planned_manure_type_id
            WHERE b.delivery_date=:date ORDER BY b.time_slot
        """, {"date":date_str})
    except Exception as e:
        st.error(f"DB error: {e}"); sc = pd.DataFrame()

    if sc.empty:
        st.info(f"📭 No bookings for {date_str}.")
    else:
        st.dataframe(sc, use_container_width=True, hide_index=True)
        liq = sc[sc["manure_form"]=="liquid"]["expected_tons"].sum()
        sol = sc[sc["manure_form"]=="solid"]["expected_tons"].sum()
        m1,m2,m3,m4 = st.columns(4)
        m1.metric("Liquid (m³)",   f"{liq:.0f}")
        m2.metric("Solid (t)",     f"{sol:.0f}")
        m3.metric("Plant LKW",     sc[sc["transport"]==True].shape[0])
        m4.metric("Own transport", sc[sc["transport"]==False].shape[0])
    st.download_button("⬇️ CSV", data=sc.to_csv(index=False).encode() if not sc.empty else b"",
                       file_name=f"schedule_{date_str}.csv", mime="text/csv", key="dl_s3")

# ── TAB 4 — TRUCK CALENDAR ───────────────────────────────────────────────────
with tab4:
    st.subheader(f"🚚 Truck Calendar — {date_str}")
    ts = get_truck_schedule(selected_date)
    cl1,cl2 = st.columns(2)

    def render_truck(col, truck_name, form):
        cap  = LIQUID_TRUCK_CAPACITY_M3 if form=="liquid" else SOLID_TRUCK_CAPACITY_TONS
        unit = "m³" if form=="liquid" else "t"
        with col:
            st.markdown(f"### {truck_name} — {form.title()}")
            st.caption(f"{cap} {unit}/trip · {TRIP_DURATION_MIN} min/trip · Mon–Sat 07–19h")
            sm = {}
            if not ts.empty:
                for _, r in ts[ts["truck"]==truck_name].iterrows():
                    n = slots_needed(int(r.get("trips_count",1) or 1))
                    for s in get_slots_from(str(r.get("time_slot","")), n):
                        sm[s] = r
            rows = []
            for slot in TIME_SLOTS:
                h = int(slot.split(":")[0])
                if slot in sm:
                    r = sm[slot]; is_s = str(r.get("time_slot",""))==slot
                    tn = int(r.get("trips_count",1) or 1)
                    dm = int(r.get("total_duration_min",TRIP_DURATION_MIN) or TRIP_DURATION_MIN)
                    rows.append({"🕐":slot,"Status":"🔴 START" if is_s else "🟠 cont.",
                                 "Farmer":r.get("farmer","") if is_s else "↑",
                                 f"Qty":f"{r.get('expected_tons','')}{unit}" if is_s else "",
                                 "Trips":f"{tn}×{TRIP_DURATION_MIN}={dm}min" if is_s else "",
                                 "Worker":r.get("worker","") if is_s else ""})
                elif 7<=h<19:
                    rows.append({"🕐":slot,"Status":"🟢 Free","Farmer":"","Qty":"","Trips":"","Worker":""})
                else:
                    rows.append({"🕐":slot,"Status":"—","Farmer":"","Qty":"","Trips":"","Worker":""})
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            if not ts.empty:
                td = ts[ts["truck"]==truck_name]
                if not td.empty:
                    st.markdown("**Worker utilisation:**")
                    for w in WORKERS:
                        wr = td[td["worker"]==w]
                        um = int(wr["total_duration_min"].fillna(TRIP_DURATION_MIN).sum()) if not wr.empty else 0
                        pc = min(um/240*100,100)
                        ic = "🔴" if pc>90 else "🟡" if pc>60 else "🟢"
                        st.progress(int(pc), text=f"{ic} {w}: {um}/240 min ({pc:.0f}%)")

    render_truck(cl1,"LKW1","liquid"); render_truck(cl2,"LKW2","solid")
    if not ts.empty:
        st.divider(); st.markdown("#### All deliveries today")
        st.dataframe(ts, use_container_width=True, hide_index=True)

# ── TAB 5 — STORAGE FORECAST ─────────────────────────────────────────────────
with tab5:
    st.subheader("🏭 Storage Forecast — Synchronized with ALL Bookings & Plans")
    fc_d = st.slider("Days ahead", 7, 30, 14, key="fc_d")
    try:
        fdf = build_forecast_df(fc_d)
    except Exception as e:
        st.error(f"Forecast error: {e}"); fdf = pd.DataFrame()

    if not fdf.empty:
        tr = fdf[fdf["Date"]==date.today().strftime("%Y-%m-%d")]
        if not tr.empty:
            r = tr.iloc[0]
            f1,f2,f3,f4 = st.columns(4)
            f1.metric("Today Liquid",f"{r['Liquid Level (m³)']:.0f} m³",
                      delta=f"{r['Liquid Fill %']:.1f}%")
            f2.metric("Free Liquid", f"{LIQUID_STORAGE_CAPACITY_M3-r['Liquid Level (m³)']:.0f} m³")
            f3.metric("Today Solid", f"{r['Solid Level (t)']:.0f} t",
                      delta=f"{r['Solid Fill %']:.1f}%")
            f4.metric("Free Solid",  f"{SOLID_STORAGE_CAPACITY_TONS-r['Solid Level (t)']:.0f} t")

        def hl(row):
            ls = str(row.get("Liquid Status",""))
            ss = str(row.get("Solid Status",""))
            if "OVERFLOW" in ls or "OVERFLOW" in ss: return ["background-color:#3d1a1a"]*len(row)
            if "HIGH"     in ls or "HIGH"     in ss: return ["background-color:#2d2a1a"]*len(row)
            return [""]*len(row)
        st.dataframe(fdf.style.apply(hl,axis=1), use_container_width=True, hide_index=True)

        fig,(ax1,ax2) = plt.subplots(2,1,figsize=(12,7),sharex=True)
        fig.patch.set_facecolor("#0f1a0f"); fig.subplots_adjust(hspace=0.35)
        x = list(range(len(fdf)))
        for ax in [ax1,ax2]:
            ax.set_facecolor("#1a2d1a"); ax.tick_params(colors="#8ab885")
            ax.spines[:].set_color("#2d4a2d")

        ax1.bar(x,fdf["Liquid In (m³)"],alpha=0.7,color="#4CAF50",label="Incoming m³")
        ax1.bar(x,[-200]*len(x),alpha=0.5,color="#FF7043",label="Outflow −200 m³")
        ax1.plot(x,fdf["Liquid Level (m³)"],marker="o",lw=2,color="#81d4fa",label="Level")
        ax1.axhline(LIQUID_STORAGE_CAPACITY_M3,ls="--",color="#ef5350",lw=1.5,
                    label=f"Limit {LIQUID_STORAGE_CAPACITY_M3} m³")
        ax1.axhline(LIQUID_STORAGE_CAPACITY_M3*0.85,ls=":",color="#ffb74d",lw=1,label="85% warn")
        ax1.set_ylabel("m³",color="#8ab885"); ax1.legend(fontsize=7)
        ax1.set_title("Liquid Storage (Vorgrube)",color="#a8d5a2")
        ax1.grid(True,ls="--",lw=0.4,alpha=0.4,color="#2d4a2d")

        ax2.bar(x,fdf["Solid In (t)"],alpha=0.7,color="#8D6E63",label="Incoming t")
        ax2.bar(x,[-DAILY_SOLID_OUTFLOW_TONS]*len(x),alpha=0.5,color="#FF7043",
                label=f"Outflow −{DAILY_SOLID_OUTFLOW_TONS} t")
        ax2.plot(x,fdf["Solid Level (t)"],marker="s",lw=2,color="#ce93d8",label="Level")
        ax2.axhline(SOLID_STORAGE_CAPACITY_TONS,ls="--",color="#ef5350",lw=1.5,
                    label=f"Limit {SOLID_STORAGE_CAPACITY_TONS} t")
        ax2.axhline(SOLID_STORAGE_CAPACITY_TONS*0.85,ls=":",color="#ffb74d",lw=1,label="85% warn")
        ax2.set_ylabel("t",color="#8ab885"); ax2.legend(fontsize=7)
        ax2.set_title("Solid Manure Storage",color="#a8d5a2")
        ax2.grid(True,ls="--",lw=0.4,alpha=0.4,color="#2d4a2d")
        ax2.set_xticks(x)
        ax2.set_xticklabels(fdf["Date"]+" "+fdf["Day"],rotation=40,ha="right",
                            fontsize=7,color="#8ab885")
        plt.tight_layout(); st.pyplot(fig,use_container_width=True)

        ov = fdf[fdf["Liquid Status"].str.contains("OVERFLOW",na=False) |
                 fdf["Solid Status"].str.contains("OVERFLOW",na=False)]
        hi = fdf[fdf["Liquid Status"].str.contains("HIGH",na=False) |
                 fdf["Solid Status"].str.contains("HIGH",na=False)]
        if not ov.empty:
            st.error(f"🔴 **Overflow on:** {', '.join(ov['Date'].tolist())} — reschedule or cancel bookings!")
        if not hi.empty:
            st.warning(f"🟡 **Storage >85% on:** {', '.join(hi['Date'].tolist())}")
        st.download_button("⬇️ Download forecast CSV",
                           fdf.to_csv(index=False).encode(),
                           file_name="storage_forecast.csv", mime="text/csv", key="dl_fc")

# ── TAB 6 — CAPACITY REPORT ──────────────────────────────────────────────────
with tab6:
    st.subheader(f"📊 Capacity Report — {date_str}")
    try:
        el = float(scalar("SELECT COALESCE(SUM(expected_tons),0) FROM bookings "
                          "WHERE delivery_date=:d AND manure_form='liquid' AND status='booked'",
                          {"d":date_str}) or 0)
        es = float(scalar("SELECT COALESCE(SUM(expected_tons),0) FROM bookings "
                          "WHERE delivery_date=:d AND manure_form='solid' AND status='booked'",
                          {"d":date_str}) or 0)
        at = float(scalar("SELECT COALESCE(SUM(d.quantity_tons),0) FROM deliveries d "
                          "JOIN bookings b ON b.booking_id=d.booking_id WHERE b.delivery_date=:d",
                          {"d":date_str}) or 0)
    except Exception as e:
        st.error(f"DB error: {e}"); el=es=at=0.0
    try:
        ptr = int(scalar("SELECT COUNT(*) FROM bookings WHERE delivery_date=:d "
                         "AND transport_required=TRUE AND status!='cancelled'",{"d":date_str}) or 0)
        otr = int(scalar("SELECT COUNT(*) FROM bookings WHERE delivery_date=:d "
                         "AND (transport_required=FALSE OR transport_required IS NULL) "
                         "AND status!='cancelled'",{"d":date_str}) or 0)
    except Exception:
        ptr=otr=0
    try:
        ll = max(0, projected_liquid_level(selected_date))
        sl = max(0, projected_solid_level(selected_date))
    except Exception:
        ll=sl=0.0

    r1,r2,r3,r4 = st.columns(4)
    r1.metric("Liquid in today",    f"{el:.0f} m³",  delta=f"{el/LIQUID_STORAGE_CAPACITY_M3*100:.1f}%")
    r2.metric("Liquid level",       f"{ll:.0f} m³",  delta=f"{ll/LIQUID_STORAGE_CAPACITY_M3*100:.1f}% full")
    r3.metric("Solid in today",     f"{es:.0f} t",   delta=f"{es/SOLID_STORAGE_CAPACITY_TONS*100:.1f}%")
    r4.metric("Solid level",        f"{sl:.0f} t",   delta=f"{sl/SOLID_STORAGE_CAPACITY_TONS*100:.1f}% full")
    st.divider()
    t1,t2,t3 = st.columns(3)
    t1.metric("Plant LKW deliveries",     ptr)
    t2.metric("Own-transport deliveries", otr)
    t3.metric("Actually delivered",       f"{at:.0f} m³/t")
    st.caption(f"Daily liquid outflow: −{DAILY_LIQUID_OUTFLOW_M3} m³/day")

    fig,axes = plt.subplots(1,2,figsize=(12,4))
    fig.patch.set_facecolor("#0f1a0f")
    for ax,(title,inc,lev,cap,unit) in zip(axes,[
        ("Liquid (Vorgrube)",el,ll,LIQUID_STORAGE_CAPACITY_M3,"m³"),
        ("Solid Manure",     es,sl,SOLID_STORAGE_CAPACITY_TONS,"t")
    ]):
        ax.set_facecolor("#1a2d1a"); ax.tick_params(colors="#8ab885")
        ax.spines[:].set_color("#2d4a2d")
        bars=ax.bar(["Incoming","Level","Capacity"],[inc,lev,cap],
                    color=["#4CAF50","#81d4fa","#37474f"],alpha=0.85)
        ax.axhline(cap,ls="--",color="#ef5350",lw=1.5)
        for b in bars:
            h=b.get_height()
            ax.text(b.get_x()+b.get_width()/2,h+cap*0.01,
                    f"{h:.0f}{unit}",ha="center",va="bottom",fontsize=8,color="#e8f5e8")
        ax.set_title(f"{title} — {date_str}",color="#a8d5a2")
        ax.set_ylabel(unit,color="#8ab885")
        ax.grid(True,ls="--",lw=0.4,alpha=0.4,color="#2d4a2d")
    plt.tight_layout(); st.pyplot(fig,use_container_width=True)

    rdf = pd.DataFrame([{"date":date_str,
        "liquid_incoming_m3":el,"liquid_level_m3":ll,"liquid_capacity_m3":LIQUID_STORAGE_CAPACITY_M3,
        "liquid_outflow_m3":DAILY_LIQUID_OUTFLOW_M3,"solid_incoming_t":es,"solid_level_t":sl,
        "solid_capacity_t":SOLID_STORAGE_CAPACITY_TONS,"actual_delivered":at,
        "plant_lkw":ptr,"own_transport":otr}])
    st.dataframe(rdf, use_container_width=True)
    dl1,dl2=st.columns(2)
    with dl1:
        st.download_button("⬇️ CSV",rdf.to_csv(index=False).encode(),
                           file_name=f"capacity_{date_str}.csv",mime="text/csv",key="dl_c6")
    with dl2:
        try:
            buf=io.BytesIO()
            with pd.ExcelWriter(buf,engine="openpyxl") as w:
                rdf.to_excel(w,index=False,sheet_name="Capacity")
                build_forecast_df(14).to_excel(w,index=False,sheet_name="Forecast")
            st.download_button("⬇️ Excel",buf.getvalue(),
                               file_name=f"report_{date_str}.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                               key="dl_xl6")
        except Exception as e: st.error(f"Excel error: {e}")

# ── TAB 7 — DELIVERY PLANS ───────────────────────────────────────────────────
with tab7:
    st.subheader("📦 Delivery Plans — Large Quantity Over Multiple Days")
    st.info("Farmer commits e.g. **1 000 m³ over 10 days**. System splits into daily trips, "
            "checks storage feasibility **per day**, and creates bookings automatically. "
            "Overflow or truck-conflict days are skipped with a report.")
    pc,pv = st.tabs(["➕ Create Plan","📋 View Plans"])

    with pc:
        try:
            try:
                fp = fetch_df("SELECT farmer_id,name FROM farmers WHERE active=TRUE ORDER BY name")
            except Exception:
                fp = fetch_df("SELECT farmer_id,name FROM farmers ORDER BY name")
            mtp = fetch_df("SELECT manure_type_id,name FROM manure_types ORDER BY name")
        except Exception as e:
            st.error(f"DB error: {e}"); fp=mtp=pd.DataFrame()

        if fp.empty:
            st.warning("No farmers. Add in 'Manage Farmers' first.")
        else:
            fmp=dict(zip(fp["name"],fp["farmer_id"])); mmp=dict(zip(mtp["name"],mtp["manure_type_id"]))
            pc1,pc2=st.columns(2)
            with pc1:
                ppf=st.selectbox("👨‍🌾 Farmer",   list(fmp.keys()),key="ppf")
                ppfm=st.selectbox("💧 Form",     ["liquid","solid"],key="ppfm")
                ppt=st.selectbox("🐄 Type",      list(mmp.keys()),key="ppt")
                ppq=st.number_input("📦 Total qty",min_value=27.0,max_value=10000.0,
                                    value=500.0,step=27.0,key="ppq")
            with pc2:
                pps=st.date_input("📅 Start",value=date.today(),key="pps")
                ppe=st.date_input("📅 End",  value=date.today()+timedelta(days=9),key="ppe")
                if pps.weekday() == 6:
                    st.warning("⚠️ Start date is Sunday — first booking will be Monday.")
                if ppe.weekday() == 6:
                    st.warning("⚠️ End date is Sunday — last booking will be Saturday.")
                ppsl=st.selectbox("🕐 Slot",TIME_SLOTS,key="ppsl")
                ppn=st.text_area("📝 Notes",key="ppn",height=68)
            pp_tr=st.radio("🚛 Transport?",["Nein — own","Ja — Plant LKW"],key="pp_tr",horizontal=True)
            pp_needs=pp_tr.startswith("Ja")
            pp_worker=st.selectbox("👷 Worker",WORKERS,key="pp_w") if pp_needs else None

            if ppe>=pps:
                cap_u=LIQUID_TRUCK_CAPACITY_M3 if ppfm=="liquid" else SOLID_TRUCK_CAPACITY_TONS
                unit_u="m³" if ppfm=="liquid" else "t"
                wdays=[pps+timedelta(days=i) for i in range((ppe-pps).days+1)
                       if (pps+timedelta(days=i)).weekday()!=6]
                nd=len(wdays)
                if nd>0:
                    dq=ppq/nd; tpd=max(1,-(-int(dq)//int(cap_u))); da=min(tpd*cap_u,ppq)
                    dur_u=calc_dur(tpd)
                    v1,v2,v3,v4=st.columns(4)
                    v1.metric("Working days",nd)
                    v2.metric("Daily qty",f"{da:.1f} {unit_u}")
                    v3.metric("Trips/day",tpd)
                    v4.metric("Truck time/day",f"{dur_u} min")

                    prev=[]; rem=ppq; wdays_warn=[]
                    sim_schedule   = dict(_fetch_booked_schedule())
                    sim_truck_slots= {}
                    sim_worker_mins= {}
                    pp_truck = TRUCKS.get(ppfm) if pp_needs else None
                    # Track blocking conditions for the button
                    _any_overflow    = False
                    _any_driver_over = False
                    _any_truck_cf    = False

                    for dp in wdays:
                        if rem<=0: break
                        dqd    = min(da, rem)
                        dp_str = dp.strftime("%Y-%m-%d")

                        # Storage check
                        ok_p,lv_p,av_p,fov_p = storage_ok(dp,dqd,ppfm,sim_schedule)
                        if not ok_p and av_p > 0:
                            dqd = round(av_p, 2)
                            ok_p,lv_p,av_p,fov_p = storage_ok(dp,dqd,ppfm,sim_schedule)

                        trips_p = max(1,-(-int(dqd)//int(cap_u)))
                        dur_p   = calc_dur(trips_p)
                        ns_p    = slots_needed(trips_p)
                        blk_p   = get_slots_from(ppsl, ns_p)

                        # Truck conflict check
                        truck_flag = "—"
                        if pp_needs and pp_truck:
                            db_cf  = truck_conflicts(dp_str, pp_truck, ppsl, ns_p)
                            mem_cf = [s for s in blk_p if sim_truck_slots.get((dp_str, s))]
                            all_cf = list(set(db_cf + mem_cf))
                            truck_flag = f"🔴 {', '.join(all_cf)}" if all_cf else "✅ Free"
                            if all_cf:
                                _any_truck_cf = True

                        # Driver check
                        driver_flag = "—"
                        if pp_needs and pp_worker:
                            try:
                                db_m = int(scalar(
                                    """SELECT COALESCE(SUM(COALESCE(total_duration_min,:dd)),0)
                                       FROM bookings WHERE delivery_date=:d AND assigned_worker=:w
                                       AND status!='cancelled'""",
                                    {"d":dp_str,"w":pp_worker,"dd":TRIP_DURATION_MIN}) or 0)
                            except Exception:
                                db_m = 0
                            plan_m  = sim_worker_mins.get(dp_str, 0)
                            total_m = db_m + plan_m + dur_p
                            pct_d   = min(total_m / 240 * 100, 100)
                            driver_flag = (f"🔴 {total_m}/240 min" if total_m > 240
                                           else f"🟡 {total_m}/240 min" if pct_d > 75
                                           else f"🟢 {total_m}/240 min")
                            if total_m > 240:
                                _any_driver_over = True

                        storage_flag = ("✅ OK" if (ok_p and not fov_p)
                                        else ("⚠️ Future OV" if fov_p else "🔴 Full"))
                        if not ok_p or fov_p:
                            wdays_warn.append(dp_str)
                            _any_overflow = True

                        # Update sims for accepted days
                        has_conflict = (pp_needs and pp_truck and
                                        bool(set(truck_conflicts(dp_str, pp_truck, ppsl, ns_p) +
                                                 [s for s in blk_p if sim_truck_slots.get((dp_str,s))])))
                        driver_exceeded = (pp_needs and pp_worker and
                                           (sim_worker_mins.get(dp_str,0) + dur_p +
                                            (int(scalar("""SELECT COALESCE(SUM(COALESCE(total_duration_min,:dd)),0)
                                                FROM bookings WHERE delivery_date=:d AND assigned_worker=:w
                                                AND status!='cancelled'""",
                                                {"d":dp_str,"w":pp_worker,"dd":TRIP_DURATION_MIN}) or 0)) > 240))
                        if ok_p and not fov_p and not has_conflict and not driver_exceeded:
                            key = (dp_str, ppfm)
                            sim_schedule[key] = sim_schedule.get(key, 0.0) + dqd
                            if pp_needs and pp_truck:
                                for s in blk_p: sim_truck_slots[(dp_str, s)] = True
                            if pp_needs and pp_worker:
                                sim_worker_mins[dp_str] = sim_worker_mins.get(dp_str,0) + dur_p

                        prev.append({"Date":dp.strftime("%Y-%m-%d (%a)"),
                                     f"Qty({unit_u})":f"{dqd:.1f}",
                                     "Trips":trips_p,
                                     "Level after":f"{max(0,lv_p):.0f}/{LIQUID_STORAGE_CAPACITY_M3 if ppfm=='liquid' else SOLID_STORAGE_CAPACITY_TONS}",
                                     "Storage":storage_flag,
                                     "Truck":truck_flag,
                                     "Driver":driver_flag})
                        rem -= dqd

                    st.dataframe(pd.DataFrame(prev),use_container_width=True,hide_index=True)

                    # ── Blocking messages ──
                    if _any_overflow:
                        st.error(f"🔴 **Storage overflow on: {', '.join(wdays_warn)}** — "
                                 f"reduce total quantity or extend the date range so "
                                 f"outflow creates enough space before each delivery.")
                    if _any_driver_over:
                        st.error(f"🔴 **Driver {pp_worker} exceeds 240 min/day limit** on one or more days — "
                                 f"choose the other worker or reduce daily delivery quantity.")
                    if _any_truck_cf:
                        st.warning(f"🟠 **Truck {pp_truck} has slot conflicts** on one or more days — "
                                   f"choose an earlier/later time slot.")

                    _plan_blocked = _any_overflow or _any_driver_over
            else:
                st.warning("End date must be after start date.")

            st.divider()
            # Button is blocked if preview found overflow or driver issues
            # If preview hasn't run yet (no wdays), default to not blocked
            _plan_blocked = locals().get("_plan_blocked", False)
            if _plan_blocked:
                st.info("💡 Fix the issues highlighted above before creating the plan.")
            if st.button("✅ Create Plan + Bookings", key="pp_create", type="primary",
                         disabled=_plan_blocked):
                if ppe<pps: st.error("End date must be after start date.")
                else:
                    try:
                        fid=int(fmp[ppf]); tid=int(mmp[ppt])
                        wd2=[pps+timedelta(days=i) for i in range((ppe-pps).days+1)
                             if (pps+timedelta(days=i)).weekday()!=6]
                        pr=exec_one("""
                            INSERT INTO delivery_plans
                              (farmer_id,manure_form,manure_type_id,total_quantity,
                               start_date,end_date,daily_quantity,transport_required,
                               assigned_worker,notes,status)
                            VALUES (:fid,:form,:tid,:total,:start,:end,:daily,
                                    :transport,:worker,:notes,'active')
                            RETURNING plan_id
                        """,{"fid":fid,"form":ppfm,"tid":tid,"total":float(ppq),
                             "start":pps.strftime("%Y-%m-%d"),"end":ppe.strftime("%Y-%m-%d"),
                             "daily":round(ppq/max(1,len(wd2)),2),
                             "transport":pp_needs,"worker":pp_worker,"notes":ppn or ""},
                            fetchone=True)
                        pid=pr[0] if pr else None
                        ok_l,ov_s,cf_s=build_plan_bookings(fid,ppfm,tid,float(ppq),
                                                            pps,ppe,ppsl,pp_needs,pp_worker)
                        created=0
                        for b in ok_l:
                            exec_one("""
                                INSERT INTO bookings
                                  (farmer_id,delivery_date,time_slot,status,expected_tons,
                                   manure_form,planned_manure_type_id,transport_required,
                                   assigned_truck,assigned_worker,trips_count,
                                   total_duration_min,end_time_slot,delivery_plan_id)
                                VALUES (:farmer_id,:delivery_date,:time_slot,:status,
                                        :expected_tons,:manure_form,:planned_manure_type_id,
                                        :transport_required,:assigned_truck,:assigned_worker,
                                        :trips_count,:total_duration_min,:end_time_slot,:pid)
                            """,{**b,"pid":pid}); created+=1
                        ur="m³" if ppfm=="liquid" else "t"
                        msg=f"✅ Plan **#{pid}** — **{created}** bookings ({ppq:.0f} {ur} for {ppf})."
                        if ov_s: msg+=f"\n🔴 {len(ov_s)} day(s) skipped (overflow): {', '.join(d['date'] for d in ov_s)}"
                        if cf_s: msg+=f"\n🟠 {len(cf_s)} day(s) skipped (truck conflict): {', '.join(d['date'] for d in cf_s)}"
                        st.success(msg); _fetch_booked_schedule.clear(); st.rerun()
                    except Exception as ex: st.error(f"❌ {ex}")

with tab8:
    st.subheader("👨‍🌾 Manage Farmers")
    fa,fl=st.tabs(["➕ Add Farmer","📋 Farmer List"])

    with fa:
        st.markdown("#### Register a New Farmer")
        a1,a2=st.columns(2)
        with a1:
            nfn=st.text_input("👤 Name *",   key="nfn",placeholder="Hans Müller")
            nfp=st.text_input("📞 Phone",    key="nfp",placeholder="+49 251 …")
            nfe=st.text_input("📧 Email",    key="nfe",placeholder="hans@farm.de")
        with a2:
            nfa=st.text_area("🏡 Address",   key="nfa",height=80)
            nfno=st.text_area("📝 Notes",    key="nfno",height=80)
        b1,b2=st.columns(2)
        with b1: nfl=st.checkbox("💧 Liquid manure",value=True,key="nfl")
        with b2: nfs=st.checkbox("🟫 Solid manure", value=False,key="nfs")
        nftr=st.radio("🚛 Transport",["🚜 Own","🚛 Plant LKW"],key="nftr",horizontal=True)
        nfd=st.number_input("🗺️ One-way trip (min)",min_value=1,max_value=240,value=55,step=5,key="nfd")

        st.divider()
        if st.button("💾 Register Farmer",key="nf_save",type="primary"):
            if not nfn.strip(): st.error("❌ Name is required.")
            else:
                try:
                    if int(scalar("SELECT COUNT(*) FROM farmers WHERE LOWER(name)=LOWER(:n)",
                                  {"n":nfn.strip()}) or 0)>0:
                        st.error(f"❌ '{nfn}' already exists.")
                    else:
                        nv=(f"Delivers:{'liquid ' if nfl else ''}{'solid ' if nfs else ''}| "
                            f"Transport:{'own' if nftr.startswith('🚜') else 'plant LKW'}|"
                            f"Distance:{nfd}min|{nfno.strip()}").strip("|")
                        try:
                            row=exec_one("INSERT INTO farmers (name,phone,email,address,notes,active) "
                                         "VALUES (:n,:p,:e,:a,:no,TRUE) RETURNING farmer_id",
                                         {"n":nfn.strip(),"p":nfp.strip() or None,
                                          "e":nfe.strip() or None,"a":nfa.strip() or None,
                                          "no":nv or None},fetchone=True)
                        except Exception:
                            row=exec_one("INSERT INTO farmers (name) VALUES (:n) RETURNING farmer_id",
                                         {"n":nfn.strip()},fetchone=True)
                        st.success(f"✅ **{nfn}** registered (ID {row[0] if row else '?'})")
                        st.balloons()
                except Exception as e: st.error(f"❌ {e}")


