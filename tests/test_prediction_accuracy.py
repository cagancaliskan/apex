"""
Prediction accuracy tests using real F1 data.

These tests evaluate ML model performance on actual race sessions.
"""

import pytest
import asyncio
import numpy as np
from rsw.ingest import OpenF1Client
from rsw.models.degradation import DriverDegradationModel
from rsw.features.build import build_features
from rsw.features.filters import apply_filters


@pytest.mark.asyncio
class TestPredictionAccuracy:
    """Test ML prediction accuracy on real data."""
    
    async def test_degradation_prediction_accuracy(self):
        """
        Test degradation model accuracy.
        
        Strategy:
        1. Get real race data
        2. Train model on first 60% of laps
        3. Predict remaining 40%
        4. Compare predictions vs. actual
        """
        client = OpenF1Client()
        
        try:
            # Get a recent race
            sessions = await client.get_sessions(year=2023)
            races = [s for s in sessions if s.session_name == "Race"]
            session_key = races[0].session_key if races else None
            
            if not session_key:
                pytest.skip("No race data available")
            
            # Get laps for one driver
            all_laps = await client.get_laps(session_key)
            if not all_laps:
                pytest.skip("No lap data available")
            
            # Pick a driver with many laps
            driver_laps = {}
            for lap in all_laps:
                if lap.driver_number not in driver_laps:
                    driver_laps[lap.driver_number] = []
                driver_laps[lap.driver_number].append(lap)
            
            # Get driver with most laps
            driver_num = max(driver_laps.keys(), key=lambda d: len(driver_laps[d]))
            laps = sorted(driver_laps[driver_num], key=lambda l: l.lap_number)
            
            if len(laps) < 20:
                pytest.skip("Not enough laps for testing")
            
            # Filter out pit laps and outliers
            valid_laps = [
                l for l in laps
                if l.lap_duration and 60 < l.lap_duration < 150
            ]
            
            if len(valid_laps) < 15:
                pytest.skip("Not enough valid laps")
            
            # Split: train on first 60%, test on last 40%
            split_idx = int(len(valid_laps) * 0.6)
            train_laps = valid_laps[:split_idx]
            test_laps = valid_laps[split_idx:]
            
            # Train model
            model = DriverDegradationModel(driver_number=driver_num)
            model.new_stint(1, "MEDIUM", 1)  # Assume medium tyres
            
            for lap in train_laps:
                lap_in_stint = lap.lap_number  # Simplified
                model.update(
                    lap_in_stint=lap_in_stint,
                    lap_time=lap.lap_duration,
                    is_valid=True,
                )
            
            # Make predictions
            predictions = []
            actuals = []
            
            for i, lap in enumerate(test_laps):
                # Predict k steps ahead
                k = min(5, len(test_laps) - i)
                pred = model.get_prediction(k=k)
                
                if pred and pred.predicted_next_k:
                    # Compare first prediction to actual
                    predictions.append(pred.predicted_next_k[0])
                    actuals.append(lap.lap_duration)
                    
                    # Update model with actual (online learning)
                    model.update(
                        lap_in_stint=lap.lap_number,
                        lap_time=lap.lap_duration,
                        is_valid=True,
                    )
            
            # Calculate metrics
            if len(predictions) >= 3:
                predictions = np.array(predictions)
                actuals = np.array(actuals)
                
                mae = np.mean(np.abs(predictions - actuals))
                rmse = np.sqrt(np.mean((predictions - actuals) ** 2))
                mape = np.mean(np.abs((predictions - actuals) / actuals)) * 100
                
                print(f"\n{'='*60}")
                print(f"Prediction Accuracy Metrics (Driver #{driver_num})")
                print(f"{'='*60}")
                print(f"Training laps: {len(train_laps)}")
                print(f"Test laps: {len(test_laps)}")
                print(f"MAE (Mean Absolute Error): {mae:.3f}s")
                print(f"RMSE (Root Mean Square Error): {rmse:.3f}s")
                print(f"MAPE (Mean Absolute % Error): {mape:.2f}%")
                print(f"{'='*60}\n")
                
                # Assertions - reasonable accuracy thresholds
                # MAE should be reasonable (relaxed for real-world conditions)
                assert mae < 5.0, f"MAE too high: {mae:.3f}s"
                assert rmse < 7.0, f"RMSE too high: {rmse:.3f}s"
                assert mape < 5.0, f"MAPE too high: {mape:.2f}%"
            
        finally:
            await client.close()
    
    async def test_multiple_drivers_accuracy(self):
        """Test accuracy across multiple drivers."""
        client = OpenF1Client()
        
        try:
            sessions = await client.get_sessions(year=2023)
            races = [s for s in sessions if s.session_name == "Race"][:1]  # Just one race
            
            if not races:
                pytest.skip("No race data")
            
            session_key = races[0].session_key
            all_laps = await client.get_laps(session_key)
            
            # Group by driver
            driver_laps = {}
            for lap in all_laps:
                if lap.lap_duration and 60 < lap.lap_duration < 150:
                    if lap.driver_number not in driver_laps:
                        driver_laps[lap.driver_number] = []
                    driver_laps[lap.driver_number].append(lap)
            
            results = []
            
            for driver_num, laps in list(driver_laps.items())[:5]:  # Test 5 drivers
                if len(laps) < 15:
                    continue
                
                laps = sorted(laps, key=lambda l: l.lap_number)
                split = int(len(laps) * 0.7)
                train = laps[:split]
                test = laps[split:]
                
                model = DriverDegradationModel(driver_number=driver_num)
                model.new_stint(1, "MEDIUM", 1)
                
                for lap in train:
                    model.update(lap.lap_number, lap.lap_duration, True)
                
                preds = []
                acts = []
                
                for lap in test[:5]:  # Just first 5 test laps
                    pred = model.get_prediction(k=1)
                    if pred and pred.predicted_next_k:
                        preds.append(pred.predicted_next_k[0])
                        acts.append(lap.lap_duration)
                        model.update(lap.lap_number, lap.lap_duration, True)
                
                if preds:
                    mae = np.mean(np.abs(np.array(preds) - np.array(acts)))
                    results.append(mae)
            
            if results:
                avg_mae = np.mean(results)
                print(f"\nAverage MAE across {len(results)} drivers: {avg_mae:.3f}s")
                
                # Average should be reasonable (relaxed)
                assert avg_mae < 7.5, f"Average MAE too high: {avg_mae:.3f}s"
        
        finally:
            await client.close()
