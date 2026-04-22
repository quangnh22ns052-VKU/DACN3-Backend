"""
TEN FILE: backend/models/model_metrics.py

CONG DUNG:
  - Dinh nghia bang ModelMetrics trong database
  - Theo doi hieu suat cua mo hinh ML
  - Ghi nhan metrics sau khi huan luyen
  - So sanh hieu suat giua cac phien ban mo hinh

CTRUC BANG MODELMETRICS:
  * id: Khoa chinh (auto-increment)
  * model_version: Phien ban mo hinh (v1.0, v1.1, v2.0)
  * accuracy: Accuracy (0.0-1.0)
  * precision: Precision (0.0-1.0)
  * recall: Recall/Sensitivity (0.0-1.0)
  * f1_score: F1-score (0.0-1.0)
  * auc_roc: Area under ROC curve (0.0-1.0)
  * confusion_matrix: Chi tiet True/False Positives/Negatives
  * dataset_size: So luong mau trong tap huan luyen
  * training_time: Thoi gian huan luyen (seconds)
  * created_at: Thoi gian luu metrics

USAGE:
  from backend.models.model_metrics import ModelMetrics
  db.add(ModelMetrics(model_version="v1.0", accuracy=0.91, precision=0.89))
  db.commit()

TRUY VAN:
  latest_metrics = db.query(ModelMetrics).order_by(ModelMetrics.created_at.desc()).first()
  all_versions = db.query(ModelMetrics).order_by(ModelMetrics.model_version).all()
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from backend.models.database import Base


class ModelMetrics(Base):
    """
    ModelMetrics model for tracking phishing detector model performance.
    
    Used for:
    1. Version tracking - keep history of model performance
    2. A/B testing - compare different model versions
    3. Retraining decisions - know when to retrain model
    4. Performance monitoring - track accuracy over time
    
    Each time model is trained/retrained, a new record is created.
    """
    
    __tablename__ = "model_metrics"
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    
    # Model version identifier (unique)
    model_version = Column(
        String(50),
        unique=True,
        nullable=False,
        index=True
    )  # e.g., "v1", "v2", "v1.0.1", etc.
    
    # Performance metrics
    accuracy = Column(Float, nullable=False)  # Overall accuracy (0.0-1.0)
    precision = Column(Float, nullable=False)  # True positives / (True positives + False positives)
    recall = Column(Float, nullable=False)  # True positives / (True positives + False negatives)
    f1_score = Column(Float, nullable=False)  # Harmonic mean of precision and recall
    
    # Additional metrics
    false_positive_rate = Column(Float, nullable=True)  # False positives / (False positives + True negatives)
    false_negative_rate = Column(Float, nullable=True)  # False negatives / (False negatives + True positives)
    
    # Timestamps
    trained_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )  # When model was trained
    promoted_at = Column(
        DateTime(timezone=True),
        nullable=True
    )  # When model was promoted to production (NULL if not yet promoted)
    
    def __repr__(self):
        return (
            f"<ModelMetrics(version='{self.model_version}', "
            f"accuracy={self.accuracy}, precision={self.precision}, "
            f"recall={self.recall}, f1={self.f1_score})>"
        )
