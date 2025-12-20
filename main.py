import os
import json
import logging
import requests
import traceback
from datetime import date
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

def format_duration_hm(seconds):
    if not seconds: return "-"
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    return f"{h}h {m}m"

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
    except: return val

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
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {'chat_id': chat_id, 'text': text}
    if use_markdown: payload['parse_mode'] = 'Markdown'
    try:
        response = requests.post(url, json=payload)
        response_data = response.json()
        if not response_data.get('ok'):
            error_desc = response_data.get('description', 'Unknown error')
            logging.error(f"⚠️ Telegram rechazó mensaje: {error_desc}")
            if use_markdown and ("parse" in error_desc.lower() or "markdown" in error_desc.lower()):
                send_telegram(chat_id, text, use_markdown=False)
    except Exception as e: logging.error(f"Error Telegram: {e}")

# --- REPORTE MATUTINO MEJORADO ---
def get_morning_report():
    try:
        garmin = Garmin(GARMIN_EMAIL, GARMIN_PASSWORD)
        garmin.login()
        today = date.today().isoformat()
        
        # 1. SUEÑO
        sleep_score, sleep_qual, sleep_secs = "-", "-", 0
        try:
            sleep_data = garmin.get_sleep_data(today)
            daily_sleep = sleep_data.get('dailySleepDTO', {})
            sleep_score = daily_sleep.get('sleepScores', {}).get('overall', {}).get('value', '-')
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
                         bb_charged = max(vals)
                         bb_now = vals[-1]
        except: pass

        # 3. RHR (CORAZÓN EN REPOSO)
        rhr = "-"
        try:
            user_sum = garmin.get_user_summary(today)
            if 'restingHeartRate' in user_sum: rhr = user_sum['restingHeartRate']
        except: pass

        # 4. READINESS (BÚSQUEDA PROFUNDA)
        readiness = "-"
        # Intento A: Endpoint directo (Estructura variable)
        try:
            r_data = garmin.get_training_readiness(today)
            if r_data:
                # A veces viene directo {'score': 90}
                if 'score' in r_data: readiness = r_data['score']
                # A veces anidado {'trainingReadinessDynamicDTO': {'score': 90}}
                elif 'trainingReadinessDynamicDTO' in r_data:
                    readiness = r_data['trainingReadinessDynamicDTO'].get('score', '-')
        except: pass

        # Intento B: User Summary (Backup si el endpoint falla)
        if readiness == "-":
            try:
                if 'user_sum' not in locals(): user_sum = garmin.get_user_summary(today)
                if 'trainingReadinessDynamicDTO' in user_sum:
                     readiness = user_sum['trainingReadinessDynamicDTO'].get('score', '-')
                elif 'trainingReadiness' in user_sum:
                     readiness = user_sum['trainingReadiness']
            except: pass

        # 5. HRV
        hrv_status, hrv_avg = "-", "-"
        try:
            hrv_data = garmin.get_hrv_data(today) 
            if hrv_data and 'hrvSummary' in hrv_data:
                summary = hrv_data['hrvSummary']
                hrv_status = summary.get('status', '-').title()
                hrv_avg = summary.get('weeklyAvg', '-')
        except: pass

        msg = f"🌅 **Reporte Matutino: {today}**\n\n"
        msg += f"💤 **Sueño:** {sleep_score}/100 ({sleep_qual})\n"
        msg += f"   ⏱️ Duración: {format_duration_hm(sleep_secs)}\n\n"
        msg += f"🔋 **Body Battery:** Carga máx: {bb_charged} | Actual: {bb_now}\n"
        msg += f"💓 **Corazón:**\n   ❤️ RHR: {rhr} ppm\n   📉 VFC: {hrv_status} ({hrv_avg} ms)\n\n"
        msg += f"🚦 **Disposición (Readiness):** {readiness}/100\n"
        
        try:
            r_val = int(readiness)
            if r_val >= 85: msg += "   🚀 ¡A VOLAR! Estás a tope."
            elif r_val >= 65: msg += "   ✅ Luz verde para entrenar."
            elif r_val >= 45: msg += "   ⚠️ Baja la carga hoy."
            else: msg += "   🛑 Descansa, soldado."
        except: 
            msg += "   (Sincroniza tu reloj para ver el dato)"

        return msg
    except Exception as e: return f"❌ Error: {str(e)}"

# --- LÓGICA DE CARRERAS ---
def get_activity_menu():
    try:
        garmin = Garmin(GARMIN_EMAIL, GARMIN_PASSWORD)
        garmin.login()
        activities = garmin.get_activities(0, 5)
        if not activities: return "❌ No encontré actividades."
        msg = "📋 **Últimas Actividades:**\n\n"
        for i, act in enumerate(activities):
            start = act.get("startTimeLocal", "")[:16].replace("T", " ")
            name = act.get("activityName", "Sin nombre")
            type_key = act.get("activityType", {}).get("typeKey", "activity")
            dist_km = act.get("distance", 0) / 1000
            msg += f"`{i}` - *{start}*\n   🏃 {type_key} | 📏 {dist_km:.2f} km\n   📝 {name}\n\n"
        msg += "👉 *Envía el número (0, 1...) para ver detalles.*"
        return msg
    except Exception as e: return f"❌ Error menú: {str(e)}"

def process_report(data, zones_raw, splits_raw):
    s = data.get('summaryDTO', {})
    total_duration = s.get("duration", 0)
    location = data.get("locationName", "Ubicación desconocida")
    min_elev = safe_round(s.get("minElevation"), 0)
    max_elev = safe_round(s.get("maxElevation"), 0)
    loc_str = f"{location} ({max_elev} m)" if min_elev != "-" else location

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
    rpe_raw = s.get("directWorkoutRpe")
    metrics['rpe'] = safe_round(rpe_raw / 10, 0) if rpe_raw else "__"
    feel_raw = s.get("directWorkoutFeel")
    metrics['feeling'] = FEELING_MAP[min(FEELING_MAP.keys(), key=lambda k: abs(k-feel_raw))] if feel_raw is not None else "Normal"
    ciq_ef = get_ciq_by_id(data, EF_APP_ID, EF_FIELD_NUM_GLOBAL)
    metrics['ef'] = f"{ciq_ef:.2f}" if ciq_ef else "-"
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
    metrics['zonas_txt'] = "\n".join(zones_list) if zones_list else "Sin datos de zonas."
    clean_laps = []
    source_list = []
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
    laps_table = "| # | km | Rit | GAP | FC | Cad | GCT | EF |\n|---|---|---|---|---|---|---|---|\n"
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
    if not req or 'message' not in req: return 'OK', 200
    chat_id = req['message']['chat']['id']
    text = req['message'].get('text', '').strip().lower()
    
    # --- MODO DETECTIVE (DEBUG) ---
    if text == 'debug':
        send_telegram(chat_id, "🕵️‍♂️ Iniciando diagnóstico...", use_markdown=False)
        try:
            garmin = Garmin(GARMIN_EMAIL, GARMIN_PASSWORD)
            garmin.login()
            today = date.today().isoformat()
            
            # 1. Investigar Training Readiness (Endpoint Específico)
            try:
                raw_readiness = garmin.get_training_readiness(today)
                logging.info(f"DEBUG READINESS RAW: {raw_readiness}") # Esto va a los logs de Google
                send_telegram(chat_id, f"🔍 Readiness Endpoint:\n{str(raw_readiness)[:1000]}", use_markdown=False)
            except Exception as e:
                send_telegram(chat_id, f"❌ Falló Readiness Endpoint: {str(e)}", use_markdown=False)

            # 2. Investigar User Summary (Donde a veces se esconde)
            try:
                raw_summary = garmin.get_user_summary(today)
                logging.info(f"DEBUG SUMMARY RAW: {raw_summary}") # Esto va a los logs
                
                # Buscamos pistas clave en el resumen
                keys_found = [k for k in raw_summary.keys() if 'readiness' in k.lower() or 'score' in k.lower()]
                send_telegram(chat_id, f"🔍 Claves sospechosas en Summary:\n{keys_found}", use_markdown=False)
                
                # Ver valor exacto si existe
                val = raw_summary.get('trainingReadiness')
                send_telegram(chat_id, f"🔍 Valor 'trainingReadiness' en Summary: {val}", use_markdown=False)
                
            except Exception as e:
                send_telegram(chat_id, f"❌ Falló Summary Endpoint: {str(e)}", use_markdown=False)

        except Exception as e:
            send_telegram(chat_id, f"🔥 Error General Debug: {str(e)}", use_markdown=False)
        
        return 'OK', 200

    if text in ['mañana', 'buenos dias', 'morning', 'reporte', 'dia']:
        send_telegram(chat_id, "⏳ Obteniendo signos vitales...", use_markdown=False)
        msg = get_morning_report()
        send_telegram(chat_id, msg)
        return 'OK', 200

    if text in ['menu', 'lista', 'historial']:
        send_telegram(chat_id, "⏳ Consultando historial...", use_markdown=False)
        msg = get_activity_menu()
        send_telegram(chat_id, msg)
        return 'OK', 200

    try:
        idx = int(text)
        send_telegram(chat_id, "⏳ 1/3 Conectando...", use_markdown=False)
        garmin = Garmin(GARMIN_EMAIL, GARMIN_PASSWORD)
        garmin.login()
        send_telegram(chat_id, "✅ 2/3 Descargando...", use_markdown=False)
        
        acts = garmin.get_activities(idx, 1)
        if not acts:
            send_telegram(chat_id, "❌ No encontré esa actividad.")
            return 'OK', 200
            
        aid = acts[0]['activityId']
        details = garmin.get_activity(aid)
        try: zones = garmin.connectapi(f"/activity-service/activity/{aid}/hrTimeInZones")
        except: zones = []
        try: splits = garmin.connectapi(f"/activity-service/activity/{aid}/splits")
        except: splits = {}
        
        if details:
            m = process_report(details, zones, splits)
            rep = generate_markdown(m)
            send_telegram(chat_id, rep)
        else: send_telegram(chat_id, "❌ Actividad vacía.")
            
    except ValueError:
        help_msg = "🤖 *Comandos:*\n☀️ `mañana` (Salud)\n📋 `lista` (Historial)\n🔢 `0` (Último entreno)"
        send_telegram(chat_id, help_msg)
    except Exception as e:
        logging.error(f"FATAL: {traceback.format_exc()}")
        send_telegram(chat_id, f"🔥 Error: {str(e)}", use_markdown=False)

    return 'OK', 200