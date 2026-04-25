"""Constants for Soehnle Airfresh Clean Connect 500."""

DOMAIN = "soehnle_ac500"

# ── Service ffa0 – main control / sensor notifications ───────────────────────
UUID_WRITE = "0000EF01-0000-1000-8000-00805F9B34FB"
UUID_EF02  = "0000EF02-0000-1000-8000-00805F9B34FB"
UUID_EF03  = "0000EF03-0000-1000-8000-00805F9B34FB"
UUID_EF04  = "0000EF04-0000-1000-8000-00805F9B34FB"

# ── Service d0ff – proprietary ───────────────────────────────────────────────
UUID_FFD1  = "0000FFD1-0000-1000-8000-00805F9B34FB"  # write-without-response
UUID_FFD2  = "0000FFD2-0000-1000-8000-00805F9B34FB"
UUID_FFD3  = "0000FFD3-0000-1000-8000-00805F9B34FB"
UUID_FFD4  = "0000FFD4-0000-1000-8000-00805F9B34FB"
UUID_FFD5  = "0000FFD5-0000-1000-8000-00805F9B34FB"
UUID_FFF1  = "0000FFF1-0000-1000-8000-00805F9B34FB"

# ── EF02 Frame Layout ────────────────────────────────────────────────────────
# aa 0d a0 21 | p0  p1  p2  p3  p4  p5  p6  p7  p8  p9  p10 p11 | ee
#               spd tmr flg 00  pm  00  adc 10  e0  02  adc chk
#
# p[0]  fan speed  : 0=Spd1  1=Spd2  2=Spd3  3=Spd4
# p[1]  timer hrs  : 0=OFF   2=2h    4=4h    8=8h
# p[2]  flags      : bit0=Power bit1=UVC bit2=Timer bit5=Auto bit6+7=Night
# p[4]  PM2.5 raw  : ÷10 = µg/m³  (e.g. 50 → 5.0 µg/m³)
# p[11] checksum   : (p0+p1+p2+p4+p6+p10+0xC0) & 0xFF
#
# ── EF03 Characteristic (purpose unknown) ───────────────────────────────────
# Subscribed for reverse-engineering; raw hex logged via AC500EF03RawSensor
#
# ── EF04 History Buffer (on connect) ─────────────────────────────────────────
# EF04 is a circular history buffer of (PM2.5_raw, temp×10) measurement pairs.
# Structure per 20-byte frame: 5 × (PM2.5_raw u16, temp×10 u16) big-endian
# Framing: preceded by 0x01 (init), terminated by 0xFF
# even-indexed pairs (0,2,4,…) = PM2.5 raw (÷10 = µg/m³)
# odd-indexed  pairs (1,3,5,…) = Temperature×10 (÷10 = °C)
# Last valid odd pair = most recent temperature reading
# NO humidity sensor on this device – pair[4] is PM2.5 history, not humidity

FLAG_POWER = 0x01
FLAG_UVC   = 0x02
FLAG_TIMER = 0x04
FLAG_AUTO  = 0x20
FLAG_NIGHT = 0x40

SPEED_MAP     = {0: "speed_1", 1: "speed_2", 2: "speed_3", 3: "speed_4"}
SPEED_MAP_INV = {v: k for k, v in SPEED_MAP.items()}
PRESET_MODES  = ["speed_1", "speed_2", "speed_3", "speed_4", "auto"]

COMMANDS = {
    "power_on":   "aa0301000105ee",
    "power_off":  "aa0301000004ee",
    "uvc_on":     "aa0303000107ee",
    "uvc_off":    "aa0303000006ee",
    "night_on":   "aa030600010aee",
    "night_off":  "aa03af0001b3ee",
    "speed_1":    "aa0302000005ee",
    "speed_2":    "aa0302000106ee",
    "speed_3":    "aa0302000207ee",
    "speed_4":    "aa0302000308ee",
    "auto_on":    "aa0305000109ee",
    "auto_off":   "aa0305000008ee",
    "timer_off":  "aa0304000007ee",
    "timer_2h":   "aa0304000209ee",
    "timer_4h":   "aa030400040bee",
    "timer_8h":   "aa030400080fee",
}
