import os
import json
import logging
import requests
import traceback
from datetime import date
from garminconnect import Garmin

# ==============================================================================
# CONFIGURATION & SETUP / CONFIGURACIÓN Y SET UP
# ==============================================================================

# --- CLOUD RUN HACK ---
# Force Garmin library to use /tmp for session tokens (Read-only filesystem fix)
# Forzar a la librería Garmin a usar /tmp para tokens (Arreglo de sistema de archivos de solo lectura)
os.environ['HOME'] = '/tmp'

# --- ENVIRONMENT VARIABLES / VARIABLES DE ENTORNO ---
GARMIN_EMAIL = os.environ.get('GARMIN_EMAIL')
GARMIN_PASSWORD = os.environ.get('GARMIN_PASSWORD')
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')

# Language Selection: 'es' (Spanish) or 'en' (English). Default: 'es'
# Selección de Idioma: 'es' (Español) o 'en' (Inglés). Por defecto: 'es'
LANG_CODE = os.environ.get('BOT_LANGUAGE', 'es').lower()

# --- CONSTANTS / CONSTANTES ---
# Connect IQ ID for Efficiency Factor (Data Field)
# ID de Connect IQ para el Factor de Eficiencia
EF_APP_ID = "e9f83886-2e1d-448e-aa0a-0cdfb9160df9"
EF_FIELD_NUM_GLOBAL = 2  # Field ID in Summary / ID en Resumen
EF_FIELD_NUM_LAP = 1     # Field ID in Laps / ID en Vueltas

# ==============================================================================
# TRANSLATION DICTIONARY / DICCIONARIO DE TRADUCCIÓN
# ==============================================================================
TRANS = {
    'es': {
        # Status Messages
        'loading_1': "⏳ 1/3 Conectando...",
        'loading_2': "✅ 2/3 Descargando...",
        'loading_vital': "⏳ Obteniendo signos vitales...",
        'loading_hist': "⏳ Consultando historial...",
        'err_not_found': "❌ No encontré esa actividad.",
        'err_empty': "❌ Error: Actividad vacía.",
        'err_menu': "❌ Error obteniendo menú",
        'err_morning': "❌ Error obteniendo reporte matutino",
        
        # Help & Menu
        'help_msg': "🤖 **Comandos:**\n☀️ `mañana` (Salud)\n📋 `lista` (Historial)\n🔢 `0` (Último entreno)",
        'menu_title': "📋 **Últimas Actividades:**",
        'menu_footer': "👉 *Envía el número (0, 1...) para ver detalles.*",
        
        # Morning Report
        'morning_title': "🌅 **Reporte Matutino**",
        'sleep': "💤 **Sueño**",
        'duration': "⏱️ Duración",
        'body_batt': "🔋 **Body Battery**",
        'bb_max': "Carga máx",
        'bb_now': "Actual",
        'heart': "💓 **Corazón**",
        'rhr': "❤️ RHR (Reposo)",
        'hrv': "📉 VFC (HRV)",
        'readiness': "🚦 **Disposición**",
        'advice_go': "🚀 ¡A VOLAR! Estás a tope.",
        'advice_ok': "✅ Luz verde para entrenar.",
        'advice_warn': "⚠️ Baja la carga hoy.",
        'advice_stop': "🛑 Descansa, soldado.",
        
        # Activity Report
        'rep_title': "🏃 **REPORTE**",
        'sec_main': "⏱️ **PRINCIPALES**",
        'sec_cardio': "❤️ **CARDIO & CARGA**",
        'sec_eff': "⚡ **EFICIENCIA**",
        'sec_dyn': "👟 **DINÁMICAS**",
        'sec_splits': "📊 **SPLITS**",
        'lbl_dist': "Dist",
        'lbl_time': "Tiempo",
        'lbl_pace': "Ritmo",
        'lbl_gap': "GAP",
        'lbl_asc': "Asc",
        'lbl_load': "Carga",
        'lbl_zones': "*Zonas:*",
        'lbl_pow': "Potencia",
        'lbl_cal': "Cal",
        'lbl_cad': "Cad",
        'lbl_stride': "Zancada",
        'lbl_gct': "GCT",
        'lbl_osc': "Osc.V",
        'lbl_sens': "Sensación",
        'feel_map': {0: "Muy Débil", 25: "Débil", 50: "Normal", 75: "Fuerte", 100: "Muy Fuerte"}
    },
    'en': {
        # Status Messages
        'loading_1': "⏳ 1/3 Connecting...",
        'loading_2': "✅ 2/3 Downloading...",
        'loading_vital': "⏳ Fetching vital signs...",
        'loading_hist': "⏳ Fetching history...",
        'err_not_found': "❌ Activity not found.",
        'err_empty': "❌ Error: Empty activity.",
        'err_menu': "❌ Error fetching menu",
        'err_morning': "❌ Error fetching morning report",
        
        # Help & Menu
        'help_msg': "🤖 **Bot Commands:**\n☀️ `morning` (Health)\n📋 `list` (History)\n🔢 `0` (Latest activity)",
        'menu_title': "📋 **Recent Activities:**",
        'menu_footer': "👉 *Send the number (0, 1...) for details.*",
        
        # Morning Report
        'morning_title': "🌅 **Morning Report**",
        'sleep': "💤 **Sleep**",
        'duration': "⏱️ Duration",
        'body_batt': "🔋 **Body Battery**",
        'bb_max': "Max charge",
        'bb_now': "Current",
        'heart': "💓 **Heart**",
        'rhr': "❤️ RHR (Resting)",
        'hrv': "📉 HRV (Status)",
        'readiness': "🚦 **Readiness**",
        'advice_go': "🚀 FULL SEND! You are ready.",
        'advice_ok': "✅ Good to go.",
        'advice_warn': "⚠️ Take it easy today.",
        'advice_stop': "🛑 Rest day recommended.",
        
        # Activity Report
        'rep_title': "🏃 **REPORT**",
        'sec_main': "⏱️ **MAIN STATS**",
        'sec_cardio': "❤️ **CARDIO & LOAD**",
        'sec_eff': "⚡ **EFFICIENCY**",
        'sec_dyn': "👟 **DYNAMICS**",
        'sec_splits': "📊 **SPLITS**",
        'lbl_dist': "Dist",
        'lbl_time': "Time",
        'lbl_pace': "Pace",
        'lbl_gap': "GAP",
        'lbl_asc': "Asc",
        'lbl_load': "Load",
        'lbl_zones': "*Zones:*",
        'lbl_pow': "Power",
        'lbl_cal': "Cal",
        'lbl_cad': "Cad",
        'lbl_stride': "Stride",
        'lbl_gct': "GCT",
        'lbl_osc': "V.Osc",
        'lbl_sens': "Feeling",
        'feel_map': {0: "Very Weak", 25: "Weak", 50: "Normal", 75: "Strong", 100: "Very Strong"}
    }
}

# Select language based on Env Var (Fallback to Spanish)
# Seleccionar idioma basado en variable de entorno (Fallback a Español)
T = TRANS.get(LANG_CODE, TRANS['es'])


# ==============================================================================
# HELPER FUNCTIONS / FUNCIONES DE AYUDA
# ==============================================================================

def format_time(seconds):
    """Seconds to MM:SS or HH:MM:SS / Segundos a MM:SS"""
    if not seconds: return "00:00"
    m, s = divmod(int(seconds), 60)
    if m >= 60:
        h, m = divmod(m, 60)
        return f"{h}:{m:02}:{s:02}"
    return f"{m:02}:{s:02}"

def format_duration_hm(seconds):
    """Seconds to Xh Ym / Segundos a Xh Ym"""
    if not seconds: return "-"
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    return f"{h}h {m}m"

def format_pace(mps):
    """Meters/sec to Min/km / Metros/seg a Min/km"""
    if not mps or mps <= 0: return "-"
    seconds_per_km = 1000 / mps
    m, s = divmod(seconds_per_km, 60)
    return f"{int(m):02}:{int(s):02}"

def safe_round(val, decimals=0):
    """Safe rounding handling None/Strings / Redondeo seguro manejando Nulos"""
    try:
        if val is None or val == "N/A": return "-"
        f = float(val)
        if decimals == 0: return int(round(f))
        return round(f, decimals)
    except: return val

def get_ciq_by_id(data, target_app_id, target_field_num):
    """Extract ConnectIQ field by ID / Extraer campo ConnectIQ por ID"""
    ciq_list = data.get('connectIQMeasurements') or data.get('connectIQMeasurement', [])
    if not ciq_list: return None
    for item in ciq_list:
        app_id = str(item.get('appID', ''))
        field_num = item.get('developerFieldNumber')
        try:
            if app_id == target_app_id and int(field_num) == int(target_field_num):
                return float(item.get('value'))
        except: continue
    return None

def send_telegram(chat_id, text, use_markdown=True):
    """Send message to Telegram / Enviar mensaje a Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {'chat_id': chat_id, 'text': text}
    if use_markdown: payload['parse_mode'] = 'Markdown'
    try:
        response = requests.post(url, json=payload)
        response_data = response.json()
        if not response_data.get('ok'):
            error_desc = response_data.get('description', 'Unknown error')
            logging.error(f"⚠️ Telegram Error: {error_desc}")
            # Retry as plain text if Markdown fails / Reintentar como texto plano si falla Markdown
            if use_markdown and ("parse" in error_desc.lower() or "markdown" in error_desc.lower()):
                send_telegram(chat_id, text, use_markdown=False)
    except Exception as e: logging.error(f"Connection Error: {e}")


# ==============================================================================
# MORNING REPORT LOGIC / LÓGICA DE REPORTE MATUTINO
# ==============================================================================

def get_morning_report():
    try:
        garmin = Garmin(GARMIN_EMAIL, GARMIN_PASSWORD)
        garmin.login()
        today = date.today().isoformat()
        
        # 1. SLEEP / SUEÑO
        sleep_score, sleep_qual, sleep_secs = "-", "-", 0
        try:
            sleep_data = garmin.get_sleep_data(today)
            daily_sleep = sleep_data.get('dailySleepDTO', {})
            sleep_score = daily_sleep.get('sleepScores', {}).get('overall', {}).get('value', '-')
            # qualifierKey suele venir en inglés (GOOD, FAIR), lo dejamos o traducimos simple
            sleep_qual = daily_sleep.get('sleepScores', {}).get('overall', {}).get('qualifierKey', '').replace('_', ' ').title()
            sleep_secs = daily_sleep.get('sleepTimeSeconds', 0)
        except: pass
        
        # 2. BODY BATTERY
        bb_charged, bb_now = "-", "-"
        try:
            bb_data = garmin.get_body_battery(today)
            if bb_data:
                values = bb_data[0].get('bodyBatteryValuesArray', [])
                if values:
                    vals = [x[1] for x in values if x[1] is not None]
                    if vals: 
                        bb_charged = max(vals) # Max charge (Morning)
                        bb_now = vals[-1]      # Current charge
        except: pass

        # 3. RHR (Resting Heart Rate) / FRECUENCIA EN REPOSO
        rhr = "-"
        user_sum_data = None
        try:
            user_sum_data = garmin.get_user_summary(today)
            if 'restingHeartRate' in user_sum_data: rhr = user_sum_data['restingHeartRate']
        except: pass

        # 4. TRAINING READINESS / DISPOSICIÓN DE ENTRENAMIENTO
        # Aggressive Search / Búsqueda Agresiva
        readiness = "-"
        
        # Strategy A: Specific Endpoint / Estrategia A: Endpoint Específico
        try:
            r_data = garmin.get_training_readiness(today)
            if r_data:
                if 'score' in r_data: readiness = r_data['score']
                elif 'trainingReadinessDynamicDTO' in r_data:
                    readiness = r_data['trainingReadinessDynamicDTO'].get('score', '-')
        except: pass

        # Strategy B: User Summary (Backup) / Estrategia B: Resumen de Usuario
        if readiness == "-":
            try:
                # If we failed to get user_sum before, try now / Si fallamos antes, intentar ahora
                if not user_sum_data: user_sum_data = garmin.get_user_summary(today)
                if user_sum_data:
                    if 'trainingReadinessDynamicDTO' in user_sum_data:
                        readiness = user_sum_data['trainingReadinessDynamicDTO'].get('score', '-')
                    elif 'trainingReadiness' in user_sum_data:
                        readiness = user_sum_data['trainingReadiness']
            except: pass
            
        # 5. HRV / VFC
        hrv_status, hrv_avg = "-", "-"
        try:
            hrv_data = garmin.get_hrv_data(today) 
            if hrv_data and 'hrvSummary' in hrv_data:
                summary = hrv_data['hrvSummary']
                hrv_status = summary.get('status', '-').title()
                hrv_avg = summary.get('weeklyAvg', '-')
        except: pass

        # Build Message / Construir Mensaje
        msg = f"{T['morning_title']}: {today}\n\n"
        msg += f"{T['sleep']}: {sleep_score}/100 ({sleep_qual})\n"
        msg += f"   {T['duration']}: {format_duration_hm(sleep_secs)}\n\n"
        msg += f"{T['body_batt']}: {T['bb_max']}: {bb_charged} | {T['bb_now']}: {bb_now}\n"
        msg += f"{T['heart']}:\n   {T['rhr']}: {rhr} ppm\n   {T['hrv']}: {hrv_status} ({hrv_avg} ms)\n\n"
        msg += f"{T['readiness']}: {readiness}/100\n"
        
        # Advice Logic / Lógica de Consejo
        try:
            if readiness != "-":
                r_val = int(readiness)
                if r_val >= 85: msg += f"   {T['advice_go']}"
                elif r_val >= 65: msg += f"   {T['advice_ok']}"
                elif r_val >= 45: msg += f"   {T['advice_warn']}"
                else: msg += f"   {T['advice_stop']}"
        except: pass

        return msg
    except Exception as e: return f"{T['err_morning']}: {str(e)}"


# ==============================================================================
# ACTIVITY LOGIC / LÓGICA DE ACTIVIDADES
# ==============================================================================

def get_activity_menu():
    try:
        garmin = Garmin(GARMIN_EMAIL, GARMIN_PASSWORD)
        garmin.login()
        activities = garmin.get_activities(0, 5)
        if not activities: return T['err_not_found']
        
        msg = f"{T['menu_title']}\n\n"
        for i, act in enumerate(activities):
            start = act.get("startTimeLocal", "")[:16].replace("T", " ")
            name = act.get("activityName", "Sin nombre")
            type_key = act.get("activityType", {}).get("typeKey", "activity")
            dist_km = act.get("distance", 0) / 1000
            msg += f"`{i}` - *{start}*\n   🏃 {type_key} | 📏 {dist_km:.2f} km\n   📝 {name}\n\n"
        
        msg += f"\n{T['menu_footer']}"
        return msg
    except Exception as e: return f"{T['err_menu']}: {str(e)}"

def process_report(data, zones_raw, splits_raw):
    s = data.get('summaryDTO', {})
    total_duration = s.get("duration", 0)
    
    # Location & Elevation / Ubicación y Elevación
    location = data.get("locationName", "-")
    min_elev = safe_round(s.get("minElevation"), 0)
    max_elev = safe_round(s.get("maxElevation"), 0)
    loc_str = f"{location} ({max_elev} m)" if min_elev != "-" else location

    # Global Metrics / Métricas Globales
    metrics = {
        "fecha": s.get("startTimeLocal", "").replace("T", " "),
        "lugar_completo": loc_str,
        "tipo": data.get("activityTypeDTO", {}).get("typeKey"),
        "distancia": safe_round(s.get("distance", 0), 2),
        "duracion": s.get("duration", 0),
        "ritmo_ms": s.get("averageSpeed"),
        "vel_kmh": safe_round(s.get("averageSpeed", 0) * 3.6, 2),
        "fc_avg": safe_round(s.get("averageHR", "N/A"), 0),
        "fc_max": safe_round(s.get("maxHR", "N/A"), 0),
        "te_aer": safe_round(s.get("trainingEffect", "N/A"), 1),
        "te_ana": safe_round(s.get("anaerobicTrainingEffect", 0.0), 1),
        "carga": safe_round(s.get("activityTrainingLoad", "N/A"), 0),
        "calorias": safe_round(s.get("calories", "N/A"), 0),
        "cadencia": safe_round(s.get("averageRunCadence", "N/A"), 0),
        "cadencia_max": safe_round(s.get("maxRunCadence", "N/A"), 0),
        "zancada": safe_round(s.get("strideLength", "N/A"), 0),
        "ratio_v": safe_round(s.get("verticalRatio", "N/A"), 1),
        "osc_v": safe_round(s.get("verticalOscillation", "N/A"), 1),
        "gct": safe_round(s.get("groundContactTime", "N/A"), 0),
        "potencia": safe_round(s.get("averagePower", "N/A"), 0),
        "ascenso": safe_round(s.get("elevationGain", 0), 0),
        "gap_ms": s.get("avgGradeAdjustedSpeed")
    }
    
    # RPE & Feeling (Localized) / Sensación (Localizada)
    rpe_raw = s.get("directWorkoutRpe")
    metrics['rpe'] = safe_round(rpe_raw / 10, 0) if rpe_raw else "__"
    feel_raw = s.get("directWorkoutFeel")
    
    feel_map = T['feel_map']
    if feel_raw is not None:
        metrics['feeling'] = feel_map[min(feel_map.keys(), key=lambda k: abs(k-feel_raw))]
    else:
        metrics['feeling'] = "-"
    
    # EF Global
    ciq_ef = get_ciq_by_id(data, EF_APP_ID, EF_FIELD_NUM_GLOBAL)
    metrics['ef'] = f"{ciq_ef:.2f}" if ciq_ef else "-"
    
    # Zones / Zonas
    zones_list = []
    if zones_raw:
        zones_sorted = sorted(zones_raw, key=lambda x: x['zoneNumber'])
        for i, z in enumerate(zones_sorted):
            z_num = z.get('zoneNumber')
            secs = z.get('secsInZone', 0)
            low_bound = int(z.get('zoneLowBoundary', 0))
            if i < len(zones_sorted) - 1:
                next_low = int(zones_sorted[i+1].get('zoneLowBoundary', 0))
                range_str = f"{low_bound}-{next_low - 1} ppm"
            else: range_str = f">{low_bound} ppm"
            if secs > 0:
                pct = (secs / metrics['duracion']) * 100 if metrics['duracion'] > 0 else 0
                zones_list.append(f"  * Z{z_num} ({range_str}): {pct:.0f}% ({format_time(secs)})")
    metrics['zonas_txt'] = "\n".join(zones_list) if zones_list else "---"
    
    # Splits Processing / Procesamiento de Vueltas
    clean_laps = []
    source_list = []
    # Logic: Prioritize /splits/lapDTOs -> data['laps'] -> data['splitSummaries']
    if splits_raw and 'lapDTOs' in splits_raw and len(splits_raw['lapDTOs']) > 0:
        source_list = splits_raw['lapDTOs']
    elif 'laps' in data and len(data['laps']) > 0:
        source_list = data['laps']
    else: source_list = data.get('splitSummaries', [])
    
    for i, split in enumerate(source_list):
        dist = split.get("distance", 0)
        dur = split.get("duration", 0)
        if dist < 10 and dur < 10: continue
        if "splitSummaries" in str(source_list) and len(source_list) > 1:
            if abs(dur - total_duration) < 2.0: continue
        
        clean_laps.append({
            "nr": len(clean_laps) + 1,
            "dist": dist,
            "ritmo": format_pace(split.get("averageSpeed")),
            "gap": format_pace(split.get("avgGradeAdjustedSpeed")),
            "fc": safe_round(split.get("averageHR", "-"), 0),
            "cad": safe_round(split.get("averageRunCadence", "N/A"), 0),
            "gct": safe_round(split.get("groundContactTime", "N/A"), 0),
            "ef": f"{get_ciq_by_id(split, EF_APP_ID, EF_FIELD_NUM_LAP):.2f}" if get_ciq_by_id(split, EF_APP_ID, EF_FIELD_NUM_LAP) else "-"
        })
    metrics['laps'] = clean_laps
    return metrics

def generate_markdown(m):
    # Cabeceras de tabla traducidas (compactas)
    laps_table = "```\n"
    laps_table += f"| #  | km   | {T['lbl_pace']} | {T['lbl_gap']}   | FC  | {T['lbl_cad']} | {T['lbl_gct']} | EF  |\n"
    laps_table += "|----|------|-------|-------|-----|-----|-----|-----|\n"
    
    for l in m['laps']:
        nr = str(l['nr']).rjust(2)
        dist = f"{(l['dist']/1000):.2f}".rjust(4)
        ritmo = str(l['ritmo']).center(5)
        gap = str(l['gap']).center(5)
        fc = str(l['fc']).rjust(3)
        cad = str(l['cad']).rjust(3)
        gct = str(l['gct']).rjust(3)
        ef = str(l['ef']).rjust(4)
        
        laps_table += f"| {nr} | {dist} | {ritmo} | {gap} | {fc} | {cad} | {gct} | {ef} |\n"
    
    laps_table += "```"
    
    return f"""
# {T['rep_title']}: *{m['tipo'].upper()}*
📅 {m['fecha']}
📍 {m['lugar_completo']}

{T['sec_main']}
{T['lbl_dist']}: `{m['distancia']} m` | {T['lbl_time']}: `{format_time(m['duracion'])}`
{T['lbl_pace']}: `{format_pace(m['ritmo_ms'])}/km` | {T['lbl_gap']}: `{format_pace(m['gap_ms'])}/km`
Vel: `{m['vel_kmh']} km/h` | {T['lbl_asc']}: `{m['ascenso']} m`

{T['sec_cardio']}
FC Avg: `{m['fc_avg']} ppm` | Max: `{m['fc_max']} ppm`
{T['lbl_load']}: `{m['carga']}` | TE: `{m['te_aer']}` / `{m['te_ana']}`

{T['sec_splits']}
{m['zonas_txt']}

{T['sec_eff']} & {T['sec_dyn']}
EF: `{m['ef']}` | {T['lbl_pow']}: `{m['potencia']} W` | {T['lbl_cal']}: `{m['calorias']}`
{T['lbl_cad']}: `{m['cadencia']}` | {T['lbl_stride']}: `{m['zancada']} cm`
{T['lbl_gct']}: `{m['gct']} ms` | {T['lbl_osc']}: `{m['osc_v']} cm` (`{m['ratio_v']}%`)

{laps_table}

RPE: {m['rpe']}/10 | {T['lbl_sens']}: {m['feeling']}
    """

# ==============================================================================
# ENTRY POINT / PUNTO DE ENTRADA (WEBHOOK)
# ==============================================================================

def telegram_webhook(request):
    """
    Main entry point for Google Cloud Functions.
    Handles Telegram Webhooks and Siri/Shortcut GET requests.
    """
    
    # --- SIRI / SHORTCUTS HANDLER ---
    siri_mode = request.args.get('siri') or request.args.get('source') == 'siri'
    command_arg = request.args.get('command')
    headers = {'Content-Type': 'text/plain; charset=utf-8'}

    if siri_mode and command_arg:
        text = command_arg.strip().lower()
        try:
            # Comandos bilingües
            if text in ['mañana', 'morning', 'reporte', 'dia', 'report']:
                return get_morning_report(), 200, headers
            elif text in ['menu', 'lista', 'historial', 'list', 'history']:
                return get_activity_menu(), 200, headers
            else:
                try:
                    idx = int(text)
                    # Login again for Siri thread
                    garmin = Garmin(GARMIN_EMAIL, GARMIN_PASSWORD)
                    garmin.login()
                    activities = garmin.get_activities(idx, 1)
                    if not activities: return T['err_not_found'], 200, headers
                    act_id = activities[0]['activityId']
                    details = garmin.get_activity(act_id)
                    try: zones = garmin.connectapi(f"/activity-service/activity/{act_id}/hrTimeInZones")
                    except: zones = []
                    try: splits = garmin.connectapi(f"/activity-service/activity/{act_id}/splits")
                    except: splits = {}
                    if details:
                        metrics = process_report(details, zones, splits)
                        return generate_markdown(metrics), 200, headers
                    return T['err_empty'], 200, headers
                except: return "Command not found", 200, headers
        except Exception as e: return f"Siri Error: {str(e)}", 500, headers

    # --- TELEGRAM HANDLER ---
    req = request.get_json(silent=True)
    if not req or 'message' not in req: return 'OK', 200

    chat_id = req['message']['chat']['id']
    text = req['message'].get('text', '').strip().lower()

    # Commands / Comandos
    if text in ['mañana', 'morning', 'buenos dias', 'reporte', 'report']:
        send_telegram(chat_id, T['loading_vital'], use_markdown=False)
        send_telegram(chat_id, get_morning_report())
        return 'OK', 200

    if text in ['menu', 'lista', 'historial', 'list', 'history']:
        send_telegram(chat_id, T['loading_hist'], use_markdown=False)
        send_telegram(chat_id, get_activity_menu())
        return 'OK', 200

    # Activity by Index / Actividad por Índice
    try:
        activity_index = int(text)
        send_telegram(chat_id, T['loading_1'], use_markdown=False)
        try:
            garmin = Garmin(GARMIN_EMAIL, GARMIN_PASSWORD)
            garmin.login()
            send_telegram(chat_id, T['loading_2'], use_markdown=False)

            activities = garmin.get_activities(activity_index, 1)
            if not activities:
                send_telegram(chat_id, T['err_not_found'], use_markdown=False)
                return 'OK', 200
            
            act_id = activities[0]['activityId']
            details = garmin.get_activity(act_id)
            try: zones = garmin.connectapi(f"/activity-service/activity/{act_id}/hrTimeInZones")
            except: zones = []
            try: splits = garmin.connectapi(f"/activity-service/activity/{act_id}/splits")
            except: splits = {}

            if details:
                metrics = process_report(details, zones, splits)
                report = generate_markdown(metrics)
                send_telegram(chat_id, report)
            else:
                send_telegram(chat_id, T['err_empty'], use_markdown=False)
        except Exception as e:
            error_trace = traceback.format_exc()
            logging.error(f"ERROR: {error_trace}")
            send_telegram(chat_id, f"🔥 Error: {str(e)}", use_markdown=False)
            
    except ValueError:
        send_telegram(chat_id, T['help_msg'])

    return 'OK', 200