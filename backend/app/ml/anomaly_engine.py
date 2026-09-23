import time
import logging
import math
from typing import Any

logger = logging.getLogger(__name__)

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

try:
    from sklearn.svm import OneClassSVM
    from sklearn.neighbors import LocalOutlierFactor
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


class AnomalyDetectionEngine:
    """
    Unsupervised Anomaly Detection Engine using:
    1. One-Class SVM (Support Vector Machine with RBF kernel)
    2. Local Outlier Factor (LOF - Density-based local outlier detection)
    
    Identifies atypical citizen applications, fraudulent multivariate outliers,
    and irregular inter-governmental mesh patterns without requiring pre-labeled fraud datasets.
    """

    FEATURE_NAMES = [
        "income_ratio",          # abs(claimed - mesh) / max(claimed, mesh)
        "land_discrepancy",      # abs(claimed - registry)
        "ocr_confidence",        # 0.0 to 1.0
        "name_match_score",      # 0.0 to 1.0
        "income_to_land_ratio",  # claimed income / (land + 0.1)
        "past_rejections",       # count
    ]

    def __init__(self, contamination: float = 0.05):
        self.contamination = contamination
        self._scaler: Any = None
        self._ocsvm: Any = None
        self._lof: Any = None
        self._is_fitted = False

        if SKLEARN_AVAILABLE and NUMPY_AVAILABLE:
            self._initialize_baseline_models()

    @property
    def is_ready(self) -> bool:
        return SKLEARN_AVAILABLE and NUMPY_AVAILABLE

    def _generate_synthetic_baseline(self, n_samples: int = 250) -> Any:
        """Generates representative distribution of normal, legitimate citizen applications."""
        rng = np.random.default_rng(seed=42)
        # Normal applications: low income discrepancy, low land diff, high OCR, high name match
        income_ratios = rng.beta(a=1.5, b=8.0, size=n_samples) * 0.30       # mostly 0.0 - 0.15
        land_diffs = rng.exponential(scale=0.2, size=n_samples)              # mostly 0.0 - 0.5
        ocr_confs = rng.beta(a=8.0, b=1.5, size=n_samples)                   # mostly 0.85 - 0.99
        name_matches = rng.beta(a=9.0, b=1.2, size=n_samples)                # mostly 0.90 - 1.0
        log_inc_to_land = rng.normal(loc=4.7, scale=0.5, size=n_samples)     # log10 scale
        rejections = rng.poisson(lam=0.2, size=n_samples)                    # mostly 0

        X = np.column_stack([
            income_ratios,
            land_diffs,
            ocr_confs,
            name_matches,
            log_inc_to_land,
            rejections,
        ])
        return X

    def _initialize_baseline_models(self):
        """Pre-fits One-Class SVM and LOF on legitimate baseline mesh distribution."""
        try:
            X_train = self._generate_synthetic_baseline(n_samples=300)
            self._scaler = StandardScaler()
            X_scaled = self._scaler.fit_transform(X_train)

            # 1. One-Class SVM with RBF kernel
            self._ocsvm = OneClassSVM(
                kernel="rbf",
                gamma="scale",
                nu=self.contamination,
            )
            self._ocsvm.fit(X_scaled)

            # 2. Local Outlier Factor (LOF) with novelty=True for out-of-sample prediction
            self._lof = LocalOutlierFactor(
                n_neighbors=20,
                contamination=self.contamination,
                novelty=True,
            )
            self._lof.fit(X_scaled)

            self._is_fitted = True
            logger.info("One-Class SVM and Local Outlier Factor engines successfully calibrated.")
        except Exception as e:
            logger.warning(f"Could not fit sklearn models: {e}")
            self._is_fitted = False

    def _extract_feature_vector(self, data: dict[str, Any]) -> tuple[list[float], list[str]]:
        """Converts raw application attributes into a 6D normalized feature vector and identifies outlier reasons."""
        claimed_inc = float(data.get("annual_income_claimed", 100000.0))
        mesh_inc = float(data.get("annual_income_tax_mesh", claimed_inc))
        claimed_land = float(data.get("land_holding_acres_claimed", 2.0))
        mesh_land = float(data.get("land_holding_acres_registry", claimed_land))
        ocr_conf = float(data.get("ocr_confidence", 0.95))
        name_match = float(data.get("name_match_score", 1.0))
        rejections = float(data.get("past_rejections_count", 0))

        if claimed_inc > 0 and mesh_inc > 0:
            income_ratio = abs(mesh_inc - claimed_inc) / max(mesh_inc, claimed_inc)
        else:
            income_ratio = 1.0 if (claimed_inc != mesh_inc) else 0.0

        land_diff = abs(claimed_land - mesh_land)
        raw_inc_to_land = (claimed_inc / max(1.0, claimed_land)) if claimed_land > 0 else 50000.0
        log_inc_to_land = math.log10(max(10.0, raw_inc_to_land))

        feature_vector = [income_ratio, land_diff, ocr_conf, name_match, log_inc_to_land, rejections]

        reasons = []
        if income_ratio > 0.40:
            reasons.append(f"Unusual income divergence: {income_ratio * 100:.1f}% gap between claim and tax mesh")
        if land_diff > 2.0:
            reasons.append(f"Significant land discrepancy: {land_diff:.1f} acres difference from land registry")
        if ocr_conf < 0.75:
            reasons.append(f"Substandard OCR clarity: {ocr_conf * 100:.1f}% confidence")
        if name_match < 0.80:
            reasons.append(f"Name token deviation: {name_match * 100:.1f}% match with citizen registry")
        if rejections >= 2:
            reasons.append(f"Elevated application rejection history ({int(rejections)} prior rejections)")

        return feature_vector, reasons

    def detect_outliers(
        self,
        features_data: dict[str, Any],
        algorithm: str = "ensemble",
    ) -> dict[str, Any]:
        """
        Runs One-Class SVM and/or Local Outlier Factor (LOF) anomaly detection.
        Algorithm options: 'one_class_svm', 'lof', or 'ensemble'.
        """
        start_time = time.perf_counter()
        algo = algorithm.lower()
        if algo not in ["one_class_svm", "lof", "ensemble"]:
            algo = "ensemble"

        raw_features, outlier_reasons = self._extract_feature_vector(features_data)

        ocsvm_pred = 1
        ocsvm_score = 0.0
        lof_pred = 1
        lof_score = 1.0

        if self.is_ready and self._is_fitted:
            try:
                X = np.array([raw_features])
                X_scaled = self._scaler.transform(X)

                # One-Class SVM (-1 for outlier, 1 for inlier)
                ocsvm_pred = int(self._ocsvm.predict(X_scaled)[0])
                ocsvm_score = float(self._ocsvm.decision_function(X_scaled)[0])

                # Local Outlier Factor (-1 for outlier, 1 for inlier)
                lof_pred = int(self._lof.predict(X_scaled)[0])
                lof_score = float(-self._lof.score_samples(X_scaled)[0])
            except Exception as e:
                logger.warning(f"Error during scikit-learn anomaly inference: {e}")

        # Fallback / statistical boundary computation if sklearn not loaded
        if not (self.is_ready and self._is_fitted):
            inc_ratio, land_diff, ocr_conf, name_match, log_inc_to_land, rejections = raw_features
            anomaly_penalty = 0.0
            if inc_ratio > 0.35:
                anomaly_penalty += inc_ratio * 0.40
            if land_diff > 1.5:
                anomaly_penalty += min(0.30, land_diff * 0.10)
            if ocr_conf < 0.75:
                anomaly_penalty += (0.75 - ocr_conf) * 0.35
            if name_match < 0.80:
                anomaly_penalty += (0.80 - name_match) * 0.45
            if rejections >= 2:
                anomaly_penalty += 0.20

            is_outlier = anomaly_penalty >= 0.35
            ocsvm_pred = -1 if is_outlier else 1
            lof_pred = -1 if is_outlier else 1
            ocsvm_score = round(-anomaly_penalty, 4)
            lof_score = round(1.0 + (anomaly_penalty * 1.5), 4)

        # Combine decisions based on chosen algorithm
        if algo == "one_class_svm":
            ocsvm_norm = 1.0 / (1.0 + math.exp(max(-10.0, min(10.0, ocsvm_score * 3.0))))
            anomaly_score = round(ocsvm_norm, 4)
            is_anomaly = (anomaly_score >= 0.50) or (ocsvm_pred == -1 and anomaly_score > 0.45)
        elif algo == "lof":
            lof_norm = min(0.99, max(0.01, (lof_score - 1.0) * 0.8 + 0.1))
            anomaly_score = round(lof_norm, 4)
            is_anomaly = (anomaly_score >= 0.50) or (lof_pred == -1 and anomaly_score > 0.45)
        else:  # ensemble
            ocsvm_norm = 1.0 / (1.0 + math.exp(max(-10.0, min(10.0, ocsvm_score * 3.0))))
            lof_norm = min(0.99, max(0.01, (lof_score - 1.0) * 0.8 + 0.1))
            anomaly_score = round((ocsvm_norm + lof_norm) / 2.0, 4)
            is_anomaly = (anomaly_score >= 0.50) or (ocsvm_pred == -1 and lof_pred == -1)

        if anomaly_score >= 0.65:
            verdict = "HIGH_RISK_ANOMALY"
        elif anomaly_score >= 0.45 or is_anomaly:
            verdict = "SUSPICIOUS_OUTLIER"
        else:
            verdict = "NORMAL_INLIER"

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

        return {
            "success": True,
            "algorithm_used": algo,
            "is_anomaly": is_anomaly,
            "anomaly_score": anomaly_score,
            "ocsvm_prediction": "OUTLIER" if ocsvm_pred == -1 else "INLIER",
            "ocsvm_distance": round(ocsvm_score, 4),
            "lof_prediction": "OUTLIER" if lof_pred == -1 else "INLIER",
            "lof_score": round(lof_score, 4),
            "status_verdict": verdict,
            "outlier_reasons": outlier_reasons,
            "processing_time_ms": elapsed_ms,
        }


# Singleton instance
anomaly_engine = AnomalyDetectionEngine()
