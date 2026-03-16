"""
Example usage of the ThingsBoard Power Forecast API.
Demonstrates how to interact with all endpoints.
"""
import requests
import time
import json


# Configuration
BASE_URL = "http://localhost:8000"
MAIN_ASSET_ID = "78fda490-e08b-11f0-b68f-8f33a9d74e0c"  # Replace with your asset ID
NEW_ASSET_ID = "b4ee7360-f4fb-11f0-bef0-af3b94c8901e"    # Replace with your asset ID


def print_response(title: str, response: requests.Response):
    """Pretty print API response."""
    print("\n" + "="*60)
    print(title)
    print("="*60)
    print(f"Status Code: {response.status_code}")
    print(f"Response:")
    print(json.dumps(response.json(), indent=2))


def example_1_health_check():
    """Example 1: Health check."""
    print("\n🏥 EXAMPLE 1: Health Check")
    print("-" * 60)
    
    response = requests.get(f"{BASE_URL}/health")
    print_response("Health Check Response", response)
    
    return response.status_code == 200


def example_2_start_forecast():
    """Example 2: Start a forecast job."""
    print("\n🚀 EXAMPLE 2: Start Forecast Job")
    print("-" * 60)
    
    payload = {
        "main_asset_id": MAIN_ASSET_ID
    }
    
    print(f"Starting forecast for asset: {MAIN_ASSET_ID}")
    response = requests.post(
        f"{BASE_URL}/forecast/start",
        json=payload
    )
    
    print_response("Forecast Start Response", response)
    
    if response.status_code == 202:
        job_id = response.json()["job_id"]
        print(f"\n✓ Job started successfully!")
        print(f"Job ID: {job_id}")
        return job_id
    else:
        print("\n✗ Failed to start job")
        return None


def example_3_check_job_status(job_id: str):
    """Example 3: Check job status."""
    print("\n📊 EXAMPLE 3: Check Job Status")
    print("-" * 60)
    
    print(f"Checking status for job: {job_id}")
    
    # Poll status every 2 seconds
    max_attempts = 30  # 1 minute max
    attempt = 0
    
    while attempt < max_attempts:
        response = requests.get(f"{BASE_URL}/forecast/status/{job_id}")
        
        if response.status_code == 200:
            data = response.json()
            status = data["status"]
            progress = data.get("progress", "No progress info")
            
            print(f"\n[Attempt {attempt + 1}] Status: {status}")
            print(f"Progress: {progress}")
            
            if data.get("assets_processed") is not None:
                print(f"Assets processed: {data['assets_processed']}/{data.get('total_assets', '?')}")
            
            # Check if job is complete
            if status in ["completed", "failed"]:
                print_response(f"\nFinal Job Status ({status.upper()})", response)
                
                if status == "failed":
                    print(f"\n✗ Job failed: {data.get('error', 'Unknown error')}")
                else:
                    print(f"\n✓ Job completed successfully!")
                
                return status
        else:
            print(f"Error checking status: {response.status_code}")
            return None
        
        # Wait before next check
        time.sleep(2)
        attempt += 1
    
    print("\n⏱️ Timeout: Job still running after 1 minute")
    return "timeout"


def example_4_process_new_asset():
    """Example 4: Process a new asset."""
    print("\n🆕 EXAMPLE 4: Process New Asset")
    print("-" * 60)
    
    payload = {
        "asset_id": NEW_ASSET_ID
    }
    
    print(f"Processing new asset: {NEW_ASSET_ID}")
    response = requests.post(
        f"{BASE_URL}/forecast/new-asset",
        json=payload
    )
    
    print_response("New Asset Response", response)
    
    if response.status_code == 200:
        data = response.json()
        if data["status"] == "telemetry_written":
            print(f"\n✓ Successfully processed new asset!")
        else:
            print(f"\n⚠️ Processing completed with status: {data['status']}")
    else:
        print(f"\n✗ Failed to process new asset")


def example_5_error_handling():
    """Example 5: Error handling."""
    print("\n❌ EXAMPLE 5: Error Handling")
    print("-" * 60)
    
    # Test with invalid job ID
    print("Testing with invalid job ID...")
    response = requests.get(f"{BASE_URL}/forecast/status/invalid-job-id-12345")
    
    print_response("Error Response (404 Not Found)", response)
    
    # Test with invalid asset ID
    print("\nTesting with empty asset ID...")
    try:
        response = requests.post(
            f"{BASE_URL}/forecast/start",
            json={"main_asset_id": ""}
        )
        print_response("Validation Error Response", response)
    except Exception as e:
        print(f"Request failed: {e}")


def main():
    """Run all examples."""
    print("\n" + "="*60)
    print("ThingsBoard Power Forecast API - Usage Examples")
    print("="*60)
    print(f"\nAPI Base URL: {BASE_URL}")
    print(f"Main Asset ID: {MAIN_ASSET_ID}")
    print(f"New Asset ID: {NEW_ASSET_ID}")
    
    # Example 1: Health Check
    if not example_1_health_check():
        print("\n❌ API is not running or not accessible")
        print("Please start the API first: python start_api.py")
        return
    
    # Example 2: Start Forecast
    job_id = example_2_start_forecast()
    
    if job_id:
        # Example 3: Check Job Status
        example_3_check_job_status(job_id)
    
    # Example 4: Process New Asset
    # Uncomment if you want to test processing a single asset
    # example_4_process_new_asset()
    
    # Example 5: Error Handling
    example_5_error_handling()
    
    # Summary
    print("\n" + "="*60)
    print("EXAMPLES COMPLETED")
    print("="*60)
    print("\nFor more examples, visit the interactive API docs:")
    print(f"  - Swagger UI: {BASE_URL}/docs")
    print(f"  - ReDoc: {BASE_URL}/redoc")
    print("="*60)
    print()


if __name__ == "__main__":
    main()
