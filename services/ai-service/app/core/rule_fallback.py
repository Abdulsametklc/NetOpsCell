from app.schemas.contracts import FaultType, PowerStatus, TelemetryInput

# Kural tabanli skorlayici: LLM'e (veya LLM saglayicisina) ulasilamadiginda devreye girer.
# Girdiye gore GERCEKTEN degisir - hicbir kosulda sabit/hardcoded bir deger donmez
# (case'in diskalifiye kurali: "AI servisi mock/hardcoded ise degerlendirme disi").
#
# Agirliklar ARCHITECTURE.md SS8.7'deki ornekle birebir ayni; her esik asimi hem toplam
# olasiliga hem de o metrigin isaret ettigi ariza turune katki yapar.
TEMPERATURE_THRESHOLD_C = 65.0
TEMPERATURE_WEIGHT = 0.35

PACKET_LOSS_THRESHOLD_PCT = 15.0
PACKET_LOSS_WEIGHT = 0.30

SIGNAL_STRENGTH_THRESHOLD_DBM = -100.0
SIGNAL_STRENGTH_WEIGHT = 0.20

POWER_OUTAGE_WEIGHT = 0.35

RECURRING_FAULT_THRESHOLD_COUNT = 2
RECURRING_FAULT_WEIGHT = 0.15


def rule_based_predict(payload: TelemetryInput) -> tuple[float, FaultType]:
    """Dondugu deger cifti: (probability 0.0-1.0, en olasi ariza turu)."""
    contributions: dict[FaultType, float] = {}

    def add(fault_type: FaultType, weight: float) -> None:
        contributions[fault_type] = contributions.get(fault_type, 0.0) + weight

    if payload.temperature > TEMPERATURE_THRESHOLD_C:
        add(FaultType.ISINMA, TEMPERATURE_WEIGHT)

    if payload.packet_loss > PACKET_LOSS_THRESHOLD_PCT:
        add(FaultType.BAGLANTI, PACKET_LOSS_WEIGHT)

    if payload.signal_strength < SIGNAL_STRENGTH_THRESHOLD_DBM:
        add(FaultType.BAGLANTI, SIGNAL_STRENGTH_WEIGHT)

    if payload.power_status == PowerStatus.KESINTIDE:
        add(FaultType.GUC_KESINTISI, POWER_OUTAGE_WEIGHT)

    if payload.recent_fault_count >= RECURRING_FAULT_THRESHOLD_COUNT:
        add(FaultType.DONANIM, RECURRING_FAULT_WEIGHT)

    if not contributions:
        return 0.0, FaultType.BELIRSIZ

    probability = min(sum(contributions.values()), 0.99)
    dominant_fault_type = max(contributions, key=contributions.get)
    return probability, dominant_fault_type
