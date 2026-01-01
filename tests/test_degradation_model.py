"""
Unit tests for DriverDegradationModel.
"""

import pytest
from rsw.models.degradation.online_model import DriverDegradationModel


class TestDriverDegradationModel:
    """Test suite for driver degradation model."""
    
    def test_initialization(self):
        """Test model initializes correctly."""
        model = DriverDegradationModel(driver_number=44)
        
        assert model.driver_number == 44
        assert model.current_stint is None
        assert len(model.stint_history) == 0
    
    def test_new_stint(self):
        """Test creating a new stint."""
        model = DriverDegradationModel(driver_number=44)
        model.new_stint(stint_number=1, compound="SOFT", start_lap=1)
        
        assert model.current_stint is not None
        assert model.current_stint.compound == "SOFT"
        assert model.current_stint.stint_number == 1
    
    def test_update_and_predict(self):
        """Test updating model and making predictions."""
        model = DriverDegradationModel(driver_number=44)
        model.new_stint(stint_number=1, compound="SOFT", start_lap=1, base_pace=92.0)
        
        # Add consistent degrading laps
        for lap in range(1, 11):
            lap_time = 92.0 + 0.08 * lap  # 80ms/lap degradation
            model.update(lap_in_stint=lap, lap_time=lap_time, is_valid=True)
        
        # Get prediction
        pred = model.get_prediction(k=5)
        
        assert pred is not None
        assert pred.deg_slope > 0.05  # Should detect degradation
        assert pred.deg_slope < 0.15
        assert len(pred.predicted_next_k) == 5
        
        # Predictions should be increasing
        assert pred.predicted_next_k[4] > pred.predicted_next_k[0]
    
    def test_cliff_risk_calculation(self):
        """Test cliff risk scoring."""
        model = DriverDegradationModel(driver_number=44)
        model.new_stint(stint_number=1, compound="SOFT", start_lap=1)
        
        # Low degradation
        for lap in range(1, 11):
            model.update(lap_in_stint=lap, lap_time=92.0 + 0.03 * lap, is_valid=True)
        
        risk_low = model.get_cliff_risk()
        
        # High degradation
        model.new_stint(stint_number=2, compound="SOFT", start_lap=11)
        for lap in range(1, 11):
            model.update(lap_in_stint=lap, lap_time=92.0 + 0.15 * lap, is_valid=True)
        
        risk_high = model.get_cliff_risk()
        
        assert risk_high > risk_low
        assert risk_high > 0.5  # Should be flagged as risky
    
    def test_stint_transitions(self):
        """Test handling multiple stints."""
        model = DriverDegradationModel(driver_number=44)
        
        # First stint
        model.new_stint(stint_number=1, compound="SOFT", start_lap=1)
        for lap in range(1, 11):
            model.update(lap_in_stint=lap, lap_time=92.0 + 0.08 * lap, is_valid=True)
        
        assert model.current_stint.stint_number == 1
        assert len(model.stint_history) == 0
        
        # Second stint
        model.new_stint(stint_number=2, compound="MEDIUM", start_lap=11)
        for lap in range(1, 6):
            model.update(lap_in_stint=lap, lap_time=92.5 + 0.05 * lap, is_valid=True)
        
        assert model.current_stint.stint_number == 2
        assert len(model.stint_history) == 1
        assert model.stint_history[0].compound == "SOFT"
    
    def test_invalid_laps_filtered(self):
        """Test that invalid laps don't affect model."""
        model = DriverDegradationModel(driver_number=44)
        model.new_stint(stint_number=1, compound="SOFT", start_lap=1)
        
        # Valid laps with consistent degradation
        for lap in range(1, 11):
            model.update(lap_in_stint=lap, lap_time=92.0 + 0.05 * lap, is_valid=True)
        
        slope_before = model.get_deg_slope()
        
        # Add invalid outlier lap (should be ignored)
        model.update(lap_in_stint=11, lap_time=150.0, is_valid=False)
        
        slope_after = model.get_deg_slope()
        
        # Slope shouldn't change much (outlier ignored)
        assert abs(slope_after - slope_before) < 0.01
