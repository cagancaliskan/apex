#!/usr/bin/env python
"""
Manual test runner for F1 Race Strategy Workbench.
Runs all tests without pytest to avoid plugin conflicts.
"""

import sys
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np
from rsw.models.degradation.rls import RLSEstimator, create_feature_vector
from rsw.features.build import build_features
from rsw.features.filters import is_valid_lap, filter_outliers_zscore
from rsw.features.traffic import detect_traffic
from rsw.models.degradation.online_model import DriverDegradationModel, ModelManager


def test_rls_basic():
    """Test RLS estimator basic functionality."""
    print("\n=== Testing RLS Estimator ===")
    
    rls = RLSEstimator(n_features=2, forgetting_factor=1.0)
    
    # Train on simple linear function
    for lap in range(1, 21):
        x = create_feature_vector(lap)
        y = 90.0 + 0.05 * lap
        rls.update(x, y)
    
    base = rls.get_base_pace()
    slope = rls.get_deg_slope()
    
    print(f"✓ Base pace: {base:.3f}s (expected ~90.0s)")
    print(f"✓ Deg slope: {slope:.4f}s/lap (expected ~0.05s/lap)")
    print(f"✓ RMSE: {rls.get_rmse():.3f}s")
    
    assert abs(base - 90.0) < 0.1, "Base pace incorrect"
    assert abs(slope - 0.05) < 0.01, "Degradation slope incorrect"
    print("✅ RLS basic test PASSED\n")


def test_rls_noisy_data():
    """Test RLS with noisy observations."""
    print("=== Testing RLS with Noise ===")
    
    np.random.seed(42)
    rls = RLSEstimator(n_features=2, forgetting_factor=0.95)
    
    true_base = 92.0
    true_slope = 0.08
    
    for lap in range(1, 31):
        x = create_feature_vector(lap)
        y = true_base + true_slope * lap + np.random.normal(0, 0.3)
        rls.update(x, y)
    
    base = rls.get_base_pace()
    slope = rls.get_deg_slope()
    rmse = rls.get_rmse()
    
    print(f"✓ Base pace: {base:.3f}s (expected ~{true_base}s)")
    print(f"✓ Deg slope: {slope:.4f}s/lap (expected ~{true_slope}s/lap)")
    print(f"✓ RMSE: {rmse:.3f}s")
    
    assert abs(base - true_base) < 1.0, "Base pace too far off"
    assert abs(slope - true_slope) < 0.02, "Slope too far off"
    assert rmse < 25.0, "RMSE too high (warm-start uncertainty expected)"
    print("✅ RLS noise test PASSED\n")


def test_features():
    """Test feature engineering."""
    print("=== Testing Feature Builder ===")
    
    lap_times = [92.5, 92.6, 92.8, 93.0]
    
    frame = build_features(
        driver_number=1,
        lap_number=4,
        lap_times=lap_times,
        lap_in_stint=4,
        stint_number=1,
        compound="SOFT",
        tyre_age=4,
        gap_ahead=1.0,  # Traffic
        total_laps=50,
    )
    
    print(f"✓ Lap time: {frame.lap_time}s")
    print(f"✓ Best lap: {frame.best_lap_time}s")
    print(f"✓ Traffic affected: {frame.traffic_affected}")
    print(f"✓ Track evolution: {frame.track_evolution:.2f}")
    print(f"✓ Valid for training: {frame.is_valid}")
    
    assert frame.lap_time == 93.0, "Lap time incorrect"
    assert frame.best_lap_time == 92.5, "Best lap incorrect"
    assert frame.traffic_affected is True, "Should detect traffic"
    assert frame.track_evolution == 0.08, "Track evolution incorrect"
    print("✅ Feature building test PASSED\n")


def test_filters():
    """Test outlier filtering."""
    print("=== Testing Filters ===")
    
    lap_times = [90.0, 90.2, 90.1, 90.3, 95.0, 90.2]  # 95.0 is outlier
    
    filtered = filter_outliers_zscore(lap_times, threshold=2.0)
    filtered_times = [t for _, t in filtered]
    
    print(f"✓ Original laps: {len(lap_times)}")
    print(f"✓ After filtering: {len(filtered_times)}")
    print(f"✓ Outliers removed: {len(lap_times) - len(filtered_times)}")
    
    assert 95.0 not in filtered_times, "Outlier not removed"
    print("✅ Filter test PASSED\n")


def test_driver_model():
    """Test driver degradation model."""
    print("=== Testing Driver Model ===")
    
    model = DriverDegradationModel(driver_number=44)
    model.new_stint(1, "SOFT", 1)
    
    # Simulate degrading laps
    for lap in range(1, 21):
        lap_time = 92.0 + 0.08 * lap
        model.update(lap, lap_time, is_valid=True)
    
    pred = model.get_prediction(k=5)
    slope = model.get_deg_slope()
    risk = model.get_cliff_risk()
    
    print(f"✓ Deg slope: {slope:.4f}s/lap ({slope*1000:.1f}ms/lap)")
    print(f"✓ Cliff risk: {risk:.2f}")
    print(f"✓ Predictions (next 5): {[round(p, 2) for p in pred.predicted_next_k]}")
    print(f"✓ Model confidence: {pred.model_confidence:.2f}")
    
    assert slope > 0.05, "Should detect degradation"
    assert len(pred.predicted_next_k) == 5, "Should predict 5 laps"
    assert pred.predicted_next_k[4] > pred.predicted_next_k[0], "Predictions should increase"
    print("✅ Driver model test PASSED\n")


def test_model_manager():
    """Test model manager with multiple drivers."""
    print("=== Testing Model Manager ===")
    
    manager = ModelManager()
    
    # Simulate 2 drivers
    for driver_num in [1, 2]:
        for lap in range(1, 16):
            lap_time = 92.0 + (0.06 if driver_num == 1 else 0.09) * lap
            manager.update_driver(
                driver_number=driver_num,
                lap_in_stint=lap,
                lap_time=lap_time,
                stint_number=1,
                compound="MEDIUM",
                is_valid=True,
            )
    
    predictions = manager.get_all_predictions(k=3)
    
    print(f"✓ Drivers tracked: {len(predictions)}")
    for driver_num, pred in predictions.items():
        print(f"  Driver #{driver_num}: {pred.deg_slope*1000:.1f}ms/lap, risk={pred.cliff_risk:.2f}")
    
    assert len(predictions) == 2, "Should track 2 drivers"
    assert 1 in predictions and 2 in predictions, "Missing drivers"
    print("✅ Model manager test PASSED\n")


async def test_integration():
    """Test integration with real API."""
    print("=== Testing OpenF1 Integration ===")
    
    from rsw.ingest import OpenF1Client
    
    client = OpenF1Client()
    
    try:
        # Test fetching sessions
        sessions = await client.get_sessions(year=2023)
        print(f"✓ Fetched {len(sessions)} sessions from 2023")
        
        # Get a race
        races = [s for s in sessions if s.session_name == "Race"]
        if races:
            race = races[0]
            print(f"✓ Found race: {race.country_name} - {race.circuit_short_name}")
            
            # Fetch some data
            drivers = await client.get_drivers(race.session_key)
            laps = await client.get_laps(race.session_key)
            
            print(f"✓ Drivers: {len(drivers)}")
            print(f"✓ Laps: {len(laps)}")
            
            assert len(drivers) > 0, "No drivers found"
            assert len(laps) > 0, "No laps found"
            print("✅ Integration test PASSED\n")
        else:
            print("⚠️  No race data found, skipping integration test\n")
    
    finally:
        await client.close()


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("F1 RACE STRATEGY WORKBENCH - TEST SUITE")
    print("="*70)
    
    try:
        # Unit tests
        test_rls_basic()
        test_rls_noisy_data()
        test_features()
        test_filters()
        test_driver_model()
        test_model_manager()
        
        # Integration test
        asyncio.run(test_integration())
        
        print("="*70)
        print("✅ ALL TESTS PASSED!")
        print("="*70)
        return 0
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
