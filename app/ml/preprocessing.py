"""Reusable preprocessing components for WinDrive training and live prediction."""
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin


class DropAllMissingColumns(BaseEstimator, TransformerMixin):
    """Omit numeric columns with no observed training value from model transforms.

    The declared feature schema is intentionally retained outside this transformer.
    This only prevents an imputer from trying to calculate a median where no median
    exists. The fitted column decision is reused unchanged during live inference.
    """

    def fit(self, X, y=None):
        frame = self._frame(X)
        self.retained_columns_ = [column for column in frame.columns if frame[column].notna().any()]
        self.dropped_columns_ = [column for column in frame.columns if column not in self.retained_columns_]
        return self

    def transform(self, X):
        frame = self._frame(X)
        missing = set(self.retained_columns_) - set(frame.columns)
        if missing:
            raise ValueError(f"Inference data is missing declared numeric feature columns: {sorted(missing)}")
        return frame.loc[:, self.retained_columns_]

    @staticmethod
    def _frame(X):
        return X if isinstance(X, pd.DataFrame) else pd.DataFrame(X)
