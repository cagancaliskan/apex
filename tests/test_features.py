"""
Unit tests for feature engineering module.
"""

import pytest
from rsw.features.build import FeatureFrame, build_features
from rsw.features.filters import (
    is_valid_lap,
    filter_outliers_zscore,
    filter_outliers_iqr,
    apply_filters,
)
from rsw.features.traffic import detect_traffic, estimate_traffic_delta


class TestFeatureBuilder:
    """Test suite for feature building."""
    
    def test_build_features_basic(self):
        """Test basic feature frame creation."""
        lap_times = [92.5, 92.6, 92.8]
        
        frame = build_features(
            driver_number=1,
            lap_number=3,
            lap_times=lap_times,
            lap_in_stint=3,
            stint_number=1,
            compound="SOFT",
            tyre_age=3,
            gap_ahead=2.5,
            total_laps=50,
        )
        
        assert frame.driver_number == 1
        assert frame.lap_number == 3
        assert frame.lap_in_stint == 3
        assert frame.compound == "SOFT"
        assert frame.lap_time == 92.8
        assert frame.best_lap_time == 92.5
    
    def test_track_evolution(self):
        """Test track evolution calculation."""
        frame = build_features(
            driver_number=1,
            lap_number=25,
            lap_times=[90.0],
            lap_in_stint=1,
            stint_number=1,
            compound="MEDIUM",
            tyre_age=1,
            gap_ahead=None,
            total_laps=50,
        )
        
        assert frame.track_evolution == 0.5  # Halfway through race
    
    def test_traffic_detection(self):
        """Test traffic detection in features."""
        # Close gap = traffic
        frame1 = build_features(
            driver_number=1,
            lap_number=1,
            lap_times=[92.0],
            lap_in_stint=1,
            stint_number=1,
            compound="SOFT",
            tyre_age=1,
            gap_ahead=1.0,  # < 1.5 threshold
            total_laps=50,
        )
        
        assert frame1.traffic_affected is True
        assert frame1.clean_air is False
        
        # Large gap = clean air
        frame2 = build_features(
            driver_number=1,
            lap_number=1,
            lap_times=[92.0],
            lap_in_stint=1,
            stint_number=1,
            compound="SOFT",
            tyre_age=1,
            gap_ahead=3.0,  # > 2.0 threshold
            total_laps=50,
        )
        
        assert frame2.traffic_affected is False
        assert frame2.clean_air is True
    
    def test_validity_flags(self):
        """Test lap validity detection."""
        # Valid lap
        frame1 = build_features(
            driver_number=1,
            lap_number=1,
            lap_times=[92.0],
            lap_in_stint=1,
            stint_number=1,
            compound="SOFT",
            tyre_age=1,
            gap_ahead=3.0,
            total_laps=50,
            is_pit_out=False,
            is_sc=False,
        )
        
        assert frame1.is_valid is True
        
        # Invalid - pit out lap
        frame2 = build_features(
            driver_number=1,
            lap_number=1,
            lap_times=[95.0],
            lap_in_stint=1,
            stint_number=1,
            compound="SOFT",
            tyre_age=1,
            gap_ahead=3.0,
            total_laps=50,
            is_pit_out=True,
        )
        
        assert frame2.is_valid is False


class TestFilters:
    """Test suite for lap time filters."""
    
    def test_is_valid_lap(self):
        """Test basic lap validation."""
        assert is_valid_lap(92.5) is True
        assert is_valid_lap(None) is False
        assert is_valid_lap(0) is False
        assert is_valid_lap(200.0) is False  # Too slow
        assert is_valid_lap(92.5, is_pit_in=True) is False
        assert is_valid_lap(92.5, is_sc=True) is False
    
    def test_outlier_zscore(self):
        """Test z-score outlier detection."""
        lap_times = [90.0, 90.2, 90.1, 90.3, 90.2, 95.0, 90.1]  # 95.0 is outlier
        
        filtered = filter_outliers_zscore(lap_times, threshold=2.0)
        filtered_times = [t for _, t in filtered]
        
        assert 95.0 not in filtered_times
        assert len(filtered_times) == 6
    
    def test_outlier_iqr(self):
        """Test IQR outlier detection."""
        lap_times = [90.0, 90.2, 90.1, 90.3, 90.2, 100.0, 90.1]  # 100.0 is outlier
        
        filtered = filter_outliers_iqr(lap_times, multiplier=1.5)
        filtered_times = [t for _, t in filtered]
        
        assert 100.0 not in filtered_times
    
    def test_apply_filters(self):
        """Test combined filter application."""
        # Create frames with various validity issues
        frames = []
        for i in range(10):
            frame = FeatureFrame(
                driver_number=1,
                lap_number=i + 1,
                lap_in_stint=i + 1,
                lap_time=90.0 + i * 0.1,
                is_valid=True,
            )
            frames.append(frame)
        
        # Add invalid frames
        frames[5].is_pit_out_lap = True
        frames[5].is_valid = False
        frames[8].is_sc_lap = True
        frames[8].is_valid = False
        
        filtered = apply_filters(frames, remove_pit_laps=True, remove_sc_laps=True)
        
        assert len(filtered) == 8  # 10 - 2 invalid


class TestTraffic:
    """Test suite for traffic detection."""
    
    def test_detect_traffic(self):
        """Test traffic detection logic."""
        # Close gap = traffic
        is_traffic, severity = detect_traffic(gap_ahead=1.0)
        assert is_traffic is True
        # Should detect moderate traffic
        assert severity >= 0.5
        
        # Large gap = no traffic
        is_traffic, severity = detect_traffic(gap_ahead=3.0)
        assert is_traffic is False
        assert severity == 0.0
    
    def test_traffic_delta(self):
        """Test traffic time delta estimation."""
        # Very close = max delta
        delta = estimate_traffic_delta(gap_ahead=0.3)
        assert delta > 0.5
        
        # Far = no delta
        delta = estimate_traffic_delta(gap_ahead=3.0)
        assert delta == 0.0
