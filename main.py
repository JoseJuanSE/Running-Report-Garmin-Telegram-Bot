import os
import json
import logging
import requests
import traceback
from garminconnect import Garmin

# --- HACK PARA CLOUD RUN ---
os.environ['HOME'] = '/tmp'

# --- CONFIGURACIÓN ---
GARMIN_EMAIL = os.environ.get('GARMIN_EMAIL')
GARMIN_PASSWORD = os.environ.get('GARMIN_PASSWORD')
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')

# Configuración EF
EF_APP_ID = "e9f83886-2e1d-448e-aa0a-0cdfb9160df9"
EF_FIELD_NUM_GLOBAL = 2
EF_FIELD_NUM_LAP = 1

FEELING_MAP = {0: "Muy Débil", 25: "Débil", 50: "Normal", 75: "Fuerte", 100: "Muy Fuerte"}

# --- HELPER FUNCTIONS ---
def format_time(seconds):
    if not seconds: return "00:00"
    m, s = divmod(int(seconds), 60)
    if m >= 60:
        h, m = divmod(m, 60)
        return f"{h}:{m:02}:{s:02}"
    return f"{m:02}:{s:02}"

def format_pace(mps):
    if not mps or mps <= 0: return "-"
    seconds_per_km = 1000 / mps
    m, s = divmod(seconds_per_km, 60)
    return f"{int(m):02}:{int(s):02}"

def safe_round(val, decimals=0):
    try:
        if val is None or val == "N/A": return "-"
        f = float(val)
        if decimals == 0: return int(round(f))
        return round(f, decimals)
    except:
        return val

def get_ciq_by_id(data, target_app_id, target_field_num):
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
    """Envia mensaje a Telegram con reintento en Texto Plano si falla el Markdown"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    
    payload = {
        'chat_id': chat_id,
        'text': text
    }
    if use_markdown:
        payload['parse_mode'] = 'Markdown' # Usamos Markdown V1 (menos estricto que V2)

    try:
        response = requests.post(url, json=payload)
        response_data = response.json()
        
        if not response_data.get('ok'):
            error_desc = response_data.get('description', 'Unknown error')
            logging.error(f"⚠️ Telegram rechazó el mensaje: {error_desc}")
            
            # Si falló por formato, reintentar como texto plano
            if use_markdown and ("parse" in error_desc.lower() or "markdown" in error_desc.lower()):
                logging.info("🔄 Reintentando envío como Texto Plano...")
                send_telegram(chat_id, text, use_markdown=False)
            else:
                # Si falla por otra cosa (ej. mensaje muy largo), avisar
                if "too long" in error_desc.lower():
                     requests.post(url, json={'chat_id': chat_id, 'text': "❌ Error: El reporte es demasiado largo para Telegram."})
    except Exception as e:
        logging.error(f"Error de conexión con Telegram: {e}")

# --- LÓGICA CORE ---
def process_report(data, zones_raw, splits_raw):
    s = data.get('summaryDTO', {})
    total_duration = s.get("duration", 0)

    # Ubicación
    location = data.get("locationName", "Ubicación desconocida")
    min_elev = safe_round(s.get("minElevation"), 0)
    max_elev = safe_round(s.get("maxElevation"), 0)
    if min_elev != "-" and max_elev != "-":
        loc_str = f"{location} ({max_elev} m)" if abs(max_elev - min_elev) < 5 else f"{location} ({min_elev}-{max_elev} m)"
    else:
        loc_str = location

    # Métricas Globales
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

    # RPE & Feeling
    rpe_raw = s.get("directWorkoutRpe")
    metrics['rpe'] = safe_round(rpe_raw / 10, 0) if rpe_raw else "__"
    feel_raw = s.get("directWorkoutFeel")
    metrics['feeling'] = FEELING_MAP[min(FEELING_MAP.keys(), key=lambda k: abs(k-feel_raw))] if feel_raw is not None else "Normal"

    # EF Global
    ciq_ef = get_ciq_by_id(data, EF_APP_ID, EF_FIELD_NUM_GLOBAL)
    metrics['ef'] = f"{ciq_ef:.2f}" if ciq_ef else "-"

    # Zonas
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
            else:
                range_str = f">{low_bound} ppm"

            if secs > 0:
                pct = (secs / metrics['duracion']) * 100 if metrics['duracion'] > 0 else 0
                zones_list.append(f"  * Z{z_num} ({range_str}): {pct:.0f}% ({format_time(secs)})")
    metrics['zonas_txt'] = "\n".join(zones_list) if zones_list else "Sin datos de zonas."

    # Vueltas
    clean_laps = []
    source_list = []
    if splits_raw and 'lapDTOs' in splits_raw and len(splits_raw['lapDTOs']) > 0:
        source_list = splits_raw['lapDTOs']
    elif 'laps' in data and len(data['laps']) > 0:
        source_list = data['laps']
    else:
        source_list = data.get('splitSummaries', [])

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
            "ritmo_max": format_pace(split.get("maxSpeed")),
            "fc": safe_round(split.get("averageHR", "-"), 0),
            "fc_max": safe_round(split.get("maxHR", "-"), 0),
            "cad": safe_round(split.get("averageRunCadence", "N/A"), 0),
            "gct": safe_round(split.get("groundContactTime", "N/A"), 0),
            "vr": safe_round(split.get("verticalRatio", "N/A"), 1),
            "ascenso": safe_round(split.get("elevationGain", 0), 0),
            "gap": format_pace(split.get("avgGradeAdjustedSpeed")),
            "ef": f"{get_ciq_by_id(split, EF_APP_ID, EF_FIELD_NUM_LAP):.2f}" if get_ciq_by_id(split, EF_APP_ID, EF_FIELD_NUM_LAP) else "-"
        })
    metrics['laps'] = clean_laps
    return metrics

def generate_markdown(m):
    laps_table = ""
    # Header compacto para movil
    laps_table += "| # | km | Rit | GAP | FC | Cad | GCT | EF |\n"
    laps_table += "|---|---|---|---|---|---|---|---|\n"
    
    for l in m['laps']:
        laps_table += f"| {l['nr']} | {(l['dist']/1000):.2f} | {l['ritmo']} | {l['gap']} | {l['fc']} | {l['cad']} | {l['gct']} | {l['ef']} |\n"
    
    return f"""
# 🏃 Reporte: {m['tipo']}
📅 {m['fecha']}
📍 {m['lugar_completo']}

⏱️ *PRINCIPALES*
Dist: {m['distancia']} m | Tiempo: {format_time(m['duracion'])}
Ritmo: {format_pace(m['ritmo_ms'])}/km | GAP: {format_pace(m['gap_ms'])}/km
Vel: {m['vel_kmh']} km/h | Asc: {m['ascenso']} m

❤️ *CARDIO & CARGA*
FC Avg/Max: {m['fc_avg']} / {m['fc_max']} ppm
TE: {m['te_aer']} / {m['te_ana']} | Carga: {m['carga']}
*Zonas:*
{m['zonas_txt']}

⚡ *EFICIENCIA*
EF: {m['ef']} | Potencia: {m['potencia']} W | Cal: {m['calorias']}

👟 *DINÁMICAS*
Cad: {m['cadencia']} | Zancada: {m['zancada']} cm
GCT: {m['gct']} ms | Osc.V: {m['osc_v']} cm ({m['ratio_v']}%)

📊 *SPLITS*
{laps_table}

RPE: {m['rpe']}/10 | Sensación: {m['feeling']}
    """

# --- ENTRY POINT ---
def telegram_webhook(request):
    req = request.get_json()
    if not req or 'message' not in req:
        return 'OK', 200

    chat_id = req['message']['chat']['id']
    text = req['message'].get('text', '').strip()

    try:
        activity_index = int(text)
    except ValueError:
        return 'OK', 200 

    # 1. AVISO DE INICIO
    logging.info("Iniciando proceso...")
    send_telegram(chat_id, "⏳ 1/3 Conectando a Garmin...", use_markdown=False)

    try:
        # --- LOGIN ---
        garmin = Garmin(GARMIN_EMAIL, GARMIN_PASSWORD)
        garmin.login()
        logging.info("Login exitoso")
        send_telegram(chat_id, "✅ 2/3 Descargando actividad...", use_markdown=False)

        # --- DESCARGA ---
        activities = garmin.get_activities(activity_index, 1)
        if not activities:
            send_telegram(chat_id, "❌ No se encontró actividad.", use_markdown=False)
            return 'OK', 200
        
        last = activities[0]
        act_id = last['activityId']
        logging.info(f"Procesando actividad ID: {act_id}")
        
        details = garmin.get_activity(act_id)
        
        try: zones = garmin.connectapi(f"/activity-service/activity/{act_id}/hrTimeInZones")
        except: zones = []
        try: splits = garmin.connectapi(f"/activity-service/activity/{act_id}/splits")
        except: splits = {}

        # --- PROCESAMIENTO ---
        if details:
            metrics = process_report(details, zones, splits)
            report = generate_markdown(metrics)
            
            logging.info("Enviando reporte final...")
            # Aquí es donde fallaba antes, ahora tenemos reintento automático
            send_telegram(chat_id, report)
        else:
            send_telegram(chat_id, "❌ Error: Actividad sin detalles.", use_markdown=False)
            
    except Exception as e:
        error_trace = traceback.format_exc()
        logging.error(f"FATAL ERROR: {error_trace}")
        send_telegram(chat_id, f"🔥 Error Crítico: {str(e)}", use_markdown=False)

    return 'OK', 200