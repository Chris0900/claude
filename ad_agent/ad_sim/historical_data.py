from .models import HistoricalData, CampaignParams

HISTORICAL = [
    HistoricalData(
        month="6월",
        views_per_content=10_000,
        content_count=15,
        total_views=150_000,
        clicks=3_000,
        ctr=0.020,
        cpm=14_000,
        store_visits=300,
        visit_cvr=0.10,
        online_sales=240,
        online_cvr=0.08,
    ),
    HistoricalData(
        month="7월",
        views_per_content=12_000,
        content_count=8,
        total_views=96_000,
        clicks=1_920,
        ctr=0.020,
        cpm=14_000,
        store_visits=230,
        visit_cvr=0.12,
        online_sales=192,
        online_cvr=0.10,
    ),
    HistoricalData(
        month="8월",
        views_per_content=15_000,
        content_count=8,
        total_views=120_000,
        clicks=3_600,
        ctr=0.030,
        cpm=14_000,
        store_visits=540,
        visit_cvr=0.15,
        online_sales=360,
        online_cvr=0.10,
    ),
]

PRODUCT_PRICE_JPY = 2_300       # 16개입 판매가 (엔)
JPY_TO_KRW = 9.5                # 환율 (1엔 ≈ 9.5원, 2025-2026 기준)
PRODUCT_PRICE_KRW = int(PRODUCT_PRICE_JPY * JPY_TO_KRW)   # ≈ 21,850원

STORE_PURCHASE_RATE = 0.30      # 코스트코 방문자 중 실제 구매 비율 가정

# 9월 세 시나리오 파라미터
SCENARIOS = {
    "optimistic": {
        "label": "낙관 (예산 증액 + 인플루언서 확대)",
        "content_count": 15,
        "budget_krw": 2_100_000,       # 2,100,000원 (15명 × 평균 14만원 CPM)
        "views_per_content_mean": 17_000,
        "views_per_content_std": 3_000,
        "ctr_mean": 0.033,
        "ctr_std": 0.005,
        "visit_cvr_mean": 0.18,
        "visit_cvr_std": 0.025,
        "online_cvr_mean": 0.11,
        "online_cvr_std": 0.010,
    },
    "base": {
        "label": "기준 (동일 규모 유지 — 8월 트렌드 연장)",
        "content_count": 10,
        "budget_krw": 1_680_000,       # 8월과 동일
        "views_per_content_mean": 15_000,
        "views_per_content_std": 2_500,
        "ctr_mean": 0.030,
        "ctr_std": 0.004,
        "visit_cvr_mean": 0.15,
        "visit_cvr_std": 0.020,
        "online_cvr_mean": 0.10,
        "online_cvr_std": 0.010,
    },
    "pessimistic": {
        "label": "비관 (7월 수준으로 반등 실패)",
        "content_count": 8,
        "budget_krw": 1_344_000,       # 7월 수준
        "views_per_content_mean": 12_000,
        "views_per_content_std": 3_000,
        "ctr_mean": 0.020,
        "ctr_std": 0.005,
        "visit_cvr_mean": 0.12,
        "visit_cvr_std": 0.025,
        "online_cvr_mean": 0.08,
        "online_cvr_std": 0.012,
    },
}
