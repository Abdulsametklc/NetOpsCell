# Model Karsilastirmasi - NetOpsCell AI Fallback

Veri seti: `training_data.json` - 122 ornek toplam. Sizinti onlemek icin once %20 holdout (25 ornek) ayrildi ve model secimine/aramaya hic dahil edilmedi; GridSearchCV + 5-fold CV karsilastirmasi sadece kalan pool (97 ornek) uzerinde yapildi.

| Algoritma | Accuracy | Precision (macro) | Recall (macro) | F1 (macro) | En iyi parametreler |
|---|---|---|---|---|---|
| SVM **(secildi)** | 0.906 | 0.881 | 0.861 | 0.856 | `{'clf__C': 1.0, 'clf__gamma': 1.0}` |
| LogisticRegression | 0.895 | 0.873 | 0.850 | 0.845 | `{'clf__C': 0.1}` |
| RandomForest | 0.886 | 0.838 | 0.828 | 0.817 | `{'clf__max_depth': 4, 'clf__min_samples_leaf': 1, 'clf__n_estimators': 200}` |
| GradientBoosting | 0.865 | 0.815 | 0.806 | 0.796 | `{'clf__learning_rate': 0.1, 'clf__max_depth': 3, 'clf__n_estimators': 150}` |

## Secilen model: SVM

GridSearchCV ile hiperparametre aramasi + 5-fold CV F1 (macro) skoruna gore (sadece pool uzerinde) en iyi sonucu verdigi icin secildi. Secilen parametreler: `{'clf__C': 1.0, 'clf__gamma': 1.0}`.

Model secimi sirasinda hic gorulmemis holdout seti (25 ornek) uzerindeki tarafsiz degerlendirme:

```
               precision    recall  f1-score   support

     BAGLANTI       0.80      1.00      0.89         4
     BELIRSIZ       0.86      1.00      0.92         6
      DONANIM       1.00      1.00      1.00         3
GUC_KESINTISI       1.00      0.80      0.89         5
       ISINMA       0.80      0.80      0.80         5
      YAZILIM       1.00      0.50      0.67         2

     accuracy                           0.88        25
    macro avg       0.91      0.85      0.86        25
 weighted avg       0.89      0.88      0.87        25

```
