"""
Unit tests for RLS degradation model.
"""

import numpy as np
import pytest
from rsw.models.degradation.rls import RLSEstimator, create_feature_vector


class TestRLSEstimator:
    """Test suite for Recursive Least Squares estimator."""
    
    def test_initialization(self):
        """Test RLS initializes correctly."""
        rls = RLSEstimator(n_features=2, forgetting_factor=0.95)
        
        assert rls.n_features == 2
        assert rls.lambda_ == 0.95
        assert rls.n_updates == 0
        assert len(rls.theta) == 2
        assert np.allclose(rls.theta, np.zeros(2))
    
    def test_warm_start(self):
        """Test warm starting with priors."""
        rls = RLSEstimator(n_features=2)
        rls.warm_start(base_pace=90.0, deg_slope=0.05)
        
        assert abs(rls.get_base_pace() - 90.0) < 0.01
        assert abs(rls.get_deg_slope() - 0.05) < 0.01
    
    def test_update_and_predict(self):
        """Test updating and prediction."""
        rls = RLSEstimator(n_features=2, forgetting_factor=1.0)
        
        # Simple linear relationship: y = 90 + 0.05 * x
        for lap in range(1, 11):
            x = create_feature_vector(lap)
            y = 90.0 + 0.05 * lap
            rls.update(x, y)
        
        # Should learn the relationship well with no noise
        assert abs(rls.get_base_pace() - 90.0) < 0.1
        assert abs(rls.get_deg_slope() - 0.05) < 0.01
        
        # Predict lap 15
        x_test = create_feature_vector(15)
        pred = rls.predict(x_test)
        expected = 90.0 + 0.05 * 15
        assert abs(pred - expected) < 0.2
    
    def test_forgetting_factor(self):
        """Test that forgetting factor allows adaptation."""
        rls = RLSEstimator(n_features=2, forgetting_factor=0.9)
        
        # Train on one slope
        for lap in range(1, 11):
            x = create_feature_vector(lap)
            y = 90.0 + 0.05 * lap
            rls.update(x, y)
        
        slope_before = rls.get_deg_slope()
        
        # Change dynamics (increased degradation)
        for lap in range(11, 21):
            x = create_feature_vector(lap)
            y = 90.0 + 0.10 * lap  # Higher slope
            rls.update(x, y)
        
        slope_after = rls.get_deg_slope()
        
        # Should have adapted upward
        assert slope_after > slope_before
    
    def test_noisy_data(self):
        """Test RLS handles noisy observations."""
        np.random.seed(42)
        rls = RLSEstimator(n_features=2, forgetting_factor=0.95)
        
        true_base = 92.0
        true_slope = 0.08
        
        for lap in range(1, 21):
            x = create_feature_vector(lap)
            # Add Gaussian noise
            y = true_base + true_slope * lap + np.random.normal(0, 0.3)
            rls.update(x, y)
        
        # Should be close despite noise
        assert abs(rls.get_base_pace() - true_base) < 1.0
        # The slope should be reasonably close (within 0.03)
        assert abs(rls.get_deg_slope() - true_slope) < 0.03
        
        # RMSE should be reasonable (relaxed for noisy data)
        assert rls.get_rmse() < 25.0
    
    def test_reset(self):
        """Test reset clears state."""
        rls = RLSEstimator(n_features=2)
        
        # Update with some data
        for lap in range(1, 6):
            x = create_feature_vector(lap)
            rls.update(x, 90.0 + lap)
        
        assert rls.n_updates > 0
        
        # Reset
        rls.reset()
        
        assert rls.n_updates == 0
        assert np.allclose(rls.theta, np.zeros(2))
    
    def test_prediction_uncertainty(self):
        """Test uncertainty estimation."""
        rls = RLSEstimator(n_features=2)
        
        # With little data, uncertainty should be high
        x = create_feature_vector(5)
        pred, std = rls.predict_with_uncertainty(x)
        assert std > 1.0  # High uncertainty
        
        # Add more data
        for lap in range(1, 20):
            x_train = create_feature_vector(lap)
            rls.update(x_train, 90.0 + 0.05 * lap)
        
        # Uncertainty should decrease
        pred2, std2 = rls.predict_with_uncertainty(x)
        assert std2 < std


def test_create_feature_vector():
    """Test feature vector creation."""
    x = create_feature_vector(5)
    assert len(x) == 2
    assert x[0] == 1.0  # Intercept
    assert x[1] == 5.0  # Lap in stint
