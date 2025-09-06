import json
import logging
import re
import sys
from ipaddress import ip_address

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

# Optional dependency handling for SoCo
try:
    from soco import SoCo
except Exception as e:
    SoCo = None

CONFIG_FILE_PATH = "/app/config/config.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# --- Load config ---
try:
    with open(CONFIG_FILE_PATH) as f:
        config = json.load(f)
    SLACK_BOT_TOKEN = config["SLACK_BOT_TOKEN"]
    SLACK_APP_TOKEN = config["SLACK_APP_TOKEN"]
    SONOS_IP = config.get("SonosIP")
    if not SONOS_IP:
        raise KeyError("SonosIP saknas i config.json")
    # Validate IP
    ip_address(SONOS_IP)
    logger.info("Konfiguration laddad.")
except FileNotFoundError:
    logger.error(f"Kunde inte hitta '{CONFIG_FILE_PATH}'. Se till att filen är korrekt monterad i containern.")
    sys.exit(1)
except KeyError as e:
    logger.error(f"Saknar fält i konfigurationen: {e}")
    sys.exit(1)
except ValueError:
    logger.error("SonosIP i config.json är inte en giltig IPv4-adress.")
    sys.exit(1)

# --- Slack app ---
app = App(token=SLACK_BOT_TOKEN)
logger.info("Slack App initierad.")

# --- Sonos helpers ---
def get_sonos():
    if SoCo is None:
        raise RuntimeError("SoCo är inte installerat. Kör 'pip install soco'.")
    return SoCo(SONOS_IP)

def sonos_play():
    dev = get_sonos()
    dev.play()
    return dev.player_name

def sonos_pause():
    dev = get_sonos()
    dev.pause()
    return dev.player_name

# --- Listeners ---

# Reply to mentions (kept for visibility)
@app.event("app_mention")
def handle_app_mention_events(body, say, logger=logger):
    user = body.get("event", {}).get("user")
    text = body.get("event", {}).get("text")
    channel = body.get("event", {}).get("channel")
    logger.info(f"Mention i kanal {channel} från användare {user}: {text}")
    say(f"Hej <@{user}>, jag hörde din mention!")

# Exact "hello"
@app.message(re.compile(r"^\s*hello\s*$", re.I))
def say_hello(message, say, logger=logger):
    user_id = message.get("user")
    say(f"Hello there! <@{user_id}>")
    logger.info(f"Svarade 'Hello there!' till {user_id}")

# === PLAY ===
@app.message(re.compile(r"^\s*play\s*$", re.I))
def handle_play(message, say, logger=logger):
    try:
        player = sonos_play()
        say(f"▶️ Spelar på **{player}**.")
        logger.info("Skickade play till Sonos.")
    except Exception as e:
        logger.error(f"Fel vid play: {e}")
        say(f"❌ Kunde inte starta uppspelning: {e}")

# === STOP (pause) ===
@app.message(re.compile(r"^\s*stop\s*$", re.I))
def handle_stop(message, say, logger=logger):
    try:
        player = sonos_pause()
        say(f"⏸️ Pausade på **{player}**.")
        logger.info("Skickade stop (pause) till Sonos.")
    except Exception as e:
        logger.error(f"Fel vid stop: {e}")
        say(f"❌ Kunde inte stoppa uppspelning: {e}")

# === SET VOLUME N (0–100) ===
@app.message(re.compile(r"^\s*set volume\s+(\d{1,3})\s*$", re.I))
def handle_set_volume(message, say, context, logger=logger):
    try:
        vol = int(context['matches'][0])
        if not 0 <= vol <= 100:
            say("❌ Volymen måste vara mellan 0 och 100.")
            return
        dev = get_sonos()
        dev.volume = vol
        say(f"🔊 Satt volymen på **{dev.player_name}** till {vol}.")
        logger.info(f"Volym satt till {vol} på {dev.player_name}.")
    except Exception as e:
        logger.error(f"Fel vid set volume: {e}")
        say(f"❌ Kunde inte sätta volym: {e}")



# Optional: log everything (quiet—no auto-replies)
@app.event("message")
def log_all_messages(body, logger=logger):
    event = body.get("event", {})
    if not event.get("bot_id"):
        logger.info(f"[ALL MSG] Kanal: {event.get('channel')}, "
                    f"Användare: {event.get('user')}, Text: {event.get('text')}")

# --- Start app ---
if __name__ == "__main__":
    try:
        handler = SocketModeHandler(app, SLACK_APP_TOKEN)
        logger.info("Botten startar... Väntar på meddelanden...")
        handler.start()
    except Exception as e:
        logger.error(f"Ett fel inträffade vid start av botten: {e}")
        sys.exit(1)
