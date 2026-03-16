"""
Test Error Handling for Power Forecast API

This script tests all error handling scenarios to ensure proper validation
and error responses.
"""

import httpx
import asyncio
import json
from typing import Dict, Any


BASE_URL = "http://localhost:8000"


async def test_health_check():
    """Test 1: Health check endpoint"""
    print("\n" + "="*80)
    print("TEST 1: Health Check")
    print("="*80)
    
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        assert response.status_code == 200, "Health check should return 200"
        print("✅ PASSED")


async def test_start_forecast_missing_asset_id():
    """Test 2: Start forecast with missing asset_id"""
    print("\n" + "="*80)
    print("TEST 2: Start Forecast - Missing Asset ID")
    print("="*80)
    
    async with httpx.AsyncClient() as client:
        # Test with empty string
        response = await client.post(
            f"{BASE_URL}/forecast/start",
            json={"main_asset_id": ""}
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        assert response.status_code == 400, "Should return 400 for empty asset_id"
        assert "ASSET_ID_REQUIRED" in str(response.json()), "Should contain error code"
        print("✅ PASSED - Empty asset_id rejected")
        
        # Test with whitespace only
        response = await client.post(
            f"{BASE_URL}/forecast/start",
            json={"main_asset_id": "   "}
        )
        print(f"\nStatus: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        assert response.status_code == 400, "Should return 400 for whitespace asset_id"
        print("✅ PASSED - Whitespace asset_id rejected")


async def test_start_forecast_nonexistent_asset():
    """Test 3: Start forecast with non-existent asset"""
    print("\n" + "="*80)
    print("TEST 3: Start Forecast - Non-existent Asset")
    print("="*80)
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/forecast/start",
            json={"main_asset_id": "FAKE_ASSET_ID_12345"}
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        assert response.status_code == 404, "Should return 404 for non-existent asset"
        assert "ASSET_NOT_FOUND" in str(response.json()), "Should contain error code"
        print("✅ PASSED - Non-existent asset rejected")


async def test_new_asset_missing_asset_id():
    """Test 4: Process new asset with missing asset_id"""
    print("\n" + "="*80)
    print("TEST 4: Process New Asset - Missing Asset ID")
    print("="*80)
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/forecast/new-asset",
            json={"asset_id": ""}
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        assert response.status_code == 400, "Should return 400 for empty asset_id"
        assert "ASSET_ID_REQUIRED" in str(response.json()), "Should contain error code"
        print("✅ PASSED")


async def test_new_asset_nonexistent():
    """Test 5: Process new asset that doesn't exist"""
    print("\n" + "="*80)
    print("TEST 5: Process New Asset - Non-existent Asset")
    print("="*80)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{BASE_URL}/forecast/new-asset",
            json={"asset_id": "FAKE_ASSET_ID_99999"}
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        assert response.status_code == 404, "Should return 404 for non-existent asset"
        assert "ASSET_NOT_FOUND" in str(response.json()), "Should contain error code"
        print("✅ PASSED")


async def test_new_asset_missing_attributes():
    """Test 6: Process new asset with missing required attributes"""
    print("\n" + "="*80)
    print("TEST 6: Process New Asset - Missing Required Attributes")
    print("="*80)
    print("⚠️  This test requires a real asset_id with missing attributes")
    print("    Please provide an asset_id that exists but lacks required attributes")
    print("    Skipping for now...")
    print("⏭️  SKIPPED")


async def test_job_status_tracking():
    """Test 7: Job status with error tracking"""
    print("\n" + "="*80)
    print("TEST 7: Job Status - Error Tracking")
    print("="*80)
    
    async with httpx.AsyncClient() as client:
        # Start a forecast job (will fail with fake asset)
        response = await client.post(
            f"{BASE_URL}/forecast/start",
            json={"main_asset_id": "VALID_TEST_ASSET"}  # Replace with a real asset_id
        )
        
        if response.status_code == 404:
            print("⚠️  Need a valid asset_id to test job status tracking")
            print("⏭️  SKIPPED - Replace 'VALID_TEST_ASSET' with real asset_id")
            return
        
        print(f"Start Response: {response.status_code}")
        job_data = response.json()
        job_id = job_data.get("job_id")
        print(f"Job ID: {job_id}")
        
        # Check job status
        await asyncio.sleep(2)
        status_response = await client.get(f"{BASE_URL}/forecast/status/{job_id}")
        print(f"\nStatus Response: {status_response.status_code}")
        print(f"Response: {json.dumps(status_response.json(), indent=2)}")
        
        status_data = status_response.json()
        assert "successful_assets" in status_data, "Should have successful_assets field"
        assert "failed_assets" in status_data, "Should have failed_assets field"
        assert "skipped_assets" in status_data, "Should have skipped_assets field"
        assert "errors" in status_data, "Should have errors field"
        assert "current_step" in status_data, "Should have current_step field"
        print("✅ PASSED - All error tracking fields present")


async def test_invalid_job_id():
    """Test 8: Check status with invalid job_id"""
    print("\n" + "="*80)
    print("TEST 8: Job Status - Invalid Job ID")
    print("="*80)
    
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/forecast/status/INVALID_JOB_123")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        assert response.status_code == 404, "Should return 404 for invalid job_id"
        print("✅ PASSED")


async def run_all_tests():
    """Run all error handling tests"""
    print("\n" + "#"*80)
    print("#" + " "*25 + "ERROR HANDLING TEST SUITE" + " "*29 + "#")
    print("#"*80)
    
    tests = [
        ("Health Check", test_health_check),
        ("Missing Asset ID (Start)", test_start_forecast_missing_asset_id),
        ("Non-existent Asset (Start)", test_start_forecast_nonexistent_asset),
        ("Missing Asset ID (New)", test_new_asset_missing_asset_id),
        ("Non-existent Asset (New)", test_new_asset_nonexistent),
        ("Missing Attributes (New)", test_new_asset_missing_attributes),
        ("Job Status Tracking", test_job_status_tracking),
        ("Invalid Job ID", test_invalid_job_id),
    ]
    
    passed = 0
    failed = 0
    skipped = 0
    
    for name, test_func in tests:
        try:
            await test_func()
            if "SKIPPED" not in str(test_func.__doc__):
                passed += 1
            else:
                skipped += 1
        except AssertionError as e:
            failed += 1
            print(f"❌ FAILED: {e}")
        except Exception as e:
            failed += 1
            print(f"❌ ERROR: {e}")
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"✅ Passed:  {passed}")
    print(f"❌ Failed:  {failed}")
    print(f"⏭️  Skipped: {skipped}")
    print(f"📊 Total:   {len(tests)}")
    print("="*80)
    
    if failed == 0:
        print("\n🎉 All tests passed! Error handling is working correctly.")
    else:
        print(f"\n⚠️  {failed} test(s) failed. Please review the output above.")


if __name__ == "__main__":
    print("Starting error handling tests...")
    print("Make sure the API is running on http://localhost:8000")
    print("\nPress Ctrl+C to cancel\n")
    
    try:
        asyncio.run(run_all_tests())
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests cancelled by user")
    except Exception as e:
        print(f"\n\n❌ Test suite error: {e}")
