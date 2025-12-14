# CPU-Scheduler-Project

# Bu ptoje İşteim Sistemleri dersi için yapılmıştır.
# 6 CPU Zamanlama Algoritmasını test eder.FCFS, Preemptive SJF, Non-preemptive SJF, Round Robin, Preemptive Priority, Non-preemptive Priority.

# Sonuçlar:
# FCFS, basit yapısı nedeniyle yüksek bekleme süresine sahiptir.
# SJF algoritmaları, ortalama bekleme ve çevrim süresini minimize etmektedir.
# Round Robin, adil bir zamanlama sağlar ancak bağlam değiştirme sayısı fazladır.
# Priority Scheduling, yüksek öncelikli süreçlere avantaj sağlar ancak düşük öncelikli süreçler aç kalabilir.
# Preemptive algoritmalar, tepki süresini iyileştirirken sistem yükünü artırabilir.

## Çalıştırma
```bash
python3 scheduler.py cases/case1.csv --out out_case1
python3 scheduler.py cases/case2.csv --out out_case2