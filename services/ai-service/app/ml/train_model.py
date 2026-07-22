"""
NetOpsCell AI Service - egitilmis ML modeli (case SS12.1 bonus: +8).

Egitim verisi: training_data.json (docs/sample_telemetry.json'dan kopyalandi,
122 etiketli telemetri ornegi - bkz. docs/ai-approach.md SS7).

Birden fazla algoritma, her biri icin GridSearchCV ile hiperparametre
aramasi yapilarak (5-fold stratified CV, sadece egitim havuzunda - holdout'a
hic dokunulmadan) karsilastirilir. En iyi (tuned) skoru alan algoritma/
hiperparametre kombinasyonu, hic gorulmemis holdout'ta bir kez degerlendirilip
sonra tum veriyle yeniden egitilerek model.joblib olarak kaydedilir
(bkz. docs/ai-approach.md SS7.1 - karsilastirma tablosu).

Kullanim:
    python -m app.ml.train_model

Cikti:
    app/ml/model.joblib          - secilen (en iyi, tuned) modelin pipeline'i
    app/ml/model_comparison.md   - tum algoritmalarin karsilastirma tablosu
"""

import json
from pathlib import Path

import joblib
from sklearn.base import clone
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
from sklearn.model_selection import GridSearchCV, StratifiedKFold, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

DATA_PATH = Path(__file__).parent / "training_data.json"
MODEL_PATH = Path(__file__).parent / "model.joblib"
COMPARISON_PATH = Path(__file__).parent / "model_comparison.md"

FEATURE_NAMES = [
    "signal_strength",
    "packet_loss",
    "temperature",
    "recent_fault_count",
    "power_status_kesintide",
]

SCORING = ["accuracy", "precision_macro", "recall_macro", "f1_macro"]

# Her aday: (base pipeline, hiperparametre arama gridi). Grid anahtarlari
# "clf__" ile baslar (Pipeline icindeki adimin adi). GridSearchCV her
# kombinasyonu 5-fold CV ile dener - en iyi f1_macro'ya gore secer.
CANDIDATES: dict[str, tuple[Pipeline, dict]] = {
    "LogisticRegression": (
        Pipeline(
            [
                ("scaler", StandardScaler()),
                ("clf", LogisticRegression(max_iter=2000, class_weight="balanced", random_state=42)),
            ]
        ),
        {"clf__C": [0.01, 0.1, 1.0, 10.0, 100.0]},
    ),
    "SVM": (
        Pipeline(
            [
                ("scaler", StandardScaler()),
                ("clf", SVC(kernel="rbf", probability=True, class_weight="balanced", random_state=42)),
            ]
        ),
        {
            "clf__C": [0.1, 1.0, 10.0, 100.0],
            "clf__gamma": ["scale", "auto", 0.01, 0.1, 1.0],
        },
    ),
    "RandomForest": (
        Pipeline(
            [
                ("scaler", StandardScaler()),
                ("clf", RandomForestClassifier(random_state=42, class_weight="balanced")),
            ]
        ),
        {
            "clf__n_estimators": [100, 200, 400],
            "clf__max_depth": [4, 6, 8, None],
            "clf__min_samples_leaf": [1, 2, 4],
        },
    ),
    "GradientBoosting": (
        Pipeline(
            [
                ("scaler", StandardScaler()),
                ("clf", GradientBoostingClassifier(random_state=42)),
            ]
        ),
        {
            "clf__n_estimators": [100, 150, 250],
            "clf__max_depth": [2, 3, 4],
            "clf__learning_rate": [0.05, 0.1, 0.2],
        },
    ),
}


def load_dataset() -> tuple[list[list[float]], list[str]]:
    raw = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    features: list[list[float]] = []
    labels: list[str] = []
    for sample in raw["samples"]:
        features.append(
            [
                sample["signal_strength"],
                sample["packet_loss"],
                sample["temperature"],
                sample["recent_fault_count"],
                1.0 if sample["power_status"] == "KESINTIDE" else 0.0,
            ]
        )
        labels.append(sample["label"]["fault_type"])
    return features, labels


def tune_candidates(
    X: list[list[float]], y: list[str]
) -> dict[str, dict]:
    """Her aday icin GridSearchCV ile hiperparametre aramasi yapar (5-fold CV,
    sadece verilen X/y uzerinde - cagiran taraf bunun holdout icermedigini
    garanti etmeli). En iyi (tuned) pipeline + 4 metrik + secilen parametreleri
    dondurur."""
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    results: dict[str, dict] = {}
    for name, (pipeline, param_grid) in CANDIDATES.items():
        search = GridSearchCV(
            pipeline,
            param_grid,
            scoring=SCORING,
            refit="f1_macro",
            cv=cv,
            n_jobs=-1,
        )
        search.fit(X, y)
        best_idx = search.best_index_
        cv_results = search.cv_results_
        results[name] = {
            "pipeline": search.best_estimator_,
            "best_params": search.best_params_,
            "accuracy": cv_results["mean_test_accuracy"][best_idx],
            "precision_macro": cv_results["mean_test_precision_macro"][best_idx],
            "recall_macro": cv_results["mean_test_recall_macro"][best_idx],
            "f1_macro": cv_results["mean_test_f1_macro"][best_idx],
        }
    return results


def main() -> None:
    X, y = load_dataset()

    # SIZINTIYI ONLEMEK ICIN KRITIK SIRALAMA: holdout seti model secimi
    # baslamadan ONCE ayrilir ve secim asamasinda HICBIR sekilde kullanilmaz.
    # Aksi halde (once tum veriyle CV yapip sonra ayni veriden holdout almak)
    # algoritma secimi zaten holdout'taki satirlari "gormus" olur - bu da
    # raporlanan holdout skorunu iyimser/yanli gosterir (bkz. docs/ai-approach.md SS8).
    X_pool, X_holdout, y_pool, y_holdout = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # Model secimi + hiperparametre aramasi SADECE pool (egitim havuzu)
    # uzerinde, GridSearchCV + 5-fold CV ile yapilir.
    tuned = tune_candidates(X_pool, y_pool)
    ranked = sorted(tuned.items(), key=lambda kv: kv[1]["f1_macro"], reverse=True)
    winner_name = ranked[0][0]
    winner_params = tuned[winner_name]["best_params"]

    print(f"=== GridSearchCV + 5-fold CV karsilastirmasi (pool: {len(X_pool)} ornek, holdout HARIC) ===")
    for name, metrics in ranked:
        print(
            f"{name:20s} acc={metrics['accuracy']:.3f}  "
            f"precision={metrics['precision_macro']:.3f}  "
            f"recall={metrics['recall_macro']:.3f}  "
            f"f1={metrics['f1_macro']:.3f}  "
            f"best_params={tuned[name]['best_params']}"
        )
    print(f"\nSecilen model (en yuksek f1_macro): {winner_name} {winner_params}")

    # GridSearchCV'nin best_estimator_'u zaten pool ile fit edilmis durumda -
    # hic gormedigi holdout uzerinde BIR KEZ degerlendiriyoruz (tarafsiz tahmin).
    winner_pipeline = tuned[winner_name]["pipeline"]
    y_pred = winner_pipeline.predict(X_holdout)
    holdout_report = classification_report(y_holdout, y_pred, zero_division=0)
    print(f"\n=== {winner_name} - hic gorulmemis holdout raporu ({len(y_holdout)} ornek) ===")
    print(holdout_report)

    # Production'da kullanilacak nihai pipeline: ayni (tuned) hiperparametrelerle,
    # ARTIK holdout de dahil TUM veriyle yeniden egitilir (model secimi/
    # degerlendirmesi bittikten sonra bunu yapmak sizinti degildir, standart pratiktir).
    base_pipeline, _ = CANDIDATES[winner_name]
    final_pipeline = clone(base_pipeline).set_params(**winner_params)
    final_pipeline.fit(X, y)
    joblib.dump(
        {"pipeline": final_pipeline, "feature_names": FEATURE_NAMES, "algorithm": winner_name},
        MODEL_PATH,
    )
    print(f"\nModel kaydedildi: {MODEL_PATH}")

    comparison_lines = [
        "# Model Karsilastirmasi - NetOpsCell AI Fallback\n",
        f"Veri seti: `{DATA_PATH.name}` - {len(X)} ornek toplam. Sizinti onlemek icin "
        f"once %20 holdout ({len(y_holdout)} ornek) ayrildi ve model secimine/aramaya hic "
        f"dahil edilmedi; GridSearchCV + 5-fold CV karsilastirmasi sadece kalan pool "
        f"({len(y_pool)} ornek) uzerinde yapildi.\n",
        "| Algoritma | Accuracy | Precision (macro) | Recall (macro) | F1 (macro) | En iyi parametreler |",
        "|---|---|---|---|---|---|",
    ]
    for name, metrics in ranked:
        marker = " **(secildi)**" if name == winner_name else ""
        comparison_lines.append(
            f"| {name}{marker} | {metrics['accuracy']:.3f} | "
            f"{metrics['precision_macro']:.3f} | {metrics['recall_macro']:.3f} | "
            f"{metrics['f1_macro']:.3f} | `{tuned[name]['best_params']}` |"
        )
    comparison_lines.append(
        f"\n## Secilen model: {winner_name}\n\n"
        f"GridSearchCV ile hiperparametre aramasi + 5-fold CV F1 (macro) skoruna gore "
        f"(sadece pool uzerinde) en iyi sonucu verdigi icin secildi. Secilen parametreler: "
        f"`{winner_params}`.\n\nModel secimi sirasinda hic gorulmemis holdout seti "
        f"({len(y_holdout)} ornek) uzerindeki tarafsiz degerlendirme:\n\n```\n{holdout_report}\n```\n"
    )
    COMPARISON_PATH.write_text("\n".join(comparison_lines), encoding="utf-8")
    print(f"Karsilastirma raporu kaydedildi: {COMPARISON_PATH}")


if __name__ == "__main__":
    main()
