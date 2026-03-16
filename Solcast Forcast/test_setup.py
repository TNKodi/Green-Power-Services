"""
Simple test script to verify the API setup.
Run this to test basic functionality without starting the full server.
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


async def test_configuration():
    """Test configuration loading."""
    print("\n" + "="*60)
    print("TEST 1: Configuration")
    print("="*60)
    
    try:
        from app.utils.config import settings
        
        print(f"✓ Configuration loaded successfully")
        print(f"  - Service: {settings.APP_NAME}")
        print(f"  - Version: {settings.APP_VERSION}")
        print(f"  - TB Host: {settings.TB_HOST}")
        print(f"  - TB Username: {settings.TB_USERNAME[:3]}***")
        print(f"  - Target Level: {settings.DEFAULT_TARGET_LEVEL}")
        print(f"  - Timezone: {settings.TZ_LOCAL}")
        
        # Validate
        settings.validate()
        print("✓ Configuration validation passed")
        return True
        
    except Exception as e:
        print(f"✗ Configuration test failed: {e}")
        return False


async def test_thingsboard_connection():
    """Test ThingsBoard connection."""
    print("\n" + "="*60)
    print("TEST 2: ThingsBoard Connection")
    print("="*60)
    
    try:
        from app.services.thingsboard_client import ThingsBoardClient
        
        async with ThingsBoardClient() as client:
            # This will trigger login
            token = await client._ensure_token()
            
            if token:
                print("✓ Successfully authenticated with ThingsBoard")
                print(f"  - Token: {token[:20]}...")
                return True
            else:
                print("✗ Authentication failed - no token received")
                return False
                
    except Exception as e:
        print(f"✗ ThingsBoard connection test failed: {e}")
        return False


async def test_job_manager():
    """Test job manager functionality."""
    print("\n" + "="*60)
    print("TEST 3: Job Manager")
    print("="*60)
    
    try:
        from app.services.job_manager import job_manager, JobStatus
        
        # Create a test job
        job_id = await job_manager.create_job("test-asset-123")
        print(f"✓ Created test job: {job_id}")
        
        # Update job status
        await job_manager.update_job_status(
            job_id,
            JobStatus.RUNNING,
            progress="Testing job manager"
        )
        print("✓ Updated job status")
        
        # Retrieve job
        job = await job_manager.get_job(job_id)
        if job:
            print(f"✓ Retrieved job information")
            print(f"  - Status: {job.status}")
            print(f"  - Progress: {job.progress}")
        
        # Complete job
        await job_manager.mark_completed(job_id)
        print("✓ Marked job as completed")
        
        return True
        
    except Exception as e:
        print(f"✗ Job manager test failed: {e}")
        return False


async def test_models():
    """Test Pydantic models."""
    print("\n" + "="*60)
    print("TEST 4: API Models")
    print("="*60)
    
    try:
        from app.models import (
            ForecastStartRequest,
            ForecastStartResponse,
            HealthResponse
        )
        from datetime import datetime
        
        # Test request model
        request = ForecastStartRequest(main_asset_id="test-123")
        print(f"✓ Created ForecastStartRequest: {request.main_asset_id}")
        
        # Test response models
        response = ForecastStartResponse(job_id="test-job", status="started")
        print(f"✓ Created ForecastStartResponse: {response.job_id}")
        
        health = HealthResponse(
            status="ok",
            service="test",
            timestamp=datetime.now()
        )
        print(f"✓ Created HealthResponse: {health.status}")
        
        return True
        
    except Exception as e:
        print(f"✗ Models test failed: {e}")
        return False


async def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("ThingsBoard Power Forecast API - Test Suite")
    print("="*60)
    
    results = []
    
    # Run tests
    results.append(await test_configuration())
    results.append(await test_thingsboard_connection())
    results.append(await test_job_manager())
    results.append(await test_models())
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"\nPassed: {passed}/{total}")
    
    if passed == total:
        print("\n✓ All tests passed! The API is ready to use.")
        print("\nNext steps:")
        print("  1. Run: python start_api.py")
        print("  2. Visit: http://localhost:8000/docs")
    else:
        print("\n✗ Some tests failed. Please check the errors above.")
        print("\nCommon issues:")
        print("  - Check .env file exists and has correct values")
        print("  - Verify ThingsBoard server is accessible")
        print("  - Ensure all dependencies are installed")
    
    print("="*60)
    print()


if __name__ == "__main__":
    asyncio.run(main())
