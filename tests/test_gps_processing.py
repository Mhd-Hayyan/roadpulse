import os
import pandas as pd
import numpy as np
import pytest

from src.processing.gps_processing import (
    is_valid_coordinate,
    is_inside_route_area,
    process_gps_events,
    run_pipeline
)

def test_is_valid_coordinate():
    # Valid
    assert is_valid_coordinate(9.93, 76.26)
    assert is_valid_coordinate(0.0, 0.0)
    
    # Invalid missing
    assert not is_valid_coordinate(np.nan, 76.26)
    assert not is_valid_coordinate(9.93, np.nan)
    
    # Invalid out of bounds
    assert not is_valid_coordinate(91.0, 76.26)
    assert not is_valid_coordinate(9.93, 181.0)
    assert not is_valid_coordinate(-91.0, 76.26)

def test_is_inside_route_area():
    # Inside Route: Lat 9.90 to 9.97, Lon 76.23 to 76.31
    assert is_inside_route_area(9.93, 76.26)
    assert is_inside_route_area(9.90, 76.23)
    assert is_inside_route_area(9.97, 76.31)
    
    # Outside Route
    assert not is_inside_route_area(9.89, 76.26) # lat too low
    assert not is_inside_route_area(9.98, 76.26) # lat too high
    assert not is_inside_route_area(9.93, 76.22) # lon too low
    assert not is_inside_route_area(9.93, 76.32) # lon too high
    
    # Invalid coords should also be outside
    assert not is_inside_route_area(np.nan, 76.26)

def test_process_gps_events():
    data = {
        'event_id': ['e1', 'e2', 'e3'],
        'center_latitude': [9.93, 9.80, np.nan],
        'center_longitude': [76.26, 76.20, 76.26]
    }
    df = pd.DataFrame(data)
    
    df_out = process_gps_events(df)
    
    # Check expected columns
    expected_cols = ['gps_valid', 'inside_route_area', 'gps_quality', 'map_match_latitude', 'map_match_longitude']
    for col in expected_cols:
        assert col in df_out.columns
        
    # Check values
    assert df_out.loc[0, 'gps_valid'] == 1
    assert df_out.loc[0, 'inside_route_area'] == 1
    assert df_out.loc[0, 'gps_quality'] == 'good'
    assert df_out.loc[0, 'map_match_latitude'] == 9.93
    assert df_out.loc[0, 'map_match_longitude'] == 76.26
    
    assert df_out.loc[1, 'gps_valid'] == 1
    assert df_out.loc[1, 'inside_route_area'] == 0
    assert df_out.loc[1, 'gps_quality'] == 'outside_route_area'
    assert df_out.loc[1, 'map_match_latitude'] == 9.80
    
    assert df_out.loc[2, 'gps_valid'] == 0
    assert df_out.loc[2, 'inside_route_area'] == 0
    assert df_out.loc[2, 'gps_quality'] == 'invalid_coordinates'
    assert pd.isna(df_out.loc[2, 'map_match_latitude'])

def test_pipeline_output(tmp_path):
    input_path = "data/processed/filtered_events.csv"
    if not os.path.exists(input_path):
        pytest.skip(f"Input file {input_path} not found")
        
    output_path = str(tmp_path / "gps_processed_events.csv")
    
    df_out = run_pipeline(input_path, output_path)
    
    # Output file should be created
    assert os.path.exists(output_path)
    
    # Should not be empty if input has data
    assert len(df_out) > 0
    
    # Check columns
    assert 'gps_valid' in df_out.columns
    assert 'inside_route_area' in df_out.columns
    assert 'map_match_latitude' in df_out.columns
    assert 'map_match_longitude' in df_out.columns

def run():
    print("Running test_gps_processing.py checks...")
    print("- Testing coordinate validity...")
    test_is_valid_coordinate()
    print("- Testing route area inclusion...")
    test_is_inside_route_area()
    print("- Testing dataframe processing...")
    test_process_gps_events()
    print("All GPS processing tests passed!")

if __name__ == "__main__":
    run()
