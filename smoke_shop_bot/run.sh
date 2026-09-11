#!/usr/bin/env bash
# تشغيل البوت مع إعادة تشغيل تلقائي لو صار قطع بالنت أو تسكر لأي سبب.
# استخدام: bash run.sh   (اتركه شغال بخلفية بـ screen أو tmux أو nohup)
cd "$(dirname "$0")"
while true; do
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] بنشغل البوت..."
  python3 bot.py
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] البوت وقف. رح يعيد التشغيل خلال ٥ ثواني... (Ctrl+C للإيقاف النهائي)"
  sleep 5
done
